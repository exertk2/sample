import pandas as pd
import streamlit as st

st.title("Streamlit DataFrame with 1-based Index")

# データを作成
data = {'col1': [10, 20, 30], 'col2': [100, 200, 300]}
df = pd.DataFrame(data)

st.subheader("Original DataFrame (0-based index)")
st.dataframe(df)

# インデックスを1から始めるようにシフト
df.index += 1

st.subheader("DataFrame with 1-based index (using df.index += 1)")
st.dataframe(df)
