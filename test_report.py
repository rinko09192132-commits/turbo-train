#!/usr/bin/env python3
"""サンプルデータでHTMLレポート生成をテストする"""

from analyzer import AnalysisResult, FinancialAnalyzer, QuarterlyMetric, SegmentMetric
from html_viewer import HTMLReportGenerator
from xbrl_parser import FinancialItem, ParsedFinancials, SegmentData


def create_sample_filings() -> list[ParsedFinancials]:
    """テスト用のサンプル財務データを作成する"""
    filings = []

    # 8四半期分のデータ
    periods = [
        ("2024-03-31", "annual"),
        ("2024-06-30", "quarterly"),
        ("2024-09-30", "quarterly"),
        ("2024-12-31", "quarterly"),
        ("2025-03-31", "annual"),
        ("2025-06-30", "quarterly"),
        ("2025-09-30", "quarterly"),
        ("2025-12-31", "quarterly"),
    ]

    # 売上高の推移 (百万円単位)
    revenues = [
        3_200_000, 850_000, 1_700_000, 2_600_000,
        3_500_000, 920_000, 1_850_000, 2_800_000,
    ]
    op_incomes = [
        320_000, 85_000, 175_000, 260_000,
        380_000, 98_000, 195_000, 290_000,
    ]
    net_incomes = [
        220_000, 55_000, 115_000, 175_000,
        260_000, 65_000, 130_000, 195_000,
    ]
    total_assets = [
        8_500_000, 8_600_000, 8_700_000, 8_800_000,
        9_000_000, 9_100_000, 9_200_000, 9_400_000,
    ]
    op_cf = [
        450_000, 120_000, 250_000, 380_000,
        500_000, 135_000, 270_000, 420_000,
    ]
    inv_cf = [
        -280_000, -75_000, -150_000, -230_000,
        -310_000, -80_000, -160_000, -250_000,
    ]
    fin_cf = [
        -150_000, -40_000, -80_000, -120_000,
        -170_000, -45_000, -90_000, -140_000,
    ]

    for i, (period_end, filing_type) in enumerate(periods):
        items = [
            FinancialItem("NetSales", "売上高", f"CurrentYearDuration", str(revenues[i]),
                          period="current_duration"),
            FinancialItem("OperatingIncome", "営業利益", f"CurrentYearDuration", str(op_incomes[i]),
                          period="current_duration"),
            FinancialItem("ProfitLossAttributableToOwnersOfParent", "親会社帰属純利益",
                          f"CurrentYearDuration", str(net_incomes[i]),
                          period="current_duration"),
            FinancialItem("TotalAssets", "総資産", f"CurrentYearInstant", str(total_assets[i]),
                          period="current_instant"),
            FinancialItem("NetCashProvidedByUsedInOperatingActivities", "営業CF",
                          f"CurrentYearDuration", str(op_cf[i]),
                          period="current_duration"),
            FinancialItem("NetCashProvidedByUsedInInvestingActivities", "投資CF",
                          f"CurrentYearDuration", str(inv_cf[i]),
                          period="current_duration"),
            FinancialItem("NetCashProvidedByUsedInFinancingActivities", "財務CF",
                          f"CurrentYearDuration", str(fin_cf[i]),
                          period="current_duration"),
        ]

        # セグメントデータ (年次のみ)
        segments = []
        if filing_type == "annual":
            segments = [
                SegmentData("自動車", "NetSales", "売上高", revenues[i] * 0.65, "current"),
                SegmentData("金融", "NetSales", "売上高", revenues[i] * 0.20, "current"),
                SegmentData("その他", "NetSales", "売上高", revenues[i] * 0.15, "current"),
                SegmentData("自動車", "OperatingIncome", "営業利益", op_incomes[i] * 0.70, "current"),
                SegmentData("金融", "OperatingIncome", "営業利益", op_incomes[i] * 0.25, "current"),
                SegmentData("その他", "OperatingIncome", "営業利益", op_incomes[i] * 0.05, "current"),
            ]

        filing = ParsedFinancials(
            doc_id=f"S100TEST{i:02d}",
            company_name="テスト株式会社",
            period_end=period_end,
            filing_type=filing_type,
            items=items,
            segments=segments,
        )
        filings.append(filing)

    return filings


def main():
    print("サンプルデータでテスト実行...")

    # 1. サンプルデータ作成
    filings = create_sample_filings()
    print(f"  サンプル書類数: {len(filings)}")

    # 2. 分析
    analyzer = FinancialAnalyzer()
    analysis = analyzer.analyze(filings)
    print(f"  四半期推移指標数: {len(analysis.quarterly_trends)}")
    print(f"  セグメント期間数: {len(analysis.segment_results)}")

    # サマリ表示
    print("\n  --- 最新期サマリ ---")
    for label, value in analysis.latest_summary.items():
        print(f"    {label}: {value}")

    # セグメント表示
    for period, segments in analysis.segment_results.items():
        print(f"\n  --- セグメント ({period}) ---")
        for seg in segments:
            metrics_str = ", ".join(f"{k}: {v:,.0f}" for k, v in seg.metrics.items())
            print(f"    {seg.segment_name}: {metrics_str}")

    # 3. HTMLレポート生成
    generator = HTMLReportGenerator()
    output_path = generator.generate(analysis, output_path="output/test_report.html")
    print(f"\n  レポート生成完了: {output_path}")
    print("テスト完了!")


if __name__ == "__main__":
    main()
