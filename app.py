import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import plotly.express as px
import numpy as np

# --- 1. データ準備 (サンプルデータ) ---
# 実際のデータに置き換えてください
@st.cache_data
def load_data():
    # 鹿児島市の区や町を想定したサンプル地区名
    districts = ['中央町', '天文館', '鴨池', '谷山', '伊敷', '桜ヶ丘']
    
    # 2015年から2024年までの月ごとの人口データを生成
    # 実際にはCSVなどからロードします
    data = []
    for year in range(2015, 2025):
        for month in range(1, 13):
            date_str = f"{year}-{month:02d}"
            for district in districts:
                # ランダムな人口データを生成（増減をシミュレート）
                base_pop = 5000 + np.random.randint(-1000, 1000)
                change = np.random.randint(-50, 50) # 月ごとの微細な変化
                population = base_pop + (year - 2015) * 100 + change # 年々増加傾向の例
                data.append({'年月': date_str, '地区名': district, '人口': max(1000, int(population))}) # 最低人口設定

    df = pd.DataFrame(data)
    
    # 年月のdatetime型変換
    df['年月'] = pd.to_datetime(df['年月'])
    
    # 地区ごとの緯度経度データ (これも仮のデータ、実際はGeocodingなどが必要)
    # 鹿児島市役所付近を中心としたランダムな位置
    geo_data = {
        '中央町': {'lat': 31.5959, 'lon': 130.5586},
        '天文館': {'lat': 31.5901, 'lon': 130.5562},
        '鴨池': {'lat': 31.5650, 'lon': 130.5470},
        '谷山': {'lat': 31.5000, 'lon': 130.4900},
        '伊敷': {'lat': 31.6200, 'lon': 130.5400},
        '桜ヶ丘': {'lat': 31.5400, 'lon': 130.5200}
    }
    
    return df, geo_data

df, geo_data = load_data()

# --- 2. Streamlit UI ---
st.title('鹿児島市 人口増減ダッシュボード')
st.write('年月スライダーを動かして、各地区の人口変動を見てみよう！')

# 年月スライダー
# データフレームからユニークな年月を取得し、ソート
unique_months = sorted(df['年月'].unique())
selected_month_idx = st.slider(
    '年月を選択',
    0, len(unique_months) - 1, len(unique_months) - 1, # 初期値を最新月に設定
    format_func=lambda x: unique_months[x].strftime('%Y年%m月')
)
selected_date = unique_months[selected_month_idx]

st.subheader(f'選択中の年月: {selected_date.strftime("%Y年%m月")}')

# --- 3. 地図の表示 ---
st.subheader('地図上の人口増減')

# 選択された年月のデータにフィルタリング
df_filtered = df[df['年月'] == selected_date]

# 各地区の緯度経度を結合
df_map = pd.DataFrame(columns=['地区名', '人口', 'lat', 'lon'])
for index, row in df_filtered.iterrows():
    district = row['地区名']
    if district in geo_data:
        df_map = pd.concat([df_map, pd.DataFrame([{
            '地区名': district,
            '人口': row['人口'],
            'lat': geo_data[district]['lat'],
            'lon': geo_data[district]['lon']
        }])], ignore_index=True)

# 地図の中心を鹿児島市役所付近に設定
map_center = [31.5960, 130.5580]
m = folium.Map(location=map_center, zoom_start=12)

# マーカークラスターで人口を表示（棒グラフの代替表現）
# 人口の増減をマーカーの色やサイズで表現することも可能
# ここでは人口が多いほどマーカーの色を濃くする例
min_pop = df_map['人口'].min()
max_pop = df_map['人口'].max()

for idx, row in df_map.iterrows():
    # 人口に応じた色のグラデーション（例: 青系のグラデーション）
    normalized_pop = (row['人口'] - min_pop) / (max_pop - min_pop)
    color_val = int(255 * (1 - normalized_pop)) # 人口が多いほど暗い青
    color_hex = f'#{color_val:02x}{color_val:02x}FF' # BGR形式

    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=np.log(row['人口'] / 1000) * 5, # 人口に応じて円の大きさを調整（対数スケールで変化を緩やかに）
        color=color_hex,
        fill=True,
        fill_color=color_hex,
        fill_opacity=0.7,
        tooltip=f"{row['地区名']}: 人口 {row['人口']}人"
    ).add_to(m)

# Streamlitに地図を表示
st.write(m._repr_html_(), unsafe_allow_html=True)

# --- 4. 人口推移グラフ (棒グラフ) ---
st.subheader('選択地区の人口推移')

# 全期間の人口推移グラフ
# ここでは全ての地区の人口を合計して表示する例
df_total_pop_over_time = df.groupby('年月')['人口'].sum().reset_index()

fig_line = px.line(df_total_pop_over_time, 
                   x='年月', 
                   y='人口', 
                   title='鹿児島市全体の人口推移')
fig_line.update_layout(xaxis_title="年月", yaxis_title="人口")
st.plotly_chart(fig_line, use_container_width=True)

# 地区ごとの人口推移を見るための選択ボックス
selected_district = st.selectbox('詳細を見たい地区を選択', df['地区名'].unique())

if selected_district:
    df_district_pop = df[df['地区名'] == selected_district].sort_values('年月')
    
    # 棒グラフで人口を表示
    fig_bar = px.bar(df_district_pop, 
                     x='年月', 
                     y='人口', 
                     title=f'{selected_district}の人口推移')
    fig_bar.update_layout(xaxis_title="年月", yaxis_title="人口")
    st.plotly_chart(fig_bar, use_container_width=True)

