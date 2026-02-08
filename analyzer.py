"""決算データ分析モジュール

過去8四半期の推移分析、セグメント別実績の集計を行う。
"""

from collections import defaultdict
from dataclasses import dataclass, field

from xbrl_parser import ParsedFinancials


@dataclass
class QuarterlyMetric:
    """四半期ごとの指標値"""
    period_end: str  # YYYY-MM-DD
    filing_type: str  # annual / quarterly / semi_annual
    label: str  # 日本語ラベル
    value: float
    unit: str = ""
    yoy_change: float | None = None  # 前年同期比 (%)


@dataclass
class SegmentMetric:
    """セグメント別指標"""
    segment_name: str
    metrics: dict[str, float] = field(default_factory=dict)  # {指標名: 値}


@dataclass
class AnalysisResult:
    """分析結果"""
    company_name: str = ""
    sec_code: str = ""
    edinet_code: str = ""
    # 四半期推移: {指標名: [QuarterlyMetric, ...]}
    quarterly_trends: dict[str, list[QuarterlyMetric]] = field(default_factory=dict)
    # セグメント別: {期末日: [SegmentMetric, ...]}
    segment_results: dict[str, list[SegmentMetric]] = field(default_factory=dict)
    # 最新期の主要指標サマリ
    latest_summary: dict[str, str] = field(default_factory=dict)
    # 警告メッセージ
    warnings: list[str] = field(default_factory=list)


class FinancialAnalyzer:
    """財務データの分析を行うクラス"""

    # 表示する主要指標 (優先度順)
    KEY_METRICS = [
        ("NetSales", "売上高"),
        ("Revenue", "売上収益"),
        ("OperatingRevenue1", "営業収益"),
        ("OperatingIncome", "営業利益"),
        ("OrdinaryIncome", "経常利益"),
        ("ProfitLossAttributableToOwnersOfParent", "親会社帰属純利益"),
        ("ProfitLoss", "当期純利益"),
        ("TotalAssets", "総資産"),
        ("NetAssets", "純資産"),
        ("NetCashProvidedByUsedInOperatingActivities", "営業CF"),
        ("NetCashProvidedByUsedInInvestingActivities", "投資CF"),
        ("NetCashProvidedByUsedInFinancingActivities", "財務CF"),
    ]

    def analyze(self, filings: list[ParsedFinancials]) -> AnalysisResult:
        """複数期の財務データを分析する

        Args:
            filings: 期ごとのパース済み財務データリスト (時系列順)

        Returns:
            AnalysisResult
        """
        result = AnalysisResult()

        if not filings:
            result.warnings.append("分析対象の書類がありません")
            return result

        # 基本情報
        latest = filings[-1]
        result.company_name = latest.company_name

        # 四半期推移の構築
        self._build_quarterly_trends(filings, result)

        # セグメント別実績の構築
        self._build_segment_results(filings, result)

        # 最新期サマリ
        self._build_latest_summary(result)

        return result

    def _build_quarterly_trends(
        self, filings: list[ParsedFinancials], result: AnalysisResult
    ):
        """過去8四半期の推移データを構築する"""
        # 期末日ごとにデータを整理
        period_data: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))

        for filing in filings:
            period_end = filing.period_end
            if not period_end:
                continue

            for item in filing.items:
                # 当期のデータのみ (current_duration or current_instant)
                if item.period not in ("current_duration", "current_instant",
                                       "current_q_duration"):
                    continue

                try:
                    numeric_value = float(str(item.value).replace(",", ""))
                except (ValueError, TypeError):
                    continue

                period_data[period_end][item.element_id].append(
                    (numeric_value, item.unit, filing.filing_type)
                )

        # 各指標の推移を構築
        sorted_periods = sorted(period_data.keys())
        # 最大8四半期分
        recent_periods = sorted_periods[-8:]

        for elem_id, label in self.KEY_METRICS:
            metrics_list = []
            for period in recent_periods:
                values = period_data[period].get(elem_id, [])
                if not values:
                    continue

                # 連結優先、最初の値を使用
                value, unit, filing_type = values[0]

                metric = QuarterlyMetric(
                    period_end=period,
                    filing_type=filing_type,
                    label=label,
                    value=value,
                    unit=unit,
                )
                metrics_list.append(metric)

            if metrics_list:
                # 前年同期比を計算
                self._calculate_yoy(metrics_list)
                result.quarterly_trends[label] = metrics_list

    def _calculate_yoy(self, metrics: list[QuarterlyMetric]):
        """前年同期比を計算する"""
        for i, metric in enumerate(metrics):
            # 約1年前のデータを探す
            target_year = int(metric.period_end[:4]) - 1
            target_suffix = metric.period_end[4:]

            for j in range(i):
                prev = metrics[j]
                if (prev.period_end[:4] == str(target_year)
                        and prev.period_end[4:] == target_suffix
                        and prev.value != 0):
                    metric.yoy_change = (
                        (metric.value - prev.value) / abs(prev.value) * 100
                    )
                    break

    def _build_segment_results(
        self, filings: list[ParsedFinancials], result: AnalysisResult
    ):
        """セグメント別実績を構築する"""
        for filing in filings:
            period_end = filing.period_end
            if not period_end or not filing.segments:
                continue

            # セグメント名ごとに集約
            seg_map: dict[str, dict[str, float]] = defaultdict(dict)

            for seg in filing.segments:
                if seg.period != "current":
                    continue
                metric_label = seg.label
                seg_map[seg.segment_name][metric_label] = seg.value

            if seg_map:
                segment_metrics = []
                for seg_name, metrics in sorted(seg_map.items()):
                    segment_metrics.append(
                        SegmentMetric(segment_name=seg_name, metrics=metrics)
                    )
                result.segment_results[period_end] = segment_metrics

    def _build_latest_summary(self, result: AnalysisResult):
        """最新期のサマリを構築する"""
        for label, metrics_list in result.quarterly_trends.items():
            if not metrics_list:
                continue
            latest = metrics_list[-1]
            value_str = self._format_value(latest.value)
            yoy_str = ""
            if latest.yoy_change is not None:
                sign = "+" if latest.yoy_change > 0 else ""
                yoy_str = f" ({sign}{latest.yoy_change:.1f}%)"
            result.latest_summary[label] = f"{value_str}{yoy_str}"

    @staticmethod
    def _format_value(value: float) -> str:
        """数値を読みやすい形式にフォーマットする (百万円単位)"""
        abs_val = abs(value)
        sign = "-" if value < 0 else ""
        if abs_val >= 1_000_000_000_000:
            return f"{sign}{abs_val / 1_000_000_000_000:.1f}兆円"
        elif abs_val >= 100_000_000:
            return f"{sign}{abs_val / 100_000_000:.0f}億円"
        elif abs_val >= 1_000_000:
            return f"{sign}{abs_val / 1_000_000:.0f}百万円"
        elif abs_val >= 1_000:
            return f"{sign}{abs_val / 1_000:.0f}千円"
        else:
            return f"{sign}{abs_val:.0f}円"
