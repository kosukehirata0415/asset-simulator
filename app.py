import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="資産推移予測シミュレーター", layout="wide")

st.title("📈 資産推移予測シミュレーター")
st.write("SBI証券の残高CSVをアップロードして、将来の資産を予測します。")

# ① CSV一式をアップロードする
uploaded_files = st.file_uploader("残高一覧のCSVファイルをアップロードしてください（複数可）", type="csv", accept_multiple_files=True)

if uploaded_files:
    total_assets = 0
    all_data = []

    # ② CSVから投資しているファンド一覧と資産推移を描画する
    for file in uploaded_files:
        # SBI証券のCSVは1行目にタイトルがあるため、2行目をヘッダーとして読み込む
        try:
            df = pd.read_csv(file, header=1, encoding='shift_jis')
        except:
            # エンコーディングエラー時のフォールバック
            df = pd.read_csv(file, header=1, encoding='utf-8')
        
        # 評価額の列を探して合計を計算
        if '評価額(円)' in df.columns:
            total_assets += df['評価額(円)'].sum()
            all_data.append(df)

    if all_data:
        st.success(f"読み込み完了！現在の総資産額: {total_assets:,.0f} 円")
        
        # データフレームを結合して表示
        combined_df = pd.concat(all_data, ignore_index=True)
        st.write("### 💼 保有ファンド一覧")
        st.dataframe(combined_df[['ファンド名', '評価額(円)', '評価損益(円)', '評価損益率(％)']])

        # ③ 今後積み立てる金額を入力する
        st.write("### 💰 今後の積立シミュレーション")
        monthly_investment = st.number_input("毎月の積立金額を入力してください（円）", min_value=0, value=170000, step=10000)
        yearly_investment = monthly_investment * 12
        years = 20

        # ④ 4つのパターンで将来予測する
        st.write("### 📊 20年後の資産推移予測")
        
        # 各パターンの年利設定
        rates = {
            "パターン① (利回り5%)": 0.05,
            "パターン② (利回り7%)": 0.07,
            "パターン③ (市場平均: 8%)": 0.08,
            "パターン④ (過去実績ベース: 12%)": 0.12 # 過去分析から12%を設定
        }

        # シミュレーション計算
        results = {'経過年数': np.arange(0, years + 1)}
        for name, rate in rates.items():
            assets = [total_assets]
            current_asset = total_assets
            for _ in range(years):
                # 1年ごとの複利計算（簡易版: 年初一括投資として計算）
                current_asset = current_asset * (1 + rate) + yearly_investment
                assets.append(current_asset)
            results[name] = assets

        results_df = pd.DataFrame(results)

        # グラフ描画 (Plotly)
        fig = go.Figure()
        for name in rates.keys():
            fig.add_trace(go.Scatter(x=results_df['経過年数'], y=results_df[name], mode='lines+markers', name=name))
        
        fig.update_layout(xaxis_title='経過年数 (年)', yaxis_title='想定資産額 (円)', hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
