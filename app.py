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
def create_and_populate_db(db_name='school_data.db'):
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # 学校ごとの緯度経度データ (データ生成時に使用)
        geo_data_map = {
            '中央小学校': {'lat': 31.5959, 'lon': 130.5586},
            '天文館小学校': {'lat': 31.5901, 'lon': 130.5562},
            '鴨池小学校': {'lat': 31.5650, 'lon': 130.5470},
            '谷山小学校': {'lat': 31.5000, 'lon': 130.4900},
            '伊敷小学校': {'lat': 31.6200, 'lon': 130.5400},
            '桜ヶ丘小学校': {'lat': 31.5400, 'lon': 130.5200}
        }

        # school_data_tableの作成 (緯度経度、児童生徒数、特別支援学級人数カラムを含む)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS school_data_table (
                Date TEXT NOT NULL,
                School_Name TEXT NOT NULL,
                Student_Count INTEGER NOT NULL,
                Special_Support_Class_Size INTEGER NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                PRIMARY KEY (Date, School_Name) -- 年月と学校名の組み合わせをユニークにする
            )
        ''')

        # サンプル学校データ (児童生徒数と特別支援学級人数) の生成
        schools = list(geo_data_map.keys()) # 緯度経度データにある学校名を使用
        data = []
        current_date = datetime.date.today()

        for year in range(2015, current_date.year + 1):
            for month in range(1, 13):
                if year == current_date.year and month > current_date.month:
                    break
                date_str = f"{year}-{month:02d}"
                for school in schools:
                    initial_students = np.random.randint(300, 800)
                    yearly_student_change = np.random.randint(-20, 30)
                    monthly_student_fluctuation = np.random.randint(-50, 50)
                    
                    student_count = initial_students + (year - 2015) * yearly_student_change + monthly_student_fluctuation
                    student_count = max(100, int(student_count)) # 最低児童生徒数

                    special_support_class_size = np.random.randint(5, 30) # 特別支援学級人数

                    # 緯度経度を取得
                    lat = geo_data_map[school]['lat']
                    lon = geo_data_map[school]['lon']
                    
                    data.append((date_str, school, student_count, special_support_class_size, lat, lon))

        # データを挿入 (INSERT OR IGNORE で重複を避ける)
        cursor.execute("SELECT COUNT(*) FROM school_data_table")
        if cursor.fetchone()[0] == 0: # テーブルが空の場合のみ挿入
            cursor.executemany("INSERT OR IGNORE INTO school_data_table (Date, School_Name, Student_Count, Special_Support_Class_Size, lat, lon) VALUES (?, ?, ?, ?, ?, ?)", data)
            st.success("児童生徒数、特別支援学級人数、緯度経度データがデータベースに投入されました。")
        else:
            st.info("学校データは既にデータベースに存在します。スキップしました。")

        conn.commit()
        
    except sqlite3.Error as e:
        st.error(f"データベースの作成またはデータ投入エラー: {e}")
    finally:
        if conn:
            conn.close()

# --- データロード関数 (SQLiteから) ---
@st.cache_data
def load_data_from_sqlite(db_name='school_data.db'):
    conn = None
    df = pd.DataFrame() # dfを空のDataFrameで初期化

    try:
        conn = sqlite3.connect(db_name) 
        
        # 統合されたテーブルからデータを取得
        query_school_data = "SELECT Date, School_Name, Student_Count, Special_Support_Class_Size, lat, lon FROM school_data_table"
        df = pd.read_sql_query(query_school_data, conn)
        
        # 年月のdatetime型変換 ('YYYY-MM' 形式を想定)
        df['Date'] = pd.to_datetime(df['Date']).dt.to_period('M').dt.to_timestamp()
        
    except sqlite3.Error as e:
        st.error(f"データベースからのデータロードエラー: {e}")
        df = pd.DataFrame() 
    finally:
        if conn:
            conn.close()
    
    return df

# --- アプリケーションのメイン処理 ---
DB_NAME = 'school_data.db'

# データベースファイルが存在しない場合、または空の場合に作成・投入
if not os.path.exists(DB_NAME) or os.path.getsize(DB_NAME) == 0:
    st.info(f"'{DB_NAME}' が見つからないか空です。データベースを作成し、データを投入します。")
    create_and_populate_db(DB_NAME)
# else:
#    st.info(f"'{DB_NAME}' が存在します。既存のデータベースを使用します。")

# データをロード
df = load_data_from_sqlite(DB_NAME) 

# --- 2. Streamlit UI ---
st.title('鹿児島市 児童生徒数ダッシュボード')
st.write('年月スライダーを動かして、各学校の児童生徒数と特別支援学級人数の変動を見てみよう！')

# 年月スライダー
if df.empty:
    st.error("データがロードされませんでした。データベースファイルとテーブルが存在するか確認してください。")
    st.stop() 

unique_months = sorted(df['Date'].unique())

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
st.subheader('地図上の児童生徒数変動')

df_filtered = df[
    (df['Date'].dt.year == selected_date.year) & 
    (df['Date'].dt.month == selected_date.month)
].copy() # SettingWithCopyWarningを避けるために.copy()を使用

# df_mapを直接df_filteredから作成 (latとlonが既に含まれているため)
# 学校名、児童生徒数、特別支援学級人数、lat、lonカラムをそのまま使用
df_map = df_filtered[['School_Name', 'Student_Count', 'Special_Support_Class_Size', 'lat', 'lon']]


map_center = [31.5960, 130.5580]
m = folium.Map(location=map_center, zoom_start=12)

if not df_map.empty:
    min_students = df_map['Student_Count'].min()
    max_students = df_map['Student_Count'].max()

    for idx, row in df_map.iterrows():
        normalized_students = (row['Student_Count'] - min_students) / (max_students - min_students) if (max_students - min_students) > 0 else 0.5
        
        # 色を児童生徒数に基づいて調整 (例: 児童生徒数が多いほど青みが濃くなる)
        color_val_r = int(255 * (1 - normalized_students))
        color_val_g = int(255 * (1 - normalized_students))
        color_val_b = 255
        color_hex = f'#{color_val_r:02x}{color_val_g:02x}{color_val_b:02x}'

        # 円の半径を児童生徒数に基づいて調整
        radius = np.log(max(row['Student_Count'], 100) / 100) * 5 + 5
        radius = max(5, radius)

        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=radius,
            color=color_hex,
            fill=True,
            fill_color=color_hex,
            fill_opacity=0.7,
            tooltip=f"{row['School_Name']}: 児童生徒数 {row['Student_Count']}人, 特別支援学級人数 {row['Special_Support_Class_Size']}人"
        ).add_to(m)

folium_static(m)

st.markdown("---")

# --- 4. 児童生徒数推移グラフ ---

st.subheader('選択学校の児童生徒数推移')

df_total_students_over_time = df.groupby('Date')['Student_Count'].sum().reset_index()

fig_line_students = px.line(df_total_students_over_time, 
                   x='Date', 
                   y='Student_Count', 
                   title='鹿児島市全体の児童生徒数推移')
fig_line_students.update_layout(xaxis_title="年月", yaxis_title="児童生徒数", hovermode="x unified")
st.plotly_chart(fig_line_students, use_container_width=True)

if not df.empty:
    selected_school = st.selectbox('詳細を見たい学校を選択', df['School_Name'].unique())

    if selected_school:
        df_school_data = df[df['School_Name'] == selected_school].sort_values('Date')
        
        fig_bar_students = px.bar(df_school_data, 
                        x='Date', 
                        y='Student_Count', 
                        title=f'{selected_school}の児童生徒数推移',
                        labels={'Date': '年月', 'Student_Count': '児童生徒数'})
        fig_bar_students.update_layout(xaxis_title="年月", yaxis_title="児童生徒数")
        st.plotly_chart(fig_bar_students, use_container_width=True)

        fig_bar_special = px.bar(df_school_data, 
                        x='Date', 
                        y='Special_Support_Class_Size', 
                        title=f'{selected_school}の特別支援学級人数推移',
                        labels={'Date': '年月', 'Special_Support_Class_Size': '特別支援学級人数'})
        fig_bar_special.update_layout(xaxis_title="年月", yaxis_title="特別支援学級人数")
        st.plotly_chart(fig_bar_special, use_container_width=True)

else:
    st.info("児童生徒数推移グラフを表示するためのデータがありません。")
