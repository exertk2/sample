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

        # population_tableの作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS population_table (
                年月 TEXT NOT NULL,
                地区名 TEXT NOT NULL,
                人口 INTEGER NOT NULL
            )
        ''')

        # district_geodataテーブルの作成 (緯度経度用)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS district_geodata (
                地区名 TEXT NOT NULL UNIQUE,
                lat REAL NOT NULL,
                lon REAL NOT NULL
            )
        ''')

        # サンプル人口データの生成 (元のapp.pyのロジックに類似)
        districts = ['中央町', '天文館', '鴨池', '谷山', '伊敷', '桜ヶ丘']
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
                    data.append((date_str, district, population))

        # 人口データを挿入
        # 既にデータがある場合はスキップするために、INSERT OR IGNORE を使用
        # ただし、このサンプルでは毎回全期間のデータを生成するため、
        # 重複挿入を避けるには、まず既存データをクリアするか、より複雑なロジックが必要です。
        # 簡単のため、ここでは毎回挿入を試みますが、実運用では注意が必要です。
        # 既存データがあるか確認し、なければ挿入するロジックを追加
        cursor.execute("SELECT COUNT(*) FROM population_table")
        if cursor.fetchone()[0] == 0: # テーブルが空の場合のみ挿入
            cursor.executemany("INSERT INTO population_table (年月, 地区名, 人口) VALUES (?, ?, ?)", data)
            st.success("人口データがデータベースに投入されました。")
        else:
            st.info("人口データは既にデータベースに存在します。スキップしました。")


        # 地理データを挿入
        geo_data_for_db = [
            ('中央町', 31.5959, 130.5586),
            ('天文館', 31.5901, 130.5562),
            ('鴨池', 31.5650, 130.5470),
            ('谷山', 31.5000, 130.4900),
            ('伊敷', 31.6200, 130.5400),
            ('桜ヶ丘', 31.5400, 130.5200)
        ]

        # 地理データは重複を避けるため INSERT OR REPLACE を使用
        for district, lat, lon in geo_data_for_db:
            cursor.execute("INSERT OR REPLACE INTO district_geodata (地区名, lat, lon) VALUES (?, ?, ?)", (district, lat, lon))
        st.success("地区の緯度経度データがデータベースに投入または更新されました。")

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
    geo_data = {} # geo_dataを空の辞書で初期化

    try:
        conn = sqlite3.connect(db_name) 
        
        # 人口データを取得
        query_population = "SELECT 年月, 地区名, 人口 FROM population_table"
        df = pd.read_sql_query(query_population, conn)
        
        # 年月のdatetime型変換 ('YYYY-MM' 形式を想定)
        df['年月'] = pd.to_datetime(df['年月']).dt.to_period('M').dt.to_timestamp()
        
        # 緯度経度データを取得
        query_geodata = "SELECT 地区名, lat, lon FROM district_geodata"
        df_geodata = pd.read_sql_query(query_geodata, conn)

        # 緯度経度データを辞書形式に変換
        geo_data = {row['地区名']: {'lat': row['lat'], 'lon': row['lon']} 
                    for index, row in df_geodata.iterrows()}
        
    except sqlite3.Error as e:
        st.error(f"データベースからのデータロードエラー: {e}")
        df = pd.DataFrame() 
        geo_data = {}
    finally:
        if conn:
            conn.close()
    
    return df, geo_data

# --- アプリケーションのメイン処理 ---
DB_NAME = 'population_data.db'

# データベースファイルが存在しない場合、または空の場合に作成・投入
if not os.path.exists(DB_NAME) or os.path.getsize(DB_NAME) == 0:
    st.info(f"'{DB_NAME}' が見つからないか空です。データベースを作成し、データを投入します。")
    create_and_populate_db(DB_NAME)
else:
    st.info(f"'{DB_NAME}' が存在します。既存のデータベースを使用します。")

# データをロード
df, geo_data = load_data_from_sqlite(DB_NAME)

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
]

if not geo_data:
    st.warning("緯度経度データがロードされませんでした。地図を表示できません。")
    df_map = pd.DataFrame() 
else:
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


