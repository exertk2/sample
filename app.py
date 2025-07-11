import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.express as px
import numpy as np
import datetime

# --- 1. データ準備 (サンプルデータ) ---
# 実際のデータに置き換えてください
@st.cache_data
def load_data():
    # 鹿児島市の区や町を想定したサンプル地区名
    districts = ['中央町', '天文館', '鴨池', '谷山', '伊敷', '桜ヶ丘']
    
    # 2015年1月から現在までの月ごとの人口データを生成
    # 実際にはCSVなどからロードします
    data = []
    # 現在の日付を取得
    current_date = datetime.date.today() # 実行時点の最新日付
    
    for year in range(2015, current_date.year + 1):
        for month in range(1, 13):
            # 現在の年月を超えないように調整
            if year == current_date.year and month > current_date.month:
                break
            
            date_str = f"{year}-{month:02d}"
            for district in districts:
                # ランダムな人口データを生成（増減をシミュレート）
                # 初期人口と年ごとの傾向
                initial_pop = np.random.randint(4000, 7000)
                yearly_change = np.random.randint(-50, 150) # 年々増加傾向の例
                
                # 月ごとの微細な変動
                monthly_fluctuation = np.random.randint(-100, 100)
                
                # 人口計算
                population = initial_pop + (year - 2015) * yearly_change + monthly_fluctuation
                
                # 最低人口を設定（極端な減少を防ぐ）
                population = max(1000, int(population)) 
                
                data.append({'年月': date_str, '地区名': district, '人口': population})

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

if len(unique_months) == 0:
    st.error("利用可能な年月データがありません。データ準備部分を確認してください。")
    st.stop() # データがない場合はここで処理を停止
else:
    # スライダーのmin/max/初期値
    min_slider_val = 0
    max_slider_val = len(unique_months) - 1
    default_slider_val = len(unique_months) - 1 # 最新月を初期値に

    # format_funcを明示的に定義
    def format_slider_date(x):
        return unique_months[x].strftime('%Y年%m月')

    selected_month_idx = st.slider(
        '年月を選択',
        min_value=min_slider_val,
        max_value=max_slider_val,
        value=default_slider_val,
        # ここを format_func から format に修正しました！
        format=format_slider_date 
    )

selected_date = unique_months[selected_month_idx]

st.subheader(f'選択中の年月: {selected_date.strftime("%Y年%m月")}')

st.markdown("---")

# --- 3. 地図の表示 ---
st.subheader('地図上の人口変動')

# 選択された年月のデータにフィルタリング
df_filtered = df[df['年月'] == selected_date]

# 各地区の緯度経度を結合
df_map = pd.DataFrame(columns=['地区名', '人口', 'lat', 'lon'])
for index, row in df_filtered.iterrows():
    district = row['地区名']
    if district in geo_data:
        df_map.loc[len(df_map)] = [
            district,
            row['人口'],
            geo_data[district]['lat'],
            geo_data[district]['lon']
        ]

# 地図の中心を鹿児島市役所付近に設定
map_center = [31.5960, 130.5580]
m = folium.Map(location=map_center, zoom_start=12)

# 人口に応じて円のサイズと色を変更するマーカーを追加
if not df_map.empty: # データが空でないことを確認
    min_pop = df_map['人口'].min()
    max_pop = df_map['人口'].max()

    for idx, row in df_map.iterrows():
        # 人口に応じた色のグラデーション（例: 青系のグラデーション）
        # 人口が少ないほど明るい青、多いほど濃い青
        # 0.0-1.0に正規化し、それを255に掛けて色を計算
        normalized_pop = (row['人口'] - min_pop) / (max_pop - min_pop) if (max_pop - min_pop) > 0 else 0.5
        color_val_r = int(255 * (1 - normalized_pop))
        color_val_g = int(255 * (1 - normalized_pop))
        color_val_b = 255 # 青を強調
        color_hex = f'#{color_val_r:02x}{color_val_g:02x}{color_val_b:02x}'

        # 人口に応じて円の大きさを調整（対数スケールで変化を緩やかに）
        # 最低人口を1000として、半径を計算
        radius = np.log(max(row['人口'], 1000) / 1000) * 5 + 5 # 最低半径を5に設定
        radius = max(5, radius) # 半径が小さくなりすぎないように

        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=radius,
            color=color_hex,
            fill=True,
            fill_color=color_hex,
            fill_opacity=0.7,
            tooltip=f"{row['地区名']}: 人口 {row['人口']}人"
        ).add_to(m)

# Streamlitに地図を表示 (folium_staticを使用)
folium_static(m)

st.markdown("---")

## 4. 人口推移グラフ (棒グラフ)

st.subheader('選択地区の人口推移')

# 全期間の人口推移グラフ
# ここでは全ての地区の人口を合計して表示する例
df_total_pop_over_time = df.groupby('年月')['人口'].sum().reset_index()

fig_line = px.line(df_total_pop_over_time, 
                   x='年月', 
                   y='人口', 
                   title='鹿児島市全体の人口推移')
fig_line.update_layout(xaxis_title="年月", yaxis_title="人口", hovermode="x unified")
st.plotly_chart(fig_line, use_container_width=True)

# 地区ごとの人口推移を見るための選択ボックス
selected_district = st.selectbox('詳細を見たい地区を選択', df['地区名'].unique())

if selected_district:
    df_district_pop = df[df['地区名'] == selected_district].sort_values('年月')
    
    # 棒グラフで人口を表示
    fig_bar = px.bar(df_district_pop, 
                     x='年月', 
                     y='人口', 
                     title=f'{selected_district}の人口推移',
                     labels={'年月': '年月', '人口': '人口'})
    fig_bar.update_layout(xaxis_title="年月", yaxis_title="人口")
    st.plotly_chart(fig_bar, use_container_width=True)
