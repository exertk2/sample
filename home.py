# Home.py
import streamlit as st

st.set_page_config(
    page_title="Streamlit ナビゲーションサンプル",
    page_icon="🏠",
    layout="centered"
)

st.title("ようこそ！")
st.write("これはStreamlitのナビゲーション機能のサンプルアプリです。")
st.write("左側のサイドバーから他のページに移動できます。")

st.info("このアプリは `st.navigation` を使用してページを管理しています。")

# 必要であれば、ここにホームページのコンテンツを追加
st.write("---")
st.header("メインコンテンツ")
st.write("ここにホームページの主要な情報を表示します。")
