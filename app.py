import streamlit as st
import pandas as pd
import numpy as np

st.title('製品評価データのグラフ化')

st.write("""
このアプリケーションは、架空の製品評価データを生成し、
それを棒グラフと折れ線グラフで視覚化します。
""")

# 1. 評価データの生成
# 製品A, B, Cの3ヶ月間の評価点（1〜5点）を想定
products = ['製品A', '製品B', '製品C']
months = ['1月', '2月', '3月']

data = {
    '製品': np.repeat(products, len(months)),
    '月': np.tile(months, len(products)),
    '評価点': np.random.randint(1, 6, size=len(products) * len(months)) # 1から5までのランダムな整数
}
df = pd.DataFrame(data)

st.subheader('評価データテーブル')
st.dataframe(df)

# 2. 製品ごとの平均評価点を計算
st.subheader('製品ごとの平均評価点')
avg_ratings = df.groupby('製品')['評価点'].mean().reset_index()
st.dataframe(avg_ratings)

# 3. 棒グラフで製品ごとの平均評価点を表示
st.write('#### 製品ごとの平均評価点の棒グラフ')
st.bar_chart(avg_ratings.set_index('製品'))

# 4. 月ごとの製品評価の推移
st.subheader('月ごとの製品評価推移')

# ピボットテーブルを作成して、月をインデックス、製品をカラムにする
pivot_df = df.pivot_table(index='月', columns='製品', values='評価点')
st.dataframe(pivot_df)

# 5. 折れ線グラフで月ごとの評価推移を表示
st.write('#### 月ごとの製品評価推移の折れ線グラフ')
st.line_chart(pivot_df)

st.write("""
**グラフの読み方:**
* **棒グラフ:** 各製品が平均してどのくらいの評価を得ているかを示します。
* **折れ線グラフ:** 各製品の評価が時間（月）とともにどのように変化したかを示します。
""")

# 追加のインタラクション（オプション）
st.sidebar.subheader('評価点のフィルタリング')
min_rating = st.sidebar.slider(
    '表示する最低評価点',
    min_value=1,
    max_value=5,
    value=3
)
filtered_df = df[df['評価点'] >= min_rating]
st.sidebar.write(f'評価点が{min_rating}点以上のデータ数: {len(filtered_df)}')
st.sidebar.dataframe(filtered_df)

st.sidebar.write("---")
st.sidebar.info("このアプリはデモンストレーション用です。")
