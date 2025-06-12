import pandas as pd
import streamlit as st

st.title("Streamlit DataFrame with 1-based Index (after reset_index)")

# データを作成
data = {'col1': [10, 20, 30, 40, 50], 'col2': [100, 200, 300, 400, 500]}
df_original = pd.DataFrame(data)

st.subheader("Original DataFrame")
st.dataframe(df_original)

# 特定の条件でフィルタリング（インデックスが飛び飛びになる）
df_filtered = df_original[df_original['col1'] > 20]

st.subheader("Filtered DataFrame (original index preserved)")
st.dataframe(df_filtered)

# インデックスをリセットして0から始まるようにし、その後1から始めるようにシフト
df_reset_shifted = df_filtered.reset_index(drop=True)
df_reset_shifted.index += 1

st.subheader("Filtered DataFrame with 1-based index (after reset_index and shift)")
st.dataframe(df_reset_shifted)
