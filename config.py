"""EDINET決算分析ツール 設定"""

# EDINET API v2
EDINET_API_BASE = "https://api.edinet-fsa.go.jp/api/v2"
DOCUMENTS_LIST_URL = f"{EDINET_API_BASE}/documents.json"
DOCUMENT_URL = f"{EDINET_API_BASE}/documents"

# 書類タイプコード
# ordinanceCode="010" = 企業内容等の開示に関する内閣府令
# formCode: 030000=有価証券報告書, 043000=四半期報告書, 050000=半期報告書
DOC_TYPES = {
    "annual": {"ordinanceCode": "010", "formCode": "030000", "label": "有価証券報告書"},
    "quarterly": {"ordinanceCode": "010", "formCode": "043000", "label": "四半期報告書"},
    "semi_annual": {"ordinanceCode": "010", "formCode": "050000", "label": "半期報告書"},
}

# 取得タイプ (書類取得API)
# type=1: 提出本文書及び監査報告書
# type=2: PDFファイル
# type=3: 代替書面・添付文書
# type=4: 英文ファイル
# type=5: CSV (XBRLデータをCSV変換)
DOWNLOAD_TYPE_CSV = 5

# 主要財務項目 (XBRL要素ID)
FINANCIAL_ELEMENTS = {
    # 売上・収益
    "NetSales": "売上高",
    "Revenue": "売上収益",
    "NetSalesOfCompletedConstructionContracts": "完成工事高",
    "OperatingRevenue1": "営業収益",
    # 利益
    "OperatingIncome": "営業利益",
    "OrdinaryIncome": "経常利益",
    "ProfitLossAttributableToOwnersOfParent": "親会社株主に帰属する当期純利益",
    "ProfitLoss": "当期純利益",
    # 資産
    "TotalAssets": "総資産",
    "NetAssets": "純資産",
    # キャッシュフロー
    "NetCashProvidedByUsedInOperatingActivities": "営業CF",
    "NetCashProvidedByUsedInInvestingActivities": "投資CF",
    "NetCashProvidedByUsedInFinancingActivities": "財務CF",
    # その他
    "NumberOfEmployees": "従業員数",
}

# セグメント関連XBRL要素パターン
SEGMENT_ELEMENTS = {
    "NetSales": "売上高",
    "Revenue": "売上収益",
    "OperatingIncome": "営業利益",
    "OrdinaryIncome": "経常利益",
    "SegmentProfitLoss": "セグメント利益",
    "SegmentAssets": "セグメント資産",
}

# データ保存ディレクトリ
DATA_DIR = "data"
CACHE_DIR = "data/cache"
OUTPUT_DIR = "output"
