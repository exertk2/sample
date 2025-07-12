import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.express as px
import numpy as np
import datetime
import sqlite3
import os # ファイルの存在チェックのためにosモジュールをインポート

# --- データベースの作成とデータ投入関数 ---
def create_and_populate_db(db_name='population_data.db'):
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # 地区ごとの緯度経度データ (データ生成時に使用)
        geo_data_map = {
            '中央町': {'lat': 31.5959, 'lon': 130.5586},
            '天文館': {'lat': 31.5901, 'lon': 130.5562},
            '鴨池': {'lat': 31.5650, 'lon': 130.5470},
            '谷山': {'lat': 31.5000, 'lon': 130.4900},
            '伊敷': {'lat': 31.6200, 'lon': 130.5400},
            '桜ヶ丘': {'lat': 31.5400, 'lon': 130.5200}
        }

        # population_tableの作成 (緯度経度カラムを含む)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS population_table (
                年月 TEXT NOT NULL,
                地区名 TEXT NOT NULL,
                人口 INTEGER NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                PRIMARY KEY (年月, 地区名) -- 年月と地区名の組み合わせをユニークにする
            )
        ''')

        # サンプル人口データの生成
        districts = list(geo_data_map.keys()) # 緯度経度データにある地区名を使用
        data = []
        current_date = datetime.date.today()

        for year in range(2015, current_date.year + 1):
            for month in range(1, 13):
                if year == current_date.year and month > current_date.month:
                    break
                date_str = f"{year}-{month:02d}"
                for district in districts:
                    initial_pop = np.random.randint(4000, 7000)
                    yearly_change = np.random.randint(-50, 150)
                    monthly_fluctuation = np.random.randint(-100, 100)
                    population = initial_pop + (year - 2015) * yearly_change + monthly_fluctuation
                    population = max(1000, int(population))
                    
                    # 緯度経度を取得
                    lat = geo_data_map[district]['lat']
                    lon = geo_data_map[district]['lon']
                    
                    data.append((date_str, district, population, lat, lon))

        # 人口データを挿入 (INSERT OR IGNORE で重複を避ける)
        cursor.execute("SELECT COUNT(*) FROM population_table")
        if cursor.fetchone()[0] == 0: # テーブルが空の場合のみ挿入
            cursor.executemany("INSERT OR IGNORE INTO population_table (年月, 地区名, 人口, lat, lon) VALUES (?, ?, ?, ?, ?)", data)
            st.success("人口データと緯度経度データがデータベースに投入されました。")
        else:
            st.info("人口データは既にデータベースに存在します。スキップしました。")

        conn.commit()
        
    except sqlite3.Error as e:
        st.error(f"データベースの作成またはデータ投入エラー: {e}")
    finally:
        if conn:
            conn.close()

# --- データロード関数 (SQLiteから) ---
@st.cache_data
def load_data_from_sqlite(db_name='population_data.db'):
    conn = None
    df = pd.DataFrame() # dfを空のDataFrameで初期化

    try:
        conn = sqlite3.connect(db_name) 
        
        # 統合されたテーブルからデータを取得
        query_population = "SELECT 年月, 地区名, 人口, lat, lon FROM population_table"
        df = pd.read_sql_query(query_population, conn)
        
        # 年月のdatetime型変換 ('YYYY-MM' 形式を想定)
        df['年月'] = pd.to_datetime(df['年月']).dt.to_period('M').dt.to_timestamp()
        
    except sqlite3.Error as e:
        st.error(f"データベースからのデータロードエラー: {e}")
        df = pd.DataFrame() 
    finally:
        if conn:
            conn.close()
    
    return df

# --- アプリケーションのメイン処理 ---
DB_NAME = 'population_data.db'

# データベースファイルが存在しない場合、または空の場合に作成・投入
if not os.path.exists(DB_NAME) or os.path.getsize(DB_NAME) == 0:
    st.info(f"'{DB_NAME}' が見つからないか空です。データベースを作成し、データを投入します。")
    create_and_populate_db(DB_NAME)
else:
    st.info(f"'{DB_NAME}' が存在します。既存のデータベースを使用します。")

# データをロード
df = load_data_from_sqlite(DB_NAME) # geo_dataは別途返されない

# --- 2. Streamlit UI ---
st.title('鹿児島市 人口増減ダッシュボード')
st.write('年月スライダーを動かして、各地区の人口変動を見てみよう！')

# 年月スライダー
if df.empty:
    st.error("データがロードされませんでした。データベースファイルとテーブルが存在するか確認してください。")
    st.stop() 

unique_months = sorted(df['年月'].unique())

if len(unique_months) == 0:
    st.error("利用可能な年月データがありません。データベースのデータを確認してください。")
    st.stop()
else:
    unique_dates = [pd.Timestamp(dt).to_pydatetime().date() for dt in unique_months]
    
    min_slider_date = unique_dates[0]
    max_slider_date = unique_dates[-1]
    default_slider_date = unique_dates[-1]

    selected_date_from_slider = st.slider(
        '年月を選択',
        min_value=min_slider_date,
        max_value=max_slider_date,
        value=default_slider_date,
    )

selected_date = pd.to_datetime(selected_date_from_slider)

st.subheader(f'選択中の年月: {selected_date.strftime("%Y年%m月")}')

st.markdown("---")

# --- 3. 地図の表示 ---
st.subheader('地図上の人口変動')

df_filtered = df[
    (df['年月'].dt.year == selected_date.year) & 
    (df['年月'].dt.month == selected_date.month)
].copy() # SettingWithCopyWarningを避けるために.copy()を使用

# df_mapを直接df_filteredから作成 (latとlonが既に含まれているため)
# 地区名、人口、lat、lonカラムをそのまま使用
df_map = df_filtered[['地区名', '人口', 'lat', 'lon']]


map_center = [31.5960, 130.5580]
m = folium.Map(location=map_center, zoom_start=12)

if not df_map.empty:
    min_pop = df_map['人口'].min()
    max_pop = df_map['人口'].max()

    for idx, row in df_map.iterrows():
        normalized_pop = (row['人口'] - min_pop) / (max_pop - min_pop) if (max_pop - min_pop) > 0 else 0.5
        color_val_r = int(255 * (1 - normalized_pop))
        color_val_g = int(255 * (1 - normalized_pop))
        color_val_b = 255
        color_hex = f'#{color_val_r:02x}{color_val_g:02x}{color_val_b:02x}'

        radius = np.log(max(row['人口'], 1000) / 1000) * 5 + 5
        radius = max(5, radius)

        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=radius,
            color=color_hex,
            fill=True,
            fill_color=color_hex,
            fill_opacity=0.7,
            tooltip=f"{row['地区名']}: 人口 {row['人口']}人"
        ).add_to(m)

folium_static(m)

st.markdown("---")

# --- 4. 人口推移グラフ ---

st.subheader('選択地区の人口推移')

df_total_pop_over_time = df.groupby('年月')['人口'].sum().reset_index()

fig_line = px.line(df_total_pop_over_time, 
                   x='年月', 
                   y='人口', 
                   title='鹿児島市全体の人口推移')
fig_line.update_layout(xaxis_title="年月", yaxis_title="人口", hovermode="x unified")
st.plotly_chart(fig_line, use_container_width=True)

if not df.empty:
    selected_district = st.selectbox('詳細を見たい地区を選択', df['地区名'].unique())

    if selected_district:
        df_district_pop = df[df['地区名'] == selected_district].sort_values('年月')
        
        fig_bar = px.bar(df_district_pop, 
                        x='年月', 
                        y='人口', 
                        title=f'{selected_district}の人口推移',
                        labels={'年月': '年月', '人口': '人口'})
        fig_bar.update_layout(xaxis_title="年月", yaxis_title="人口")
        st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("人口推移グラフを表示するためのデータがありません。")


