import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="資産推移予測シミュレーター", layout="wide")

st.title("📈 資産推移予測シミュレーター")

# ① CSV一式をアップロードする
uploaded_files = st.file_uploader("残高一覧のCSVファイルをアップロードしてください（複数可）", type="csv", accept_multiple_files=True)

if uploaded_files:
    all_data = []
    
    for file in uploaded_files:
        try:
            df = pd.read_csv(file, header=1, encoding='shift_jis')
        except:
            df = pd.read_csv(file, header=1, encoding='utf-8')
        
        # 必要な列があるデータだけを抽出・数値化
        if '評価額(円)' in df.columns and '評価損益(円)' in df.columns and 'ファンド名' in df.columns:
            # カンマなどが含まれている場合を考慮して数値に変換
            df['評価額(円)'] = pd.to_numeric(df['評価額(円)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df['評価損益(円)'] = pd.to_numeric(df['評価損益(円)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            all_data.append(df)

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # ② 最初に総資産額と投資成績（損益）を表示する
        total_assets = combined_df['評価額(円)'].sum()
        total_profit = combined_df['評価損益(円)'].sum()
        total_principal = total_assets - total_profit
        profit_ratio = (total_profit / total_principal * 100) if total_principal > 0 else 0

        st.write("---")
        st.write("### 💎 現在の資産状況")
        col1, col2, col3 = st.columns(3)
        # ① 金額にカンマ区切りをつけて表示
        col1.metric("総資産額", f"{int(total_assets):,} 円")
        col2.metric("評価損益", f"{int(total_profit):,} 円", f"{profit_ratio:.2f}%")
        col3.metric("投資元本", f"{int(total_principal):,} 円")

        # ④ 過去の投資成績（年利）を計算する
        st.write("---")
        st.write("### 📊 過去の実績利回りの計算")
        st.write("※CSVには運用期間のデータがないため、おおよその運用年数を入力して実績利回り（年利）を逆算します。")
        invested_years = st.number_input("これまでの運用年数を入力してください（年）", min_value=0.1, value=5.0, step=0.5)

        # CAGR（年平均成長率）の計算
        if total_principal > 0 and invested_years > 0:
            past_cagr = (total_assets / total_principal) ** (1 / invested_years) - 1
        else:
            past_cagr = 0.0
        
        st.info(f"💡 過去の投資成績ベースの想定利回り（年利）: **{past_cagr * 100:.2f} %**")

        st.write("---")
        st.write("### 💼 保有ファンド一覧")
        # ファンド一覧の表示（カンマ区切り設定）
        display_df = combined_df[['ファンド名', '評価額(円)', '評価損益(円)', '評価損益率(％)']].copy()
        st.dataframe(
            display_df,
            column_config={
                "評価額(円)": st.column_config.NumberColumn(format="%d"),
                "評価損益(円)": st.column_config.NumberColumn(format="%d"),
            },
            hide_index=True
        )

        # ③ 積み立て額はファンド毎に入力できるようにする
        st.write("---")
        st.write("### 💰 今後のファンド別 積立金額設定")
        unique_funds = combined_df['ファンド名'].unique()
        
        monthly_investments = {}
        for fund in unique_funds:
            # わかりやすいようにファンドごとの入力欄を生成
            monthly_investments[fund] = st.number_input(f"【{fund}】 の毎月積立額 (円)", min_value=0, value=0, step=10000)

        total_monthly_investment = sum(monthly_investments.values())
        st.success(f"**毎月の合計積立額: {int(total_monthly_investment):,} 円**")

        yearly_investment = total_monthly_investment * 12
        years = 20

        # パターン別の将来予測
        st.write("---")
        st.write("### 📈 20年後の資産推移予測")
        
        rates = {
            "パターン① (利回り5%)": 0.05,
            "パターン② (利回り7%)": 0.07,
            "パターン③ (市場平均: 8%)": 0.08,
            f"パターン④ (過去実績ベース: {past_cagr*100:.1f}%)": past_cagr
        }

        results = {'経過年数': np.arange(0, years + 1)}
        for name, rate in rates.items():
            assets = [total_assets]
            current_asset = total_assets
            for _ in range(years):
                current_asset = current_asset * (1 + rate) + yearly_investment
                assets.append(current_asset)
            results[name] = assets

        results_df = pd.DataFrame(results)

        # グラフ描画
        fig = go.Figure()
        for name in rates.keys():
            fig.add_trace(go.Scatter(x=results_df['経過年数'], y=results_df[name], mode='lines+markers', name=name))
        
        fig.update_layout(xaxis_title='経過年数 (年)', yaxis_title='想定資産額 (円)', hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
