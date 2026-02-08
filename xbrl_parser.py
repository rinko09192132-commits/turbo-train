"""EDINET CSVデータ (type=5) パーサー

EDINET API type=5で取得できるCSVは以下の構造:
- XBRL要素をCSV形式に変換したもの
- 主要ファイル: jpcrp_cor (連結財務諸表), jppfs_cor (個別財務諸表)
- 各行は要素ID、コンテキスト、値を含む
"""

import csv
import io
import re
from dataclasses import dataclass, field

from config import FINANCIAL_ELEMENTS, SEGMENT_ELEMENTS


@dataclass
class FinancialItem:
    """財務データ項目"""
    element_id: str
    label: str
    context_id: str
    value: str
    unit: str = ""
    period: str = ""
    is_consolidated: bool = True


@dataclass
class SegmentData:
    """セグメントデータ"""
    segment_name: str
    element_id: str
    label: str
    value: float
    period: str = ""


@dataclass
class ParsedFinancials:
    """パース済み財務データ"""
    doc_id: str = ""
    company_name: str = ""
    period_end: str = ""
    filing_type: str = ""
    items: list[FinancialItem] = field(default_factory=list)
    segments: list[SegmentData] = field(default_factory=list)
    raw_data: list[dict] = field(default_factory=list)


class XBRLCSVParser:
    """EDINET CSVデータをパースして財務情報を抽出する"""

    # コンテキストIDパターン
    # CurrentYearDuration = 当期累計
    # CurrentYearInstant = 当期末時点
    # Prior1YearDuration = 前期累計
    # Prior1YearInstant = 前期末時点
    CONTEXT_PATTERNS = {
        "current_duration": re.compile(r"CurrentYear.*Duration", re.IGNORECASE),
        "current_instant": re.compile(r"CurrentYear.*Instant", re.IGNORECASE),
        "prior1_duration": re.compile(r"Prior1Year.*Duration", re.IGNORECASE),
        "prior1_instant": re.compile(r"Prior1Year.*Instant", re.IGNORECASE),
        # 四半期
        "current_q_duration": re.compile(
            r"CurrentQuarter.*Duration|CurrentYTD.*Duration", re.IGNORECASE
        ),
        "prior1_q_duration": re.compile(
            r"Prior1Quarter.*Duration|Prior1YTD.*Duration", re.IGNORECASE
        ),
    }

    SEGMENT_CONTEXT_PATTERN = re.compile(
        r"(CurrentYear|Prior1Year).*Duration.*_(.+?)(?:Member|Segment)", re.IGNORECASE
    )

    def parse_csv_files(self, csv_files: dict[str, str], doc_info: dict = None) -> ParsedFinancials:
        """CSVファイル群から財務データを抽出する

        Args:
            csv_files: ファイル名 -> CSV内容 の辞書
            doc_info: 書類メタ情報

        Returns:
            ParsedFinancials
        """
        result = ParsedFinancials()
        if doc_info:
            result.doc_id = doc_info.get("docID", "")
            result.company_name = doc_info.get("filerName", "")
            result.period_end = doc_info.get("periodEnd", "")
            result.filing_type = doc_info.get("_filingType", "")

        for filename, content in csv_files.items():
            # 連結財務諸表のCSVを優先的に処理
            lower_name = filename.lower()
            is_consolidated = "jpcrp" in lower_name or "jpcor" in lower_name

            rows = self._parse_csv_content(content)
            result.raw_data.extend(rows)

            # 主要財務項目の抽出
            self._extract_financial_items(rows, result, is_consolidated)

            # セグメントデータの抽出
            self._extract_segment_data(rows, result)

        return result

    def _parse_csv_content(self, content: str) -> list[dict]:
        """CSVの内容をパースする

        EDINETのCSVは以下の列を持つ:
        要素ID, コンテキストID, 値, ...
        ヘッダ行の有無はファイルにより異なる
        """
        rows = []
        reader = csv.reader(io.StringIO(content))

        header = None
        for row_num, row in enumerate(reader):
            if not row or len(row) < 3:
                continue

            # ヘッダ行の検出
            if row_num == 0 and any(
                h in str(row[0]).lower() for h in ["要素id", "element", "項目"]
            ):
                header = row
                continue

            # ヘッダがない場合のデフォルト列マッピング
            if header is None:
                header = self._detect_header(row)
                if header and row_num == 0:
                    continue

            record = self._row_to_dict(row, header)
            if record:
                rows.append(record)

        return rows

    def _detect_header(self, sample_row: list[str]) -> list[str]:
        """CSVのヘッダを推定する"""
        # EDINET CSVの標準的な列構成
        if len(sample_row) >= 5:
            return [
                "要素ID", "コンテキストID", "相対年度", "連結・個別",
                "期間・時点", "値", "単位", "タイトル項目"
            ][:len(sample_row)]
        elif len(sample_row) >= 3:
            return ["要素ID", "コンテキストID", "値"] + [
                f"col{i}" for i in range(3, len(sample_row))
            ]
        return None

    def _row_to_dict(self, row: list[str], header: list[str] = None) -> dict | None:
        """CSV行を辞書に変換する"""
        if not row or len(row) < 3:
            return None

        if header and len(row) >= len(header):
            record = {header[i]: row[i] for i in range(len(header))}
        else:
            record = {
                "要素ID": row[0] if len(row) > 0 else "",
                "コンテキストID": row[1] if len(row) > 1 else "",
                "値": row[2] if len(row) > 2 else "",
            }

        # 追加列
        if len(row) > 3:
            record.setdefault("単位", row[3] if len(row) > 3 else "")
        if len(row) > 4:
            record.setdefault("相対年度", row[4] if len(row) > 4 else "")

        return record

    def _extract_financial_items(
        self, rows: list[dict], result: ParsedFinancials, is_consolidated: bool
    ):
        """主要財務項目を抽出する"""
        for row in rows:
            element_id = row.get("要素ID", "")
            context_id = row.get("コンテキストID", "")
            value = row.get("値", "")

            if not element_id or not value:
                continue

            # XBRL要素名の末尾部分でマッチ
            matched_element = None
            matched_label = None
            for elem_key, elem_label in FINANCIAL_ELEMENTS.items():
                if element_id.endswith(elem_key) or elem_key in element_id:
                    matched_element = elem_key
                    matched_label = elem_label
                    break

            if not matched_element:
                continue

            # コンテキストから期間を判定
            period = self._classify_context(context_id)

            item = FinancialItem(
                element_id=matched_element,
                label=matched_label,
                context_id=context_id,
                value=value,
                unit=row.get("単位", ""),
                period=period,
                is_consolidated=is_consolidated,
            )
            result.items.append(item)

    def _extract_segment_data(self, rows: list[dict], result: ParsedFinancials):
        """セグメントデータを抽出する"""
        for row in rows:
            element_id = row.get("要素ID", "")
            context_id = row.get("コンテキストID", "")
            value = row.get("値", "")

            if not element_id or not value:
                continue

            # セグメント関連要素かチェック
            matched_element = None
            matched_label = None
            for elem_key, elem_label in SEGMENT_ELEMENTS.items():
                if element_id.endswith(elem_key) or elem_key in element_id:
                    matched_element = elem_key
                    matched_label = elem_label
                    break

            if not matched_element:
                continue

            # コンテキストIDからセグメント名を抽出
            seg_match = self.SEGMENT_CONTEXT_PATTERN.search(context_id)
            if not seg_match:
                continue

            segment_name = seg_match.group(2)
            # セグメント名を読みやすく変換
            segment_name = self._clean_segment_name(segment_name)

            try:
                numeric_value = float(value.replace(",", ""))
            except (ValueError, AttributeError):
                continue

            period_type = "current" if "CurrentYear" in context_id else "prior"

            seg = SegmentData(
                segment_name=segment_name,
                element_id=matched_element,
                label=matched_label,
                value=numeric_value,
                period=period_type,
            )
            result.segments.append(seg)

    def _classify_context(self, context_id: str) -> str:
        """コンテキストIDから期間分類を返す"""
        for period_type, pattern in self.CONTEXT_PATTERNS.items():
            if pattern.search(context_id):
                return period_type
        return "unknown"

    def _clean_segment_name(self, raw_name: str) -> str:
        """セグメント名をクリーンアップする"""
        # CamelCase -> スペース区切り
        name = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw_name)
        # 一般的な接尾辞を除去
        name = re.sub(r"(Segment|Member|Business|Operations?)$", "", name).strip()
        return name if name else raw_name
