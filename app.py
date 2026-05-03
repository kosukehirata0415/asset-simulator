import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import zipfile
import io

# ページ全体の設定
st.set_page_config(page_title="資産推移予測シミュレーター", layout="wide")

# ★デザインの調整
st.markdown("""
<style>
    .stApp {
        font-family: 'Helvetica Neue', 'Hiragino Sans', 'Meiryo', sans-serif;
    }
    h1 {
        font-size: 1.6rem !important;
        text-align: center;
        margin-bottom: 1.5rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetric"] {
        border-radius: 12px;
        padding: 15px !important;
        border: 1px solid rgba(128, 128, 128, 0.15);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #14b8a6; 
        background-color: transparent; 
    }
    [data-testid="stMetric"] > div {
        display: flex !important;
        flex-direction: row !important;
        align-items: baseline !important;
        gap: 10px !important;
        flex-wrap: wrap !important;
    }
    [data-testid="stMetricLabel"] {
        width: 100% !important;
        margin-bottom: 4px !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }
    .amount-preview {
        font-size: 0.85rem;
        color: #14b8a6;
        font-weight: bold;
        margin-top: -15px;
        margin-bottom: 10px;
    }
    .reach-metric [data-testid="stMetric"] {
        border-left: 5px solid #f43f5e;
        background-color: rgba(244, 63, 94, 0.05);
    }
    @media (max-width: 640px) {
        .main .block-container {
            padding: 1rem 0.5rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("💹 資産推移シミュレーター")

# ★CSVデータ読み込み・整形処理を共通関数化
def process_csv_data(file_content):
    try:
        # まずはShift-JISで読み込み
        df = pd.read_csv(io.BytesIO(file_content), header=1, encoding='shift_jis')
    except:
        # エラーが出たらUTF-8でリトライ
        df = pd.read_csv(io.BytesIO(file_content), header=1, encoding='utf-8')
        
    if '評価額(円)' in df.columns and '評価損益(円)' in df.columns and 'ファンド名' in df.columns:
        df = df[df['ファンド名'].notna()]
        df = df[~df['ファンド名'].astype(str).str.contains('該当データはありません')]
        df['評価額(円)'] = pd.to_numeric(df['評価額(円)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        df['評価損益(円)'] = pd.to_numeric(df['評価損益(円)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        if '口座区分' not in df.columns:
            df['口座区分'] = '不明'
            
        df = df[df['評価額(円)'] > 0]
        return df
    return None

# ① ファイルアップロード（CSVとZIPの両方に対応）
uploaded_files = st.file_uploader("CSVまたはZIPファイルをアップロード（複数可）", type=["csv", "zip"], accept_multiple_files=True)

if uploaded_files:
    all_data = []
    
    # ★ZIP展開とCSV読み込みの処理
    for file in uploaded_files:
        if file.name.lower().endswith('.zip'):
            # ZIPファイルの場合の処理
            with zipfile.ZipFile(file) as z:
                for filename in z.namelist():
                    # Macの隠しファイル等を除外し、CSVだけを処理
                    if filename.lower().endswith('.csv') and '__MACOSX' not in filename:
                        with z.open(filename) as f:
                            file_content = f.read()
                            df = process_csv_data(file_content)
                            if df is not None:
                                all_data.append(df)
        elif file.name.lower().endswith('.csv'):
            # 単体のCSVファイルの場合の処理
            file_content = file.read()
            df = process_csv_data(file_content)
            if df is not None:
                all_data.append(df)

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # --- 事前計算 ---
        total_assets = combined_df['評価額(円)'].sum()
        total_profit = combined_df['評価損益(円)'].sum()
        total_principal = total_assets - total_profit
        profit_ratio = (total_profit / total_principal * 100) if total_principal > 0 else 0

        # --- タブの作成 ---
        tab1, tab2, tab3, tab4 = st.tabs(["💰 現在の資産", "📑 分析・詳細", "🚀 将来予測", "🤖 AIアドバイザー"])

        # 【タブ1：現在の資産】
        with tab1:
            st.write("### 💰 資産状況")
            col1, col2, col3 = st.columns(3)
            col1.metric("総資産額", f"{int(total_assets):,} 円")
            col2.metric("評価損益", f"{int(total_profit):,} 円", f"{profit_ratio:.1f}%")
            col3.metric("投資元本", f"{int(total_principal):,} 円")

            st.write("### 📊 資産構成比率")
            pie_df = combined_df.groupby('ファンド名')['評価額(円)'].sum().reset_index()
            fig_pie = go.Figure(data=[go.Pie(
                labels=pie_df['ファンド名'], values=pie_df['評価額(円)'], hole=.4,
                marker=dict(colors=['#14b8a6', '#0ea5e9', '#6366f1', '#a855f7', '#ec4899', '#f59e0b']),
                textinfo='percent+label', textposition='outside', insidetextorientation='horizontal' 
            )])
            fig_pie.update_layout(margin=dict(l=50, r=50, t=30, b=80), legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"), height=550, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)

        # 【タブ2：分析・詳細】
        with tab2:
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

            st.write("### 📑 保有ファンド詳細")
            display_df = combined_df[['ファンド名', '口座区分', '評価額(円)', '評価損益(円)', '評価損益率(％)']].copy()
            display_df['評価額(円)'] = display_df['評価額(円)'].apply(lambda x: f"{int(x):,}")
            display_df['評価損益(円)'] = display_df['評価損益(円)'].apply(lambda x: f"{int(x):,}")
            st.dataframe(display_df, hide_index=True, use_container_width=True)

        # 【タブ3：将来予測と目標達成】
        with tab3:
            today = datetime.date.today()
            invested_years = (today - start_date).days / 365.25
            past_cagr = (total_assets / total_principal) ** (1 / invested_years) - 1 if total_principal > 0 and invested_years > 0 else 0

            st.write("### ⚙️ 積立・目標設定")
            target_amount = st.number_input("🎯 目標とする資産額を設定（円）", min_value=1000000, value=100000000, step=10000000)
            st.markdown(f'<p class="amount-preview">確認：{target_amount:,} 円</p>', unsafe_allow_html=True)

            unique_funds = combined_df['ファンド名'].unique()
            total_monthly_investment = 0
            with st.expander("ファンド別の積立額を入力する", expanded=True):
                for fund in unique_funds:
                    amount = st.number_input(f"{fund}", min_value=0, value=0, step=10000, key=f"input_{fund}")
                    st.markdown(f'<p class="amount-preview">確認：{amount:,} 円</p>', unsafe_allow_html=True)
                    total_monthly_investment += amount
            st.success(f"**合計積立額: {int(total_monthly_investment):,} 円 / 月**")

            st.write("### 🚀 将来の資産予測")
            forecast_years = st.slider("予測期間（年）を選択", min_value=1, max_value=40, value=20)
            
            rates = {"5%": 0.05, "7%": 0.07, "市場平均(8%)": 0.08, f"過去実績({past_cagr*100:.1f}%)": past_cagr}
            yearly_inv = total_monthly_investment * 12
            results_years = np.arange(0, forecast_years + 1)
            reach_years = {}
            
            fig = go.Figure()
            colors = ['#94a3b8', '#2dd4bf', '#0ea5e9', '#0f766e']
            for i, (label, rate) in enumerate(rates.items()):
                assets = [total_assets]
                curr = total_assets
                reached = False
                for y in range(1, forecast_years + 1):
                    curr = curr * (1 + rate) + yearly_inv
                    assets.append(curr)
                    if not reached and curr >= target_amount:
                        reach_years[label] = y
                        reached = True
                if not reached: reach_years[label] = "-"
                fig.add_trace(go.Scatter(x=results_years, y=assets, name=label, mode='lines+markers', line=dict(width=3, color=colors[i]), marker=dict(size=6)))

            fig.add_hline(y=target_amount, line_dash="dash", line_color="#f43f5e", annotation_text=f" 目標: {target_amount/10000:,.0f}万円", annotation_position="top left", annotation_font=dict(color="#f43f5e", size=12))
            fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), xaxis_title="経過年数（年）", yaxis_title="資産額（円）", hovermode="x unified", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig.update_xaxes(dtick=1, showgrid=True, gridcolor='rgba(128,128,128,0.2)', rangeslider_visible=False)
            fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            st.write("#### 🚩 目標到達予定時期")
            st.markdown('<div class="reach-metric">', unsafe_allow_html=True)
            cols = st.columns(4)
            for i, (label, year) in enumerate(reach_years.items()):
                if year == "-":
                    cols[i].metric(label, "到達せず")
                else:
                    cols[i].metric(label, f"{year} 年後")
            st.markdown('</div>', unsafe_allow_html=True)

        # 【タブ4：🤖 AIアドバイザー】
        with tab4:
            st.write("### 🤖 ポートフォリオ診断アドバイス")
            
            us_keywords = ['Ｓ＆Ｐ５００', '米国', 'S&P500']
            global_keywords = ['オール・カントリー', '全世界']
            us_amount = combined_df[combined_df['ファンド名'].str.contains('|'.join(us_keywords), na=False)]['評価額(円)'].sum()
            us_ratio = (us_amount / total_assets) * 100 if total_assets > 0 else 0
            specific_amount = combined_df[~combined_df['口座区分'].str.contains('NISA|非課税', na=False)]['評価額(円)'].sum()

            with st.chat_message("assistant"):
                st.write(f"現在の総資産 **{total_assets:,.0f}円** に基づく客観的な分析レポートです。素晴らしい資産形成のペースですが、より盤石にするためのポイントをまとめました。")
                
                st.markdown("#### 🇺🇸 資産の分散状況について")
                if us_ratio > 60:
                    st.write(f"現在、ポートフォリオの **約{us_ratio:.0f}%** が米国株（S&P500等）で構成されています。S&P500は世界最強のインデックスの一つであり、これまでの高いリターンの原動力となっています。")
                    st.write("一方で、特定の国に資産が集中しているのは事実です。今後の積立で『オール・カントリー』の比率を高めるご予定は、将来的な米国経済の停滞や為替変動（極端な円高など）に対する**非常に賢明なリスクヘッジ**となります。")
                else:
                    st.write("特定の国や地域に偏りすぎず、バランスの取れたアセットアロケーションが構築できています。")

                st.markdown("#### 🏦 特定口座の取り扱いとNISA活用")
                if specific_amount > 0:
                    st.write(f"現在、特定口座に **約{specific_amount/10000:,.0f}万円** の資産があります。評価益がかなり大きいため、**これを無理に売却してNISAに移そうとすると、約20%の税金が引かれてしまい、複利の運用資金を減らしてしまうデメリット**があります。")
                    st.write("そのため、特定口座の資産は無理に動かさず**『そのまま長期保有（ガチホ）』**するのがセオリーです。今後の新しい積立資金を、新NISA枠（年間最大360万円）に優先的に投入していく戦略を徹底してください。")
                else:
                    st.write("NISA枠を非常に効率的に活用できています。引き続き非課税の恩恵を最大限に活かしましょう。")

                st.markdown("#### 📈 将来の利回りとリスク管理")
                st.write(f"過去の推定年利が非常に高い水準ですが、これはご自身の『暴落時にも売らずに積み立てた握力』と、近年の『歴史的な株高・円安』の相乗効果によるものです。")
                st.write("投資の世界では、いつか必ず厳しい調整局面（下落相場）が訪れます。将来予測は保守的な**年利5%〜7%**程度で見積もっておき、資産が半減しても生活に困らないよう、現金の確保（生活防衛資金）もしっかり行っておきましょう。")

                st.markdown("---")
                st.write("**💡 総評**")
                st.write("王道のインデックスファンドを低コストで長期保有するという、投資の最適解をすでに実践されています。焦って方針を変える必要はありません。今のペースで淡々と積立を継続することが、目標達成への一番の近道です。")
