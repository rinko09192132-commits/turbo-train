"""HTML レポート生成モジュール

Chart.js を使用したインタラクティブな決算分析レポートを生成する。
- 過去8四半期の推移チャート (売上高・営業利益・純利益)
- 主要指標テーブル
- セグメント別実績の棒グラフ＋テーブル
"""

import json
import os
from datetime import datetime

from analyzer import AnalysisResult
from config import OUTPUT_DIR


class HTMLReportGenerator:
    """決算分析HTMLレポートを生成する"""

    def generate(self, analysis: AnalysisResult, output_path: str = None) -> str:
        """分析結果からHTMLレポートを生成する

        Args:
            analysis: 分析結果
            output_path: 出力先パス (Noneの場合自動生成)

        Returns:
            生成したHTMLファイルのパス
        """
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = analysis.company_name.replace(" ", "_").replace("/", "_")
            output_path = os.path.join(OUTPUT_DIR, f"report_{safe_name}_{timestamp}.html")

        # チャートデータを構築
        trend_chart_data = self._build_trend_chart_data(analysis)
        segment_chart_data = self._build_segment_chart_data(analysis)

        html = self._render_html(analysis, trend_chart_data, segment_chart_data)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def _build_trend_chart_data(self, analysis: AnalysisResult) -> dict:
        """推移チャート用データを構築する"""
        # 表示対象の指標
        target_metrics = ["売上高", "売上収益", "営業収益", "営業利益", "経常利益",
                          "親会社帰属純利益", "当期純利益"]

        labels = []  # 期間ラベル
        datasets = {}

        for metric_label, metrics_list in analysis.quarterly_trends.items():
            if metric_label not in target_metrics:
                continue

            for m in metrics_list:
                period_label = self._format_period_label(m.period_end)
                if period_label not in labels:
                    labels.append(period_label)

            datasets[metric_label] = {
                "labels": [self._format_period_label(m.period_end) for m in metrics_list],
                "values": [m.value for m in metrics_list],
                "yoy": [m.yoy_change for m in metrics_list],
            }

        # ラベルをソート
        labels.sort()

        return {"labels": labels, "datasets": datasets}

    def _build_segment_chart_data(self, analysis: AnalysisResult) -> dict:
        """セグメントチャート用データを構築する"""
        if not analysis.segment_results:
            return {}

        # 最新期のセグメントデータを使用
        latest_period = sorted(analysis.segment_results.keys())[-1]
        segments = analysis.segment_results[latest_period]

        seg_names = [s.segment_name for s in segments]
        seg_data = {}

        for seg in segments:
            for metric_name, value in seg.metrics.items():
                if metric_name not in seg_data:
                    seg_data[metric_name] = []
                seg_data[metric_name].append(value)

        return {
            "period": latest_period,
            "names": seg_names,
            "metrics": seg_data,
        }

    def _format_period_label(self, period_end: str) -> str:
        """期末日を表示用ラベルに変換する"""
        if not period_end or len(period_end) < 7:
            return period_end
        try:
            dt = datetime.strptime(period_end[:10], "%Y-%m-%d")
            year = dt.year
            month = dt.month
            if month in (3, 4):
                return f"{year}年3月期"
            elif month in (6, 7):
                return f"{year}年 1Q"
            elif month in (9, 10):
                return f"{year}年 2Q"
            elif month in (12, 1):
                return f"{year}年 3Q"
            else:
                return f"{year}年{month}月"
        except ValueError:
            return period_end[:7]

    def _format_value_html(self, value: float) -> str:
        """数値をHTML用にフォーマットする"""
        if value >= 1_000_000:
            return f"{value / 1_000_000:,.0f}百万"
        elif value >= 1_000:
            return f"{value / 1_000:,.0f}千"
        else:
            return f"{value:,.0f}"

    def _render_html(
        self,
        analysis: AnalysisResult,
        trend_data: dict,
        segment_data: dict,
    ) -> str:
        """HTMLを生成する"""
        company = analysis.company_name or "不明"
        generated_at = datetime.now().strftime("%Y年%m月%d日 %H:%M")

        # 推移テーブルHTML
        trend_table_html = self._render_trend_table(analysis)

        # セグメントテーブルHTML
        segment_table_html = self._render_segment_table(analysis)

        # 警告
        warnings_html = ""
        if analysis.warnings:
            items = "".join(f"<li>{w}</li>" for w in analysis.warnings)
            warnings_html = f'<div class="warnings"><ul>{items}</ul></div>'

        # Chart.js用JSONデータ
        trend_json = json.dumps(trend_data, ensure_ascii=False, default=str)
        segment_json = json.dumps(segment_data, ensure_ascii=False, default=str)

        # カラーパレット
        colors = [
            "#2563eb", "#dc2626", "#16a34a", "#d97706",
            "#7c3aed", "#0891b2", "#be185d", "#65a30d",
        ]
        colors_json = json.dumps(colors)

        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{company} - 決算分析レポート</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', 'Meiryo', sans-serif;
    background: #f8fafc;
    color: #1e293b;
    line-height: 1.6;
}}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
header {{
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    color: white;
    padding: 32px 0;
    margin-bottom: 24px;
}}
header .container {{ display: flex; justify-content: space-between; align-items: center; }}
header h1 {{ font-size: 1.5rem; font-weight: 700; }}
header .meta {{ font-size: 0.85rem; opacity: 0.85; }}
.card {{
    background: white;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    padding: 24px;
    margin-bottom: 24px;
}}
.card h2 {{
    font-size: 1.15rem;
    font-weight: 700;
    color: #1e3a5f;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e2e8f0;
}}
.summary-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
}}
.summary-item {{
    background: #f1f5f9;
    border-radius: 8px;
    padding: 16px;
}}
.summary-item .label {{ font-size: 0.8rem; color: #64748b; margin-bottom: 4px; }}
.summary-item .value {{ font-size: 1.2rem; font-weight: 700; color: #1e293b; }}
.summary-item .yoy {{ font-size: 0.85rem; margin-top: 2px; }}
.yoy.positive {{ color: #16a34a; }}
.yoy.negative {{ color: #dc2626; }}
.chart-container {{
    position: relative;
    height: 400px;
    margin: 16px 0;
}}
.chart-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
}}
@media (max-width: 768px) {{
    .chart-row {{ grid-template-columns: 1fr; }}
    .chart-container {{ height: 300px; }}
}}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}}
th, td {{
    padding: 10px 12px;
    text-align: right;
    border-bottom: 1px solid #e2e8f0;
}}
th {{
    background: #f8fafc;
    font-weight: 600;
    color: #475569;
    position: sticky;
    top: 0;
}}
th:first-child, td:first-child {{ text-align: left; }}
tr:hover td {{ background: #f1f5f9; }}
.table-scroll {{ overflow-x: auto; }}
.warnings {{
    background: #fef3c7;
    border: 1px solid #f59e0b;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 24px;
}}
.warnings ul {{ margin-left: 20px; }}
.tab-nav {{
    display: flex;
    gap: 4px;
    margin-bottom: 16px;
    border-bottom: 2px solid #e2e8f0;
}}
.tab-btn {{
    padding: 8px 20px;
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 600;
    color: #64748b;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    transition: all 0.2s;
}}
.tab-btn.active {{
    color: #2563eb;
    border-bottom-color: #2563eb;
}}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}
footer {{
    text-align: center;
    color: #94a3b8;
    font-size: 0.8rem;
    padding: 24px 0;
}}
</style>
</head>
<body>

<header>
<div class="container">
    <div>
        <h1>{company}</h1>
        <div>決算分析レポート</div>
    </div>
    <div class="meta">
        生成日: {generated_at}<br>
        データソース: EDINET API v2
    </div>
</div>
</header>

<div class="container">

{warnings_html}

<!-- サマリ -->
<div class="card">
<h2>最新期 主要指標サマリ</h2>
<div class="summary-grid" id="summaryGrid"></div>
</div>

<!-- タブナビゲーション -->
<div class="card">
<div class="tab-nav">
    <button class="tab-btn active" onclick="switchTab('trends')">四半期推移</button>
    <button class="tab-btn" onclick="switchTab('segments')">セグメント別</button>
    <button class="tab-btn" onclick="switchTab('tables')">詳細テーブル</button>
</div>

<!-- 四半期推移タブ -->
<div class="tab-content active" id="tab-trends">
<h2>過去8四半期 業績推移</h2>
<div class="chart-row">
    <div>
        <div class="chart-container">
            <canvas id="revenueChart"></canvas>
        </div>
    </div>
    <div>
        <div class="chart-container">
            <canvas id="profitChart"></canvas>
        </div>
    </div>
</div>
<div class="chart-container" style="height:350px;">
    <canvas id="cashflowChart"></canvas>
</div>
</div>

<!-- セグメント別タブ -->
<div class="tab-content" id="tab-segments">
<h2>セグメント別実績</h2>
<div class="chart-row">
    <div>
        <div class="chart-container">
            <canvas id="segRevenueChart"></canvas>
        </div>
    </div>
    <div>
        <div class="chart-container">
            <canvas id="segProfitChart"></canvas>
        </div>
    </div>
</div>
{segment_table_html}
</div>

<!-- 詳細テーブルタブ -->
<div class="tab-content" id="tab-tables">
<h2>四半期推移 詳細</h2>
<div class="table-scroll">
{trend_table_html}
</div>
</div>

</div><!-- card -->
</div><!-- container -->

<footer>
EDINET決算分析ツール | データ: 金融庁 EDINET API v2
</footer>

<script>
const TREND_DATA = {trend_json};
const SEGMENT_DATA = {segment_json};
const COLORS = {colors_json};

// --- サマリ表示 ---
const summaryData = {json.dumps(analysis.latest_summary, ensure_ascii=False)};
const summaryGrid = document.getElementById('summaryGrid');
Object.entries(summaryData).forEach(([label, value]) => {{
    const match = value.match(/^(.+?)\\s*\\(([+-][\\d.]+%)\\)$/);
    let valueText = value;
    let yoyHtml = '';
    if (match) {{
        valueText = match[1];
        const pct = parseFloat(match[2]);
        const cls = pct >= 0 ? 'positive' : 'negative';
        yoyHtml = `<div class="yoy ${{cls}}">前年同期比: ${{match[2]}}</div>`;
    }}
    summaryGrid.innerHTML += `
        <div class="summary-item">
            <div class="label">${{label}}</div>
            <div class="value">${{valueText}}</div>
            ${{yoyHtml}}
        </div>`;
}});

// --- タブ切り替え ---
function switchTab(tabId) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active');
    event.target.classList.add('active');
}}

// --- チャート描画 ---
function createLineChart(canvasId, title, datasetConfigs) {{
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const datasets = [];
    let allLabels = new Set();

    datasetConfigs.forEach((cfg, i) => {{
        const ds = TREND_DATA.datasets[cfg.key];
        if (!ds) return;
        ds.labels.forEach(l => allLabels.add(l));
        datasets.push({{
            label: cfg.label || cfg.key,
            data: ds.values.map((v, idx) => ({{ x: ds.labels[idx], y: v / 1000000 }})),
            borderColor: COLORS[i % COLORS.length],
            backgroundColor: COLORS[i % COLORS.length] + '20',
            borderWidth: 2.5,
            pointRadius: 4,
            tension: 0.3,
            fill: cfg.fill || false,
        }});
    }});

    if (datasets.length === 0) return;

    allLabels = [...allLabels].sort();

    new Chart(ctx, {{
        type: 'line',
        data: {{ labels: allLabels, datasets }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                title: {{ display: true, text: title, font: {{ size: 14, weight: 'bold' }} }},
                tooltip: {{
                    callbacks: {{
                        label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.y.toLocaleString()}}百万円`
                    }}
                }}
            }},
            scales: {{
                y: {{
                    title: {{ display: true, text: '百万円' }},
                    ticks: {{ callback: v => v.toLocaleString() }}
                }}
            }}
        }}
    }});
}}

function createBarChart(canvasId, title, labels, datasetsConfig) {{
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const datasets = datasetsConfig.map((cfg, i) => ({{
        label: cfg.label,
        data: cfg.data.map(v => v / 1000000),
        backgroundColor: COLORS[i % COLORS.length] + 'cc',
        borderColor: COLORS[i % COLORS.length],
        borderWidth: 1,
    }}));

    new Chart(ctx, {{
        type: 'bar',
        data: {{ labels, datasets }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                title: {{ display: true, text: title, font: {{ size: 14, weight: 'bold' }} }},
                tooltip: {{
                    callbacks: {{
                        label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.y.toLocaleString()}}百万円`
                    }}
                }}
            }},
            scales: {{
                y: {{
                    title: {{ display: true, text: '百万円' }},
                    ticks: {{ callback: v => v.toLocaleString() }}
                }}
            }}
        }}
    }});
}}

// 売上推移チャート
createLineChart('revenueChart', '売上高/売上収益 推移', [
    {{ key: '売上高', label: '売上高' }},
    {{ key: '売上収益', label: '売上収益' }},
    {{ key: '営業収益', label: '営業収益' }},
]);

// 利益推移チャート
createLineChart('profitChart', '利益 推移', [
    {{ key: '営業利益', label: '営業利益' }},
    {{ key: '経常利益', label: '経常利益' }},
    {{ key: '親会社帰属純利益', label: '純利益' }},
    {{ key: '当期純利益', label: '当期純利益' }},
]);

// キャッシュフロー推移チャート
createLineChart('cashflowChart', 'キャッシュフロー 推移', [
    {{ key: '営業CF', label: '営業CF' }},
    {{ key: '投資CF', label: '投資CF' }},
    {{ key: '財務CF', label: '財務CF' }},
]);

// セグメント別チャート
if (SEGMENT_DATA.names && SEGMENT_DATA.names.length > 0) {{
    const segMetrics = SEGMENT_DATA.metrics || {{}};

    // 売上セグメント
    const revKeys = ['売上高', '売上収益'];
    const revData = revKeys.map(k => segMetrics[k]).find(d => d);
    if (revData) {{
        createBarChart('segRevenueChart', 'セグメント別 売上高', SEGMENT_DATA.names,
            [{{ label: '売上高', data: revData }}]);
    }}

    // 利益セグメント
    const profitKeys = ['営業利益', 'セグメント利益'];
    const profData = profitKeys.map(k => segMetrics[k]).find(d => d);
    if (profData) {{
        createBarChart('segProfitChart', 'セグメント別 利益', SEGMENT_DATA.names,
            [{{ label: '利益', data: profData }}]);
    }}
}}
</script>
</body>
</html>"""

    def _render_trend_table(self, analysis: AnalysisResult) -> str:
        """推移テーブルHTMLを生成する"""
        if not analysis.quarterly_trends:
            return "<p>推移データがありません</p>"

        # 全期間を収集
        all_periods = set()
        for metrics_list in analysis.quarterly_trends.values():
            for m in metrics_list:
                all_periods.add(m.period_end)
        sorted_periods = sorted(all_periods)[-8:]

        # ヘッダ
        header_cells = "<th>指標</th>"
        for p in sorted_periods:
            header_cells += f"<th>{self._format_period_label(p)}</th>"

        # 行
        rows_html = ""
        for label, metrics_list in analysis.quarterly_trends.items():
            period_map = {m.period_end: m for m in metrics_list}
            cells = f"<td><strong>{label}</strong></td>"
            for p in sorted_periods:
                m = period_map.get(p)
                if m:
                    val = self._format_value_html(m.value)
                    yoy = ""
                    if m.yoy_change is not None:
                        sign = "+" if m.yoy_change > 0 else ""
                        cls = "positive" if m.yoy_change >= 0 else "negative"
                        yoy = f'<br><span class="yoy {cls}">{sign}{m.yoy_change:.1f}%</span>'
                    cells += f"<td>{val}{yoy}</td>"
                else:
                    cells += "<td>-</td>"
            rows_html += f"<tr>{cells}</tr>"

        return f"""<table>
<thead><tr>{header_cells}</tr></thead>
<tbody>{rows_html}</tbody>
</table>"""

    def _render_segment_table(self, analysis: AnalysisResult) -> str:
        """セグメントテーブルHTMLを生成する"""
        if not analysis.segment_results:
            return "<p>セグメントデータがありません</p>"

        latest_period = sorted(analysis.segment_results.keys())[-1]
        segments = analysis.segment_results[latest_period]

        # 全指標名を収集
        all_metrics = set()
        for seg in segments:
            all_metrics.update(seg.metrics.keys())
        sorted_metrics = sorted(all_metrics)

        # ヘッダ
        header_cells = "<th>セグメント</th>"
        for m in sorted_metrics:
            header_cells += f"<th>{m}</th>"

        # 行
        rows_html = ""
        for seg in segments:
            cells = f"<td><strong>{seg.segment_name}</strong></td>"
            for m in sorted_metrics:
                val = seg.metrics.get(m)
                if val is not None:
                    cells += f"<td>{self._format_value_html(val)}</td>"
                else:
                    cells += "<td>-</td>"
            rows_html += f"<tr>{cells}</tr>"

        period_label = self._format_period_label(latest_period)
        return f"""<h3>セグメント別実績 ({period_label})</h3>
<div class="table-scroll">
<table>
<thead><tr>{header_cells}</tr></thead>
<tbody>{rows_html}</tbody>
</table>
</div>"""
