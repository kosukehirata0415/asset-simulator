import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ページ全体の設定
st.set_page_config(page_title="資産推移予測シミュレーター", layout="wide")

# ★スマホ最適化＆スタイリッシュなカスタムCSS
st.markdown("""
<style>
    /* 全体の背景と基本フォント */
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
    }
    
    /* タイトルのモバイル調整 */
    h1 {
        color: #1E293B;
        font-size: 1.8rem !important;
        text-align: center;
        padding-bottom: 1rem;
    }
    
    /* セクション見出しの調整 */
    h3 {
        color: #334155;
        font-size: 1.3rem !important;
        border-left: 5px solid #3B82F6;
        padding-left: 10px;
        margin-top: 2rem !important;
    }

    /* メトリクス（数字）をカード風のデザインに */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 15px !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border: 1px solid #E2E8F0;
    }

    /* スマホ画面（幅640px以下）での調整 */
    @media (max-width: 640px) {
        .stMetric {
            margin-bottom: 10px;
        }
        /* 表の文字を少し小さくして視認性アップ */
        .stDataFrame {
            font-size: 0.8rem;
        }
        /* 全体のパディングを調整 */
        .main .block-container {
            padding: 1rem 0.5rem !important;
        }
    }

    /* 入力フォームのラベル調整 */
    .stNumberInput label {
        font-weight: bold;
        color: #475569;
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 資産推移シミュレーター")

# ① CSVアップロード
uploaded_files = st.file_uploader("CSVファイルをアップロード", type="csv", accept_multiple_files=True)

if uploaded_files:
    all_data = []
    for file in uploaded_files:
        try:
            df = pd.read_csv(file, header=1, encoding='shift_jis')
        except:
            df = pd.read_csv(file, header=1, encoding='utf-8')
        
        if '評価額(円)' in df.columns and '評価損益(円)' in df.columns:
            df['評価額(円)'] = pd.to_numeric(df['評価額(円)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df['評価損益(円)'] = pd.to_numeric(df['評価損益(円)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            all_data.append(df)

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # ② 資産状況ダッシュボード
        total_assets = combined_df['評価額(円)'].sum()
        total_profit = combined_df['評価損益(円)'].sum()
        total_principal = total_assets - total_profit
        profit_ratio = (total_profit / total_principal * 100) if total_principal > 0 else 0

        st.write("### 💎 現在の資産状況")
        # スマホでは自動的に縦に並ぶ
        col1, col2, col3 = st.columns(3)
        col1.metric("総資産額", f"{int(total_assets):,} 円")
        col2.metric("評価損益", f"{int(total_profit):,} 円", f"{profit_ratio:.1f}%")
        col3.metric("投資元本", f"{int(total_principal):,} 円")

        # ④ 過去の実績利回り計算
        st.write("### 📊 過去の実績から利回りを計算")
        invested_years = st.number_input("運用年数（目安）を入力", min_value=0.1, value=5.0, step=0.5)

        if total_principal > 0 and invested_years > 0:
            past_cagr = (total_assets / total_principal) ** (1 / invested_years) - 1
        else:
            past_cagr = 0.0
        
        st.info(f"💡 推定年利: **{past_cagr * 100:.2f} %**")

        # 保有ファンド一覧
        st.write("### 💼 保有ファンド一覧")
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
        colors = ['#94A3B8', '#3B82F6', '#2563EB', '#1E40AF']
        
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

        # グラフのモバイル最適化
        fig.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title="年数",
            yaxis_title="資産額",
            hovermode="x unified",
            height=450,
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
