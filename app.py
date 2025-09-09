import streamlit as st
import pandas as pd
import plotly.express as px

# アプリのタイトルを設定
st.title("利用者数グラフ化アプリ 📊")
st.markdown("---")

# データの入力セクション
st.header("データの入力")
st.write("測定日と利用者数を入力してください。")

# 空のデータフレームを作成
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["測定日", "利用者数"])

# 入力フォーム
col1, col2 = st.columns(2)
with col1:
    date = st.date_input("測定日")
with col2:
    users = st.number_input("利用者数", min_value=0, step=1)

# データを追加するボタン
if st.button("データ追加"):
    if users is not None:
        new_data = pd.DataFrame([{"測定日": date, "利用者数": users}])
        st.session_state.df = pd.concat([st.session_state.df, new_data], ignore_index=True)
        st.success("データが追加されました！")
    else:
        st.error("利用者数を入力してください。")

st.markdown("---")

# グラフの表示セクション
if not st.session_state.df.empty:
    st.header("グラフの表示")
    
    # 日付でソート
    df_sorted = st.session_state.df.sort_values(by="測定日")
    
    # グラフを作成
    fig = px.line(df_sorted, x="測定日", y="利用者数", title="利用者数の推移", markers=True)
    fig.update_layout(xaxis_title="測定日", yaxis_title="利用者数")
    
    # グラフを表示
    st.plotly_chart(fig)
else:
    st.info("データがありません。利用者数を入力してグラフを生成してください。")

st.markdown("---")

# データの表示セクション
if not st.session_state.df.empty:
    st.header("入力データ一覧")
    st.dataframe(st.session_state.df)
