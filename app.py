import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ページ全体の設定
st.set_page_config(page_title="資産推移予測シミュレーター", layout="wide")

# ★洗練されたミニマル・デザインのCSS
st.markdown("""
<style>
    .stApp {
        font-family: 'Helvetica Neue', 'Hiragino Sans', 'Meiryo', sans-serif;
    }
    h3 {
        font-size: 1.4rem !important;
        font-weight: 600;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(20, 184, 166, 0.3);
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
    }
    [data-testid="stMetric"] {
        border-radius: 8px;
        padding: 15px !important;
        border: 1px solid rgba(128, 128, 128, 0.2);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #14b8a6; 
        background-color: transparent; 
    }
    @media (max-width: 640px) {
        .main .block-container {
            padding: 2rem 1rem !important;
        }
        .stDataFrame {
            font-size: 0.85rem;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 資産推移シミュレーター")

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
            
            # ★修正箇所：「該当データはありません」などの不要な行を除外する
            df = df[df['ファンド名'].notna()]
            df = df[~df['ファンド名'].astype(str).str.contains('該当データはありません')]

            df['評価額(円)'] = pd.to_numeric(df['評価額(円)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df['評価損益(円)'] = pd.to_numeric(df['評価損益(円)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            # 評価額が0円のものもノイズになるため除外
            df = df[df['評価額(円)'] > 0]
            
            all_data.append(df)

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # ② 資産状況ダッシュボード
        total_assets = combined_df['評価額(円)'].sum()
        total_profit = combined_df['評価損益(円)'].sum()
        total_principal = total_assets - total_profit
        profit_ratio = (total_profit / total_principal * 100) if total_principal > 0 else 0

        st.write("### 💎 現在の資産状況")
        col1, col2, col3 = st.columns(3)
        col1.metric("総資産額", f"{int(total_assets):,} 円")
        col2.metric("評価損益", f"{int(total_profit):,} 円", f"{profit_ratio:.1f}%")
        col3.metric("投資元本", f"{int(total_principal):,} 円")

        # ポートフォリオの円グラフ
        st.write("### 🍰 ポートフォリオ内訳")
        pie_df = combined_df.groupby('ファンド名')['評価額(円)'].sum().reset_index()
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=pie_df['ファンド名'], 
            values=pie_df['評価額(円)'],
            hole=.4,
            marker=dict(colors=['#14b8a6', '#0ea5e9', '#6366f1', '#a855f7', '#ec4899', '#f59e0b']),
            textinfo='percent+label',
            insidetextorientation='radial'
        )])
        
        fig_pie.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            height=500,
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        # ④ 過去の実績利回り計算
        st.write("### 📊 過去の実績から利回りを計算")
        invested_years = st.number_input("運用年数（目安）を入力", min_value=0.1, value=5.0, step=0.5)

        if total_principal > 0 and invested_years > 0:
            past_cagr = (total_assets / total_principal) ** (1 / invested_years) - 1
        else:
            past_cagr = 0.0
        
        st.info(f"💡 推定年利: **{past_cagr * 100:.2f} %**")

        # 保有ファンド一覧
        st.write("### 💼 保有ファンド詳細")
        display_df = combined_df[['ファンド名', '評価額(円)', '評価損益(円)', '評価損益率(％)']].copy()
        display_df['評価額(円)'] = display_df['評価額(円)'].apply(lambda x: f"{int(x):,}")
        display_df['評価損益(円)'] = display_df['評価損益(円)'].apply(lambda x: f"{int(x):,}")
        st.dataframe(display_df, hide_index=True, use_container_width=True)

        # ③ ファンド別 積立設定
        st.write("### 💰 今後の積立設定")
        unique_funds = combined_df['ファンド名'].unique()
        
        total_monthly_investment = 0
        with st.expander("ファンドごとに金額を入力する", expanded=True):
            for fund in unique_funds:
                amount = st.number_input(f"{fund}", min_value=0, value=0, step=10000, key=fund)
                total_monthly_investment += amount

        st.success(f"**合計積立額: {int(total_monthly_investment):,} 円 / 月**")

        # 将来予測
        st.write("### 📈 20年後の資産推移")
        
        rates = {
            "5%": 0.05,
            "7%": 0.07,
            "市場平均(8%)": 0.08,
            f"過去実績({past_cagr*100:.1f}%)": past_cagr
        }

        years = 20
        yearly_inv = total_monthly_investment * 12
        results = {'年': np.arange(0, years + 1)}
        
        fig = go.Figure()
        colors = ['#94a3b8', '#2dd4bf', '#0ea5e9', '#0f766e']
        
        for i, (label, rate) in enumerate(rates.items()):
            assets = [total_assets]
            curr = total_assets
            for _ in range(years):
                curr = curr * (1 + rate) + yearly_inv
                assets.append(curr)
            
            fig.add_trace(go.Scatter(
                x=results['年'], y=assets, name=label,
                line=dict(width=3, color=colors[i]),
                marker=dict(size=4)
            ))

        fig.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title="年数",
            yaxis_title="資産額",
            hovermode="x unified",
            height=450,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
