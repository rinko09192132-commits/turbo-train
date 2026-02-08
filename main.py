#!/usr/bin/env python3
"""EDINET 決算分析ツール

EDINET API v2 を利用して上場企業の決算データを取得し、
過去8四半期の推移やセグメント別実績をHTMLレポートとして出力する。

使い方:
    python main.py --sec-code 7203 --api-key YOUR_API_KEY
    python main.py --edinet-code E02144 --api-key YOUR_API_KEY
    python main.py --company-name トヨタ --api-key YOUR_API_KEY
    python main.py --sec-code 7203 --api-key YOUR_API_KEY --start 2023-01-01 --end 2025-12-31

環境変数:
    EDINET_API_KEY: APIキー (--api-key の代わりに設定可能)
"""

import argparse
import os
import sys
import time
import webbrowser

from analyzer import FinancialAnalyzer
from edinet_client import EdinetClient
from html_viewer import HTMLReportGenerator
from xbrl_parser import XBRLCSVParser


def main():
    parser = argparse.ArgumentParser(
        description="EDINET 決算分析ツール - 上場企業の決算データを分析しHTMLレポートを生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 証券コードで検索 (トヨタ自動車)
  python main.py --sec-code 7203 --api-key YOUR_KEY

  # EDINET コードで検索
  python main.py --edinet-code E02144 --api-key YOUR_KEY

  # 企業名で検索 (部分一致)
  python main.py --company-name ソニー --api-key YOUR_KEY

  # 期間を指定
  python main.py --sec-code 7203 --api-key YOUR_KEY --start 2023-01-01 --end 2025-12-31

  # レポートを自動でブラウザで開かない
  python main.py --sec-code 7203 --api-key YOUR_KEY --no-open
        """,
    )

    # 企業指定 (いずれか1つ必須)
    company_group = parser.add_mutually_exclusive_group(required=True)
    company_group.add_argument("--sec-code", help="証券コード (例: 7203)")
    company_group.add_argument("--edinet-code", help="EDINETコード (例: E02144)")
    company_group.add_argument("--company-name", help="企業名 (部分一致)")

    # API設定
    parser.add_argument(
        "--api-key",
        default=os.environ.get("EDINET_API_KEY"),
        help="EDINET API キー (環境変数 EDINET_API_KEY でも設定可)",
    )

    # 期間
    parser.add_argument("--start", help="検索開始日 (YYYY-MM-DD)")
    parser.add_argument("--end", help="検索終了日 (YYYY-MM-DD)")

    # 出力
    parser.add_argument("-o", "--output", help="出力HTMLファイルパス")
    parser.add_argument(
        "--no-open", action="store_true", help="レポートをブラウザで自動的に開かない"
    )

    # 書類種別
    parser.add_argument(
        "--types",
        nargs="+",
        default=["annual", "quarterly", "semi_annual"],
        choices=["annual", "quarterly", "semi_annual"],
        help="取得する書類種別 (デフォルト: 全種別)",
    )

    args = parser.parse_args()

    # APIキーチェック
    if not args.api_key:
        print("エラー: APIキーが指定されていません。")
        print("  --api-key オプションまたは環境変数 EDINET_API_KEY を設定してください。")
        print("  APIキーは https://disclosure.edinet-fsa.go.jp/ で取得できます。")
        sys.exit(1)

    print("=" * 60)
    print("EDINET 決算分析ツール")
    print("=" * 60)

    # 1. EDINET API クライアント初期化
    client = EdinetClient(api_key=args.api_key)

    # 2. 書類検索
    print("\n[1/4] 書類を検索しています...")
    filings = client.search_company_filings(
        sec_code=args.sec_code,
        edinet_code=args.edinet_code,
        company_name=args.company_name,
        start_date=args.start,
        end_date=args.end,
        filing_types=args.types,
    )

    if not filings:
        print("\n該当する書類が見つかりませんでした。")
        print("検索条件を変更して再度お試しください。")
        sys.exit(0)

    # 書類一覧表示
    print("\n見つかった書類:")
    for i, doc in enumerate(filings, 1):
        print(
            f"  {i}. {doc.get('_filingTypeLabel', '不明')} "
            f"({doc.get('periodEnd', 'N/A')}) "
            f"- {doc.get('filerName', 'N/A')} "
            f"[{doc.get('docID', '')}]"
        )

    # 3. CSVデータ取得＆パース
    print(f"\n[2/4] 財務データを取得しています... ({len(filings)}件)")
    csv_parser = XBRLCSVParser()
    parsed_filings = []

    for i, doc in enumerate(filings):
        doc_id = doc.get("docID")
        if not doc_id:
            continue

        print(f"  取得中: {doc.get('_filingTypeLabel', '')} ({doc.get('periodEnd', '')})...", end="")
        try:
            zip_data = client.download_csv_data(doc_id)
            csv_files = client.extract_csv_files(zip_data)

            if csv_files:
                parsed = csv_parser.parse_csv_files(csv_files, doc_info=doc)
                parsed_filings.append(parsed)
                print(f" OK ({len(csv_files)}ファイル, {len(parsed.items)}項目)")
            else:
                print(" CSVデータなし")

            time.sleep(0.3)  # API負荷軽減
        except Exception as e:
            print(f" エラー: {e}")

    if not parsed_filings:
        print("\n財務データを取得できませんでした。")
        sys.exit(1)

    # 4. 分析
    print(f"\n[3/4] 分析しています...")
    analyzer = FinancialAnalyzer()
    analysis = analyzer.analyze(parsed_filings)

    # 分析結果サマリ表示
    if analysis.latest_summary:
        print("\n--- 最新期 主要指標 ---")
        for label, value in analysis.latest_summary.items():
            print(f"  {label}: {value}")

    if analysis.segment_results:
        latest_period = sorted(analysis.segment_results.keys())[-1]
        segments = analysis.segment_results[latest_period]
        print(f"\n--- セグメント ({latest_period}) ---")
        for seg in segments:
            metrics_str = ", ".join(f"{k}: {v:,.0f}" for k, v in seg.metrics.items())
            print(f"  {seg.segment_name}: {metrics_str}")

    if analysis.warnings:
        print("\n--- 警告 ---")
        for w in analysis.warnings:
            print(f"  * {w}")

    # 5. HTMLレポート生成
    print(f"\n[4/4] HTMLレポートを生成しています...")
    generator = HTMLReportGenerator()
    output_path = generator.generate(analysis, output_path=args.output)
    abs_path = os.path.abspath(output_path)
    print(f"  レポート生成完了: {abs_path}")

    # ブラウザで開く
    if not args.no_open:
        try:
            webbrowser.open(f"file://{abs_path}")
            print("  ブラウザでレポートを開きました")
        except Exception:
            print(f"  ブラウザで開くには: file://{abs_path}")

    print("\n完了!")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
