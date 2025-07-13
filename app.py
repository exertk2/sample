import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.express as px
import numpy as np
import datetime
import sqlite3
import os
import time

st.set_page_config(page_title="鹿児島 児童生徒数", layout="wide") # レイアウトをwideに設定

# --- データベースの作成とデータ投入関数 ---
def create_and_populate_db(db_name='school_data.db'):
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # 学校ごとの緯度経度データ (データ生成時に使用)
        geo_data_map = {
            '中央小学校': {'lat': 31.5959, 'lon': 130.5586, 'city': '鹿児島市', 'school_type': '公立小学校'},
            '天文館小学校': {'lat': 31.5901, 'lon': 130.5562, 'city': '鹿児島市', 'school_type': '公立小学校'},
            '鴨池小学校': {'lat': 31.5650, 'lon': 130.5470, 'city': '鹿児島市', 'school_type': '公立小学校'},
            '谷山小学校': {'lat': 31.5000, 'lon': 130.4900, 'city': '鹿児島市', 'school_type': '公立小学校'},
            '伊敷小学校': {'lat': 31.6200, 'lon': 130.5400, 'city': '鹿児島市', 'school_type': '公立小学校'},
            '桜ヶ丘小学校': {'lat': 31.5400, 'lon': 130.5200, 'city': '鹿児島市', 'school_type': '公立小学校'}
        }

        # school_data_tableの作成 (緯度経度、児童生徒数、特別支援学級人数、City、School_Typeカラムを含む)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS school_data_table (
                Date TEXT NOT NULL,
                School_Name TEXT NOT NULL,
                Student_Count INTEGER NOT NULL,
                Special_Support_Class_Size INTEGER NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                City TEXT NOT NULL,
                School_Type TEXT NOT NULL,
                PRIMARY KEY (Date, School_Name)
            )
        ''')

        # サンプル学校データ (児童生徒数と特別支援学級人数) の生成
        schools = list(geo_data_map.keys())
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
                    student_count = max(100, int(student_count))

                    special_support_class_size = np.random.randint(5, 30)

                    # 緯度経度、City、School_Typeを取得
                    lat = geo_data_map[school]['lat']
                    lon = geo_data_map[school]['lon']
                    city = geo_data_map[school]['city']
                    school_type = geo_data_map[school]['school_type']
                    
                    data.append((date_str, school, student_count, special_support_class_size, lat, lon, city, school_type))

        # データを挿入 (INSERT OR IGNORE で重複を避ける)
        cursor.execute("SELECT COUNT(*) FROM school_data_table")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT OR IGNORE INTO school_data_table (Date, School_Name, Student_Count, Special_Support_Class_Size, lat, lon, City, School_Type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", data)
            st.success("児童生徒数、特別支援学級人数、緯度経度、市町村、学校種別データがデータベースに投入されました。")
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
    df = pd.DataFrame()

    try:
        conn = sqlite3.connect(db_name) 
        
        # 統合されたテーブルからデータを取得 (CityとSchool_Typeを追加)
        query_school_data = "SELECT Date, School_Name, Student_Count, Special_Support_Class_Size, lat, lon, City, School_Type FROM school_data_table"
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

# 色を計算するヘルパー関数
def get_color_for_students(student_count, min_s, max_s):
    if (max_s - min_s) <= 0:
        normalized_students = 0.5 # データがない、または単一値の場合は中間色
    else:
        normalized_students = (student_count - min_s) / (max_s - min_s)
    
    # 人数が多いほど青くなる（RとGが減少）
    color_val_r = int(255 * (1 - normalized_students))
    color_val_g = int(255 * (1 - normalized_students))
    color_val_b = 255
    return f'#{color_val_r:02x}{color_val_g:02x}{color_val_b:02x}'

# --- アプリケーションのメイン処理 ---
DB_NAME = 'school_data.db'

# データベースファイルが存在しない場合、または空の場合に作成・投入
if not os.path.exists(DB_NAME) or os.path.getsize(DB_NAME) == 0:
    st.info(f"'{DB_NAME}' が見つからないか空です。データベースを作成し、データを投入します。")
    create_and_populate_db(DB_NAME)

# データをロード
df = load_data_from_sqlite(DB_NAME) 

# --- 2. Streamlit UI ---
# --- サイドバーの要素 ---
st.sidebar.subheader('絞り込み条件')

# 年月セレクトボックス
if df.empty:
    st.sidebar.error("データがロードされませんでした。データベースファイルとテーブルが存在するか確認してください。")
    st.stop() 

# 年月を降順にソート
unique_months = sorted(df['Date'].unique(), reverse=True)

if len(unique_months) == 0:
    st.sidebar.error("利用可能な年月データがありません。データベースのデータを確認してください。")
    st.stop()
else:
    # 表示用の年月文字列リストを作成 (例: "2023年01月")
    month_options = [pd.Timestamp(dt).strftime("%Y年%m月") for dt in unique_months]
    
    # セッションステートの初期化
    if 'selected_month_index' not in st.session_state:
        st.session_state.selected_month_index = 0 # 降順なので最初の要素（最新）をデフォルトに
    if 'playing' not in st.session_state:
        st.session_state.playing = False

    # 月選択セレクトボックス
    selected_month_str = st.sidebar.selectbox(
        '年月を選択',
        options=month_options,
        index=st.session_state.selected_month_index,
        key='month_selector' # 再生機能のためにkeyを設定
    )
    
    # 選択された年月文字列からインデックスを取得してセッションステートを更新
    # selectboxで手動選択された場合、indexを更新する
    current_selected_index = month_options.index(selected_month_str)
    if st.session_state.selected_month_index != current_selected_index:
        st.session_state.playing = False # 手動選択で再生を停止
        st.session_state.selected_month_index = current_selected_index

# selected_month_str から datetime オブジェクトを再構築
selected_date = pd.to_datetime(selected_month_str.replace('年', '-').replace('月', ''))

# 学校種別の選択
unique_school_types = df['School_Type'].unique()
public_elementary_index = list(unique_school_types).index('公立小学校') if '公立小学校' in unique_school_types else 0
selected_school_type = st.sidebar.selectbox('学校種別を選択', unique_school_types, index=public_elementary_index)

# 市町村の選択
unique_cities = df['City'].unique().tolist() # tolist() でリストに変換
unique_cities.insert(0, 'すべて') # 先頭に「すべて」を追加
# 初期値は「すべて」
selected_city = st.sidebar.selectbox('市町村を選択', unique_cities, index=0)

# 児童生徒数範囲のselectbox
student_count_options = {
    'すべて': (None, None), # Noneはフィルターなしを示す
    '100人未満': (0, 99),
    '100人～300人': (100, 300),
    '301人～500人': (301, 500),
    '501人以上': (501, float('inf')) # 無限大
}
selected_student_count_range_label = st.sidebar.selectbox(
    '児童生徒数範囲',
    options=list(student_count_options.keys()),
    index=0 # デフォルトは「すべて」
)
selected_student_count_min, selected_student_count_max = student_count_options[selected_student_count_range_label]

# 特別支援学級人数範囲のselectbox
special_class_options = {
    'すべて': (None, None),
    '5人未満': (0, 4),
    '5人～10人': (5, 10),
    '11人～20人': (11, 20),
    '21人以上': (21, float('inf'))
}
selected_special_class_range_label = st.sidebar.selectbox(
    '特別支援学級人数範囲',
    options=list(special_class_options.keys()),
    index=0 # デフォルトは「すべて」
)
selected_special_class_min, selected_special_class_max = special_class_options[selected_special_class_range_label]


# --- サイドバーの要素ここまで ---


# --- フィルター適用後のデータフレーム作成 ---
df_filtered = df[
    (df['Date'].dt.year == selected_date.year) & 
    (df['Date'].dt.month == selected_date.month) &
    (df['School_Type'] == selected_school_type)
].copy()

# 児童生徒数フィルターの適用
if selected_student_count_min is not None:
    df_filtered = df_filtered[
        (df_filtered['Student_Count'] >= selected_student_count_min) &
        (df_filtered['Student_Count'] <= selected_student_count_max)
    ]

# 特別支援学級人数フィルターの適用
if selected_special_class_min is not None:
    df_filtered = df_filtered[
        (df_filtered['Special_Support_Class_Size'] >= selected_special_class_min) &
        (df_filtered['Special_Support_Class_Size'] <= selected_special_class_max)
    ]

# 「すべて」が選択されていない場合のみ市町村でフィルタリング
if selected_city != 'すべて':
    df_filtered = df_filtered[df_filtered['City'] == selected_city]

# --- 3. 地図と凡例の表示を横に並べる ---
col1, col2 = st.columns([3, 1]) # 地図を3、凡例を1の比率で配置

with col1:
    df_map = df_filtered[['School_Name', 'Student_Count', 'Special_Support_Class_Size', 'lat', 'lon']]

    map_center = [31.5960, 130.5580]
    m = folium.Map(location=map_center, zoom_start=9) # zoom_startは固定

    if not df_map.empty:
        min_students = df_map['Student_Count'].min()
        max_students = df_map['Student_Count'].max()

        for idx, row in df_map.iterrows():
            color_hex = get_color_for_students(row['Student_Count'], min_students, max_students)
            
            radius = np.log(max(row['Student_Count'], 100) / 100) * 5 + 5
            radius = max(5, radius)

            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=radius,
                color='red',
                weight=0.5,     # 枠線の太さを設定 (例: 2ピクセル)
                fill=True,
                fill_color=color_hex,
                fill_opacity=0.7,
                tooltip=f"{row['School_Name']}: 児童生徒数 {row['Student_Count']}人, 特別支援学級人数 {row['Special_Support_Class_Size']}人"
            ).add_to(m)

    folium_static(m, width=700, height=500) # サイズを調整

with col2:
    st.markdown("### 凡例")
    if not df_map.empty:
        st.markdown("赤円内の青色は児童生徒数")
        st.markdown("""
            <style>
                .legend-item {
                    display: flex;
                    align-items: center;
                    margin-bottom: 5px;
                }
                .color-box {
                    width: 20px;
                    height: 20px;
                    margin-right: 10px;
                    border: 1px solid #ccc;
                }
            </style>
        """, unsafe_allow_html=True)

        # 凡例の例をいくつか表示
        min_students_for_legend = df_map['Student_Count'].min()
        max_students_for_legend = df_map['Student_Count'].max()

        if (max_students_for_legend - min_students_for_legend) > 0:
            # 5段階で凡例を表示
            num_steps = 5
            legend_steps = np.linspace(min_students_for_legend, max_students_for_legend, num_steps)
            
            for i, count in enumerate(legend_steps):
                current_color = get_color_for_students(count, min_students_for_legend, max_students_for_legend)
                label = ""
                if i == 0:
                    label = f"{int(count)}人 (少ない)"
                elif i == num_steps - 1:
                    label = f"{int(count)}人 (多い)"
                else:
                    label = f"約 {int(count)}人"
                
                st.markdown(f"""
                    <div class="legend-item">
                        <div class="color-box" style="background-color: {current_color};"></div>
                        <span>{label}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            # 人数が一律の場合
            st.info(f"現在の選択では全学校の児童生徒数が一律 {int(min_students_for_legend)} 人のため、色の濃淡による凡例は表示されません。")
    else:
        st.info("地図凡例を表示するためのデータがありません。")


# --- 4. 児童生徒数推移グラフ ---

# 全体の児童生徒数推移グラフもフィルター条件を適用 (dfに対してフィルターを適用)
df_total_students_over_time = df[
    (df['School_Type'] == selected_school_type)
].copy()

if selected_city != 'すべて':
    df_total_students_over_time = df_total_students_over_time[df_total_students_over_time['City'] == selected_city]

# 児童生徒数フィルターの適用
if selected_student_count_min is not None:
    df_total_students_over_time = df_total_students_over_time[
        (df_total_students_over_time['Student_Count'] >= selected_student_count_min) &
        (df_total_students_over_time['Student_Count'] <= selected_student_count_max)
    ]

# 特別支援学級人数フィルターの適用
if selected_special_class_min is not None:
    df_total_students_over_time = df_total_students_over_time[
        (df_total_students_over_time['Special_Support_Class_Size'] >= selected_special_class_min) &
        (df_total_students_over_time['Special_Support_Class_Size'] <= selected_special_class_max)
    ]

df_total_students_over_time = df_total_students_over_time.groupby('Date')['Student_Count'].sum().reset_index()

# グラフタイトルを動的に変更
graph_title_city_part = selected_city if selected_city != 'すべて' else '全市町村'
fig_line_students = px.line(df_total_students_over_time, 
                   x='Date', 
                   y='Student_Count', 
                   title=f'{graph_title_city_part}の{selected_school_type}全体の児童生徒数推移')
fig_line_students.update_layout(xaxis_title="年月", yaxis_title="児童生徒数", hovermode="x unified")
st.plotly_chart(fig_line_students, use_container_width=True)

if not df_filtered.empty: # df_filteredから選択肢を生成
    selected_school = st.selectbox('詳細を見たい学校を選択', df_filtered['School_Name'].unique())

    if selected_school:
        df_school_data = df[
            (df['School_Name'] == selected_school) &
            # 個別学校のグラフでは、選択された市町村と学校種別も考慮する
            ((df['City'] == selected_city) if selected_city != 'すべて' else True) & # 「すべて」の場合は市町村フィルタを適用しない
            (df['School_Type'] == selected_school_type)
        ].sort_values('Date')
        
        # 児童生徒数フィルターの適用
        if selected_student_count_min is not None:
            df_school_data = df_school_data[
                (df_school_data['Student_Count'] >= selected_student_count_min) &
                (df_school_data['Student_Count'] <= selected_student_count_max)
            ]

        # 特別支援学級人数フィルターの適用
        if selected_special_class_min is not None:
            df_school_data = df_school_data[
                (df_school_data['Special_Support_Class_Size'] >= selected_special_class_min) &
                (df_school_data['Special_Support_Class_Size'] <= selected_special_class_max)
            ]

        # もしdf_school_dataが空の場合、メッセージを表示
        if df_school_data.empty:
            st.info(f"{selected_school}のデータは、選択された市町村または学校種別、または児童生徒数・特別支援学級人数のフィルターに合致しません。")
        else:
            # 児童生徒数推移と特別支援学級人数推移のグラフを横に並べる
            graph_col1, graph_col2 = st.columns(2)

            with graph_col1:
                fig_bar_students = px.bar(df_school_data, 
                                x='Date', 
                                y='Student_Count', 
                                title=f'{selected_school}の児童生徒数推移',
                                labels={'Date': '年月', 'Student_Count': '児童生徒数'})
                fig_bar_students.update_layout(xaxis_title="年月", yaxis_title="児童生徒数")
                st.plotly_chart(fig_bar_students, use_container_width=True)

            with graph_col2:
                fig_bar_special = px.bar(df_school_data, 
                                x='Date', 
                                y='Special_Support_Class_Size', 
                                title=f'{selected_school}の特別支援学級人数推移',
                                labels={'Date': '年月', 'Special_Support_Class_Size': '特別支援学級人数'},
                                color_discrete_sequence=['#28a745']) # 緑色のHEXコード
                fig_bar_special.update_layout(xaxis_title="年月", yaxis_title="特別支援学級人数")
                st.plotly_chart(fig_bar_special, use_container_width=True)

else:
    st.info("選択された条件に合致する児童生徒数推移グラフを表示するためのデータがありません。")
