# クイックスタート

## 1. デモ実行（APIキー不要）

```bash
pip install requests
python demo_toyota.py
```

`output/toyota_7203_report.html` をブラウザで開くとレポートが表示されます。

## 2. 実データで分析

```bash
# APIキーを設定
export EDINET_API_KEY="あなたのAPIキー"

# 証券コードで実行
python main.py --sec-code 7203
```

APIキーは [EDINET](https://disclosure.edinet-fsa.go.jp/) で利用者登録後に発行できます。

## 主要オプション

| オプション | 説明 | 例 |
|-----------|------|-----|
| `--sec-code` | 証券コード | `--sec-code 6758` |
| `--company-name` | 企業名（部分一致） | `--company-name ソニー` |
| `--start` / `--end` | 検索期間 | `--start 2023-01-01` |
| `--types` | 書類種別 | `--types annual quarterly` |
| `-o` | 出力先 | `-o my_report.html` |
| `--no-open` | ブラウザ自動起動を無効化 | |
