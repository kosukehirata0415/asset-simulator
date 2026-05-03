import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime

# ページ全体の設定
st.set_page_config(page_title="資産推移予測シミュレーター", layout="wide")

# ★デザインの微調整（アイコンの統一感とUIの洗練）
st.markdown("""
<style>
    .stApp {
        font-family: 'Helvetica Neue', 'Hiragino Sans', 'Meiryo', sans-serif;
    }
    h1 {
        font-size: 1.8rem !important;
        text-align: center;
        margin-bottom: 2rem !important;
    }
    h3 {
        font-size: 1.3rem !important;
        font-weight: 600;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(20, 184, 166, 0.3);
        margin-top: 2.5rem !important;
        margin-bottom: 1.2rem !important;
    }
    /* メトリクスカードのデザイン */
    [data-testid="stMetric"] {
        border-radius: 12px;
        padding: 15px !important;
        border: 1px solid rgba(128, 128, 128, 0.15);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #14b8a6; 
        background-color: transparent; 
    }
    /* 入力金額のプレビュー */
    .amount-preview {
        font-size: 0.85rem;
        color: #14b8a6;
        font-weight: bold;
        margin-top: -15px;
        margin-bottom: 10px;
    }
    @media (max-width: 640px) {
        .main .block-container {
            padding: 1.5rem 0.8rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("💹 資産推移シミュレーター")

# ① CSVアップロード
uploaded_files = st.file_uploader("CSVファイルをアップロード（複数可）", type="csv", accept_multiple_files=True)

if uploaded_files:
    all_data = []
    for file in uploaded_files:
        try:
            df = pd.read_csv(file, header=1, encoding='shift_jis')
        except:
            df = pd.read_csv(file, header=1, encoding='utf-8')
        
        if '評価額(円)' in df.columns and '評価損益(円)' in df.columns and 'ファンド名' in df.columns:
            df = df[df['ファンド名'].notna()]
            df = df[~df['ファンド名'].astype(str).str.contains('該当データはありません')]
            df['評価額(円)'] = pd.to_numeric(df['評価額(円)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df['評価損益(円)'] = pd.to_numeric(df['評価損益(円)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df = df[df['評価額(円)'] > 0]
            all_data.append(df)

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # ② 資産状況ダッシュボード
        total_assets = combined_df['評価額(円)'].sum()
        total_profit = combined_df['評価損益(円)'].sum()
        total_principal = total_assets - total_profit
        profit_ratio = (total_profit / total_principal * 100) if total_principal > 0 else 0

        st.write("### 💰 現在の資産状況")
        col1, col2, col3 = st.columns(3)
        col1.metric("総資産額", f"{int(total_assets):,} 円")
        col2.metric("評価損益", f"{int(total_profit):,} 円", f"{profit_ratio:.1f}%")
        col3.metric("投資元本", f"{int(total_principal):,} 円")

        # ③ 資産構成比率（円グラフ）
        st.write("### 📊 資産構成比率")
        pie_df = combined_df.groupby('ファンド名')['評価額(円)'].sum().reset_index()
        fig_pie = go.Figure(data=[go.Pie(
            labels=pie_df['ファンド名'], 
            values=pie_df['評価額(円)'],
            hole=.4,
            marker=dict(colors=['#14b8a6', '#0ea5e9', '#6366f1', '#a855f7', '#ec4899', '#f59e0b']),
            textinfo='percent+label'
        )])
        fig_pie.update_layout(margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"), height=500, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

        # ④ 過去実績の分析
        st.write("### 🔍 過去実績の分析")
        col_calc1, col_calc2 = st.columns(2)
        start_date = col_calc1.date_input("運用開始日", datetime.date(2021, 1, 4))
        initial_asset = col_calc2.number_input("初期資産額（円）", min_value=0, value=780858, step=10000)
        col_calc2.markdown(f'<p class="amount-preview">確認：{initial_asset:,} 円</p>', unsafe_allow_html=True)

        today = datetime.date.today()
        invested_days = (today - start_date).days
        invested_years = invested_days / 365.25

        if invested_days > 0:
            past_cagr = (total_assets / total_principal) ** (1 / invested_years) - 1 if total_principal > 0 else 0
            st.info(f"💡 運用期間: **{invested_days}日** / 推定年利(CAGR): **{past_cagr * 100:.2f} %**")
        else:
            past_cagr = 0.0

        # ⑤ 保有ファンド詳細
        st.write("### 📑 保有ファンド詳細")
        display_df = combined_df[['ファンド名', '評価額(円)', '評価損益(円)', '評価損益率(％)']].copy()
        display_df['評価額(円)'] = display_df['評価額(円)'].apply(lambda x: f"{int(x):,}")
        display_df['評価損益(円)'] = display_df['評価損益(円)'].apply(lambda x: f"{int(x):,}")
        st.dataframe(display_df, hide_index=True, use_container_width=True)

        # ⑥ 今後の積立設定
        st.write("### ⚙️ 今後の積立設定")
        unique_funds = combined_df['ファンド名'].unique()
        total_monthly_investment = 0
        with st.expander("ファンドごとに金額を入力する", expanded=True):
            for fund in unique_funds:
                amount = st.number_input(f"{fund}", min_value=0, value=0, step=10000, key=fund)
                st.markdown(f'<p class="amount-preview">確認：{amount:,} 円</p>', unsafe_allow_html=True)
                total_monthly_investment += amount
        st.success(f"**合計積立額: {int(total_monthly_investment):,} 円 / 月**")

        # ⑦ 将来の資産予測
        st.write("### 🚀 将来の資産予測")
        
        forecast_years = st.slider("予測期間（年）を選択", min_value=1, max_value=40, value=20)
        
        rates = {"5%": 0.05, "7%": 0.07, "市場平均(8%)": 0.08, f"過去実績({past_cagr*100:.1f}%)": past_cagr}
        yearly_inv = total_monthly_investment * 12
        results_years = np.arange(0, forecast_years + 1)
        
        fig = go.Figure()
        colors = ['#94a3b8', '#2dd4bf', '#0ea5e9', '#0f766e']
        
        for i, (label, rate) in enumerate(rates.items()):
            assets = [total_assets]
            curr = total_assets
            for _ in range(forecast_years):
                curr = curr * (1 + rate) + yearly_inv
                assets.append(curr)
            
            fig.add_trace(go.Scatter(
                x=results_years, y=assets, name=label, mode='lines+markers',
                line=dict(width=3, color=colors[i]),
                marker=dict(size=6)
            ))

        fig.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title="経過年数（年）",
            yaxis_title="資産額（円）",
            hovermode="x unified",
            height=500,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        # ★修正：不要なレンジスライダーを非表示にしました
        fig.update_xaxes(
            dtick=1, 
            showgrid=True, 
            gridcolor='rgba(128,128,128,0.2)',
            rangeslider_visible=False # ここをFalseにすることで2個目のグラフのような枠を消去
        )
        fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
