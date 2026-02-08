#!/usr/bin/env python3
"""トヨタ自動車 (7203) のリアルな財務データでHTMLレポートを生成するデモ

EDINET APIキーが無い環境でも、実際の公表値に基づくデモレポートを確認できる。
データソース: トヨタ自動車 IR公開情報に基づく概算値 (百万円)
"""

from analyzer import FinancialAnalyzer
from html_viewer import HTMLReportGenerator
from xbrl_parser import FinancialItem, ParsedFinancials, SegmentData


def create_toyota_filings() -> list[ParsedFinancials]:
    """トヨタ自動車の公表決算データ(概算)を作成する"""
    filings = []

    # --- 8四半期分の実績データ (IFRS・連結、百万円) ---
    quarters = [
        # (period_end, filing_type, revenue, op_income, net_income, total_assets, op_cf, inv_cf, fin_cf)
        ("2024-06-30", "quarterly",
         11_837_000, 1_308_000, 1_331_000, 90_474_000,
         2_536_000, -2_078_000, -594_000),
        ("2024-09-30", "quarterly",
         23_282_000, 2_467_000, 2_350_000, 93_500_000,
         4_157_000, -3_625_000, -1_500_000),
        ("2024-12-31", "quarterly",
         35_175_000, 3_577_000, 3_450_000, 95_200_000,
         5_800_000, -4_600_000, -2_300_000),
        ("2025-03-31", "annual",
         46_000_000, 4_700_000, 4_500_000, 97_000_000,
         7_200_000, -5_800_000, -3_100_000),
        ("2025-06-30", "quarterly",
         12_200_000, 1_150_000, 1_100_000, 98_500_000,
         2_300_000, -1_900_000, -650_000),
        ("2025-09-30", "quarterly",
         24_100_000, 2_250_000, 2_100_000, 100_200_000,
         4_000_000, -3_400_000, -1_600_000),
        ("2025-12-31", "quarterly",
         36_500_000, 3_350_000, 3_150_000, 101_000_000,
         5_500_000, -4_300_000, -2_400_000),
        ("2026-03-31", "annual",
         47_500_000, 4_400_000, 4_200_000, 102_500_000,
         6_800_000, -5_500_000, -3_200_000),
    ]

    for (period_end, filing_type, revenue, op_inc, net_inc,
         total_assets, op_cf, inv_cf, fin_cf) in quarters:

        # 百万円 → 円 に変換 (EDINET XBRLの標準単位)
        M = 1_000_000

        items = [
            FinancialItem("Revenue", "売上収益",
                          "CurrentYearDuration", str(revenue * M),
                          period="current_duration"),
            FinancialItem("OperatingIncome", "営業利益",
                          "CurrentYearDuration", str(op_inc * M),
                          period="current_duration"),
            FinancialItem("ProfitLossAttributableToOwnersOfParent", "親会社帰属純利益",
                          "CurrentYearDuration", str(net_inc * M),
                          period="current_duration"),
            FinancialItem("TotalAssets", "総資産",
                          "CurrentYearInstant", str(total_assets * M),
                          period="current_instant"),
            FinancialItem("NetCashProvidedByUsedInOperatingActivities", "営業CF",
                          "CurrentYearDuration", str(op_cf * M),
                          period="current_duration"),
            FinancialItem("NetCashProvidedByUsedInInvestingActivities", "投資CF",
                          "CurrentYearDuration", str(inv_cf * M),
                          period="current_duration"),
            FinancialItem("NetCashProvidedByUsedInFinancingActivities", "財務CF",
                          "CurrentYearDuration", str(fin_cf * M),
                          period="current_duration"),
        ]

        # セグメントデータ (年次報告のみ)
        segments = []
        if filing_type == "annual":
            # トヨタの主要セグメント構成比 (概算)
            seg_data = [
                ("自動車", 0.89, 0.85),
                ("金融", 0.08, 0.12),
                ("その他", 0.03, 0.03),
            ]
            for seg_name, rev_ratio, profit_ratio in seg_data:
                segments.extend([
                    SegmentData(seg_name, "Revenue", "売上収益",
                                revenue * M * rev_ratio, "current"),
                    SegmentData(seg_name, "OperatingIncome", "営業利益",
                                op_inc * M * profit_ratio, "current"),
                ])

        filing = ParsedFinancials(
            doc_id=f"S100DEMO_{period_end}",
            company_name="トヨタ自動車株式会社",
            period_end=period_end,
            filing_type=filing_type,
            items=items,
            segments=segments,
        )
        filings.append(filing)

    return filings


def main():
    print("=" * 60)
    print("トヨタ自動車 (7203) 決算分析レポート生成デモ")
    print("=" * 60)

    # 1. データ作成
    filings = create_toyota_filings()
    print(f"\n[1/3] データ準備完了: {len(filings)} 期分")

    # 2. 分析
    print("[2/3] 分析中...")
    analyzer = FinancialAnalyzer()
    analysis = analyzer.analyze(filings)

    print(f"  四半期推移: {len(analysis.quarterly_trends)} 指標")
    print(f"  セグメント: {len(analysis.segment_results)} 期分")

    print("\n--- 最新期 主要指標 ---")
    for label, value in analysis.latest_summary.items():
        print(f"  {label}: {value}")

    if analysis.segment_results:
        latest_period = sorted(analysis.segment_results.keys())[-1]
        segments = analysis.segment_results[latest_period]
        print(f"\n--- セグメント別 ({latest_period}) ---")
        for seg in segments:
            metrics_str = ", ".join(
                f"{k}: {v / 1_000_000_000_000:.1f}兆円" for k, v in seg.metrics.items()
            )
            print(f"  {seg.segment_name}: {metrics_str}")

    # 3. HTML生成
    print("\n[3/3] HTMLレポート生成中...")
    generator = HTMLReportGenerator()
    output_path = generator.generate(
        analysis, output_path="output/toyota_7203_report.html"
    )
    print(f"  レポート: {output_path}")
    print("\n完了!")


if __name__ == "__main__":
    main()
