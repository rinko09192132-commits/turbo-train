# EDINET 決算分析ツール

EDINET API v2 を利用して上場企業の決算データを取得・分析し、インタラクティブな HTML レポートを生成するツール。

## 機能

- 証券コード / EDINETコード / 企業名 で企業を検索
- 有価証券報告書・四半期報告書・半期報告書を自動取得
- 過去8四半期の業績推移をチャート表示（売上・利益・CF）
- セグメント別実績の棒グラフ＋テーブル表示
- 前年同期比の自動算出
- 取得データのローカルキャッシュ

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install requests
```

Python 3.11 以上が必要です。

### 2. EDINET API キーの取得

EDINET API は 2024年4月よりAPIキーが必須です。

1. [EDINET](https://disclosure.edinet-fsa.go.jp/) にアクセス
2. 「利用者登録」からアカウントを作成
3. ログイン後「API設定」画面で Subscription Key を発行

### 3. API キーの設定

環境変数で設定する方法（推奨）:

```bash
export EDINET_API_KEY="あなたのAPIキー"
```

または `.env` ファイルに記載して `source` する方法:

```bash
echo 'export EDINET_API_KEY="あなたのAPIキー"' > .env
source .env
```

## 使い方

### 基本コマンド

```bash
# 証券コードで検索（トヨタ自動車）
python main.py --sec-code 7203

# EDINETコードで検索
python main.py --edinet-code E02144

# 企業名で検索（部分一致）
python main.py --company-name ソニー
```

### オプション

```bash
# APIキーをコマンドラインで指定
python main.py --sec-code 7203 --api-key YOUR_KEY

# 検索期間を指定
python main.py --sec-code 7203 --start 2023-01-01 --end 2025-12-31

# 出力ファイルパスを指定
python main.py --sec-code 7203 -o report.html

# ブラウザで自動的に開かない
python main.py --sec-code 7203 --no-open

# 有価証券報告書のみ取得
python main.py --sec-code 7203 --types annual

# 四半期報告書のみ取得
python main.py --sec-code 7203 --types quarterly
```

### デモ実行（APIキー不要）

```bash
# サンプルデータでテスト
python test_report.py

# トヨタ自動車のデモレポート生成
python demo_toyota.py
```

## 出力レポートの構成

生成される HTML レポートは3つのタブで構成されています。

| タブ | 内容 |
|------|------|
| 四半期推移 | 売上高・利益・キャッシュフローの折れ線チャート |
| セグメント別 | セグメント別の売上高・利益の棒グラフ＋テーブル |
| 詳細テーブル | 全指標の8四半期数値一覧（前年同期比付き） |

## ファイル構成

```
├── main.py             # CLI エントリポイント
├── edinet_client.py    # EDINET API v2 クライアント
├── xbrl_parser.py      # CSV (XBRL) パーサー
├── analyzer.py         # 財務分析モジュール
├── html_viewer.py      # HTML レポート生成
├── config.py           # 設定・定数定義
├── requirements.txt    # 依存パッケージ
├── test_report.py      # サンプルデータテスト
├── demo_toyota.py      # トヨタ自動車デモ
└── output/             # 生成レポート出力先
```

## 対応する書類種別

| 種別 | 府令コード | 様式コード |
|------|-----------|-----------|
| 有価証券報告書 | 010 | 030000 |
| 四半期報告書 | 010 | 043000 |
| 半期報告書 | 010 | 050000 |

## 注意事項

- EDINET API のデータ保存期間は10年間です。それ以前のデータは取得できません。
- API の利用にあたっては [EDINET の利用規約](https://disclosure.edinet-fsa.go.jp/) を遵守してください。
- 取得済みデータは `data/cache/` にキャッシュされます。キャッシュを削除するには同ディレクトリを削除してください。
