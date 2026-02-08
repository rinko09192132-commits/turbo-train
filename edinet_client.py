"""EDINET API v2 クライアント"""

import io
import json
import os
import time
import zipfile
from datetime import datetime, timedelta

import requests

from config import (
    CACHE_DIR,
    DATA_DIR,
    DOC_TYPES,
    DOCUMENTS_LIST_URL,
    DOCUMENT_URL,
    DOWNLOAD_TYPE_CSV,
)


class EdinetClient:
    """EDINET API v2 を利用して書類一覧取得・書類ダウンロードを行うクライアント"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)

    def get_document_list(self, date: str, doc_type: int = 2) -> dict:
        """指定日の書類一覧を取得する

        Args:
            date: 日付 (YYYY-MM-DD)
            doc_type: 1=メタデータのみ, 2=提出書類一覧+メタデータ

        Returns:
            APIレスポンスのJSON
        """
        params = {
            "date": date,
            "type": doc_type,
            "Subscription-Key": self.api_key,
        }
        resp = self.session.get(DOCUMENTS_LIST_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def search_company_filings(
        self,
        sec_code: str = None,
        edinet_code: str = None,
        company_name: str = None,
        start_date: str = None,
        end_date: str = None,
        filing_types: list[str] = None,
    ) -> list[dict]:
        """企業の提出書類を検索する

        Args:
            sec_code: 証券コード (4桁 or 5桁)
            edinet_code: EDINETコード
            company_name: 企業名 (部分一致)
            start_date: 検索開始日 (YYYY-MM-DD)
            end_date: 検索終了日 (YYYY-MM-DD)
            filing_types: 取得する書類種別 ["annual", "quarterly", "semi_annual"]

        Returns:
            マッチした書類情報のリスト
        """
        if not any([sec_code, edinet_code, company_name]):
            raise ValueError("sec_code, edinet_code, company_name のいずれかを指定してください")

        if filing_types is None:
            filing_types = ["annual", "quarterly", "semi_annual"]

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

        # 証券コードを5桁に正規化
        if sec_code and len(sec_code) == 4:
            sec_code = sec_code + "0"

        results = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        print(f"書類一覧を検索中: {start_date} ~ {end_date}")

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")

            # キャッシュ確認
            cache_path = os.path.join(CACHE_DIR, f"doclist_{date_str}.json")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                try:
                    data = self.get_document_list(date_str)
                    # キャッシュに保存
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False)
                    time.sleep(0.5)  # API負荷軽減
                except requests.exceptions.RequestException as e:
                    print(f"  {date_str}: APIエラー - {e}")
                    current += timedelta(days=1)
                    continue

            if "results" not in data:
                current += timedelta(days=1)
                continue

            for doc in data["results"]:
                # 企業フィルタ
                if sec_code and doc.get("secCode") != sec_code:
                    continue
                if edinet_code and doc.get("edinetCode") != edinet_code:
                    continue
                if company_name and company_name not in (doc.get("filerName") or ""):
                    continue

                # 書類種別フィルタ
                ord_code = doc.get("ordinanceCode")
                form_code = doc.get("formCode")
                matched = False
                for ft in filing_types:
                    dt = DOC_TYPES.get(ft)
                    if dt and ord_code == dt["ordinanceCode"] and form_code == dt["formCode"]:
                        matched = True
                        doc["_filingType"] = ft
                        doc["_filingTypeLabel"] = dt["label"]
                        break

                if matched:
                    results.append(doc)

            current += timedelta(days=1)

        # periodEnd でソート
        results.sort(key=lambda x: x.get("periodEnd") or "")
        print(f"  {len(results)} 件の書類が見つかりました")
        return results

    def download_csv_data(self, doc_id: str) -> bytes:
        """書類のCSVデータ (type=5) をダウンロードする

        Args:
            doc_id: 書類管理番号 (docID)

        Returns:
            ZIPファイルのバイナリデータ
        """
        # キャッシュ確認
        cache_path = os.path.join(CACHE_DIR, f"{doc_id}_csv.zip")
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                return f.read()

        url = f"{DOCUMENT_URL}/{doc_id}"
        params = {
            "type": DOWNLOAD_TYPE_CSV,
            "Subscription-Key": self.api_key,
        }
        resp = self.session.get(url, params=params, timeout=60)
        resp.raise_for_status()

        # キャッシュに保存
        with open(cache_path, "wb") as f:
            f.write(resp.content)

        return resp.content

    def extract_csv_files(self, zip_data: bytes) -> dict[str, str]:
        """ZIPからCSVファイルを展開する

        Args:
            zip_data: ZIPファイルのバイナリ

        Returns:
            ファイル名 -> CSV内容 の辞書
        """
        csv_files = {}
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                for name in zf.namelist():
                    if name.endswith(".csv"):
                        with zf.open(name) as f:
                            content = f.read()
                            # UTF-8 or Shift_JIS
                            try:
                                csv_files[name] = content.decode("utf-8")
                            except UnicodeDecodeError:
                                csv_files[name] = content.decode("cp932")
        except zipfile.BadZipFile:
            print(f"  警告: 無効なZIPファイル")
        return csv_files
