import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import numpy as np
import datetime
import sqlite3
import os
import time

st.set_page_config(page_title="鹿児島 児童生徒数、障害事業所", layout="wide")


# --- データベースの作成とデータ投入関数 ---
def create_and_populate_db(db_name='school_data.db'):
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # school_data_tableの作成 (idをPRIMARY KEYとして追加)
        # 既存のテーブルがある場合は削除し、新しいスキーマで再作成
        cursor.execute('DROP TABLE IF EXISTS school_data_table')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS school_data_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Date TEXT NOT NULL,
                School_Name TEXT NOT NULL,
                Student_Count INTEGER NOT NULL,
                Special_Support_Class_Size INTEGER NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                City TEXT NOT NULL,
                School_Type TEXT NOT NULL
            )
        ''')

        # 学校ごとの緯度経度データ (データ生成時に使用)
        geo_data_map = {
            '中央小学校': {'lat': 31.5959, 'lon': 130.5586, 'city': '鹿児島市', 'school_type': '公立小学校'},
            '天文館小学校': {'lat': 31.5901, 'lon': 130.5562, 'city': '鹿児島市', 'school_type': '公立小学校'},
            '鴨池小学校': {'lat': 31.5650, 'lon': 130.5470, 'city': '鹿児島市', 'school_type': '公立小学校'},
            '谷山小学校': {'lat': 31.5000, 'lon': 130.4900, 'city': '鹿児島市', 'school_type': '公立小学校'},
            '伊敷小学校': {'lat': 31.6200, 'lon': 130.5400, 'city': '鹿児島市', 'school_type': '公立小学校'},
            '桜ヶ丘小学校': {'lat': 31.5400, 'lon': 130.5200, 'city': '鹿児島市', 'school_type': '公立小学校'}
        }

        # サンプル学校データ (児童生徒数と特別支援学級人数) の生成
        schools = list(geo_data_map.keys())
        data = []
        current_date = datetime.date.today()

        for year in range(2015, current_date.year + 1):
            for month in range(1, 13):
                if year == current_date.year and month > current_date.month:
                    break
                date_str = f"{year}-{month:02d}" # YYYY-MM format
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

                    # idはAUTOINCREMENTなので挿入データには含めない
                    data.append((date_str, school, student_count, special_support_class_size, lat, lon, city, school_type))

        # データを挿入
        # idカラムがAUTOINCREMENTなので、INSERT文からidを除外
        cursor.executemany("INSERT INTO school_data_table (Date, School_Name, Student_Count, Special_Support_Class_Size, lat, lon, City, School_Type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", data)
        st.success("児童生徒数、特別支援学級人数、緯度経度、市町村、学校種別データがデータベースに投入されました。")


        # sfkopendataの作成
        cursor.execute('DROP TABLE IF EXISTS sfkopendata') # 既存のテーブルがある場合は削除
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "sfkopendata" (
                "元スプレッドシート名"	TEXT,
                "都道府県コード又は市区町村コード"	TEXT,
                "NO（※システム内の固有の番号、連番）"	TEXT,
                "指定機関名"	TEXT,
                "法人の名称"	TEXT,
                "法人の名称_かな"	TEXT,
                "法人番号"	TEXT,
                "法人住所（市区町村）"	TEXT,
                "法人住所（番地以降）"	TEXT,
                "法人電話番号"	TEXT,
                "法人FAX番号"	TEXT,
                "法人URL"	TEXT,
                "サービス種別"	TEXT,
                "事業所の名称"		TEXT,
                "事業所の名称_かな"	TEXT,
                "事業所番号"	TEXT PRIMARY KEY,
                "事業所住所（市区町村）"	TEXT,
                "事業所住所（番地以降）"	TEXT,
                "事業所電話番号"	TEXT,
                "事業所FAX番号"	TEXT,
                "事業所URL"	TEXT,
                "事業所緯度"	REAL,
                "事業所経度"	REAL,
                "利用可能な時間帯（平日）"	TEXT,
                "利用可能な時間帯（土曜）"	TEXT,
                "利用可能な時間帯（日曜）"	TEXT,
                "利用可能な時間帯（祝日）"	TEXT,
                "定休日"	TEXT,
                "利用可能曜日特記事項（留意事項）"	TEXT,
                "定員"	TEXT
            )
        ''')

        # 都道府県コードと都道府県名のマッピング (例として一部のみ)
        prefecture_map = {
            '01': '北海道', '02': '青森県', '03': '岩手県', '04': '宮城県', '05': '秋田県',
            '06': '山形県', '07': '福島県', '08': '茨城県', '09': '栃木県', '10': '群馬県',
            '11': '埼玉県', '12': '千葉県', '13': '東京都', '14': '神奈川県', '15': '新潟県',
            '16': '富山県', '17': '石川県', '18': '福井県', '19': '山梨県', '20': '長野県',
            '21': '岐阜県', '22': '静岡県', '23': '愛知県', '24': '三重県', '25': '滋賀県',
            '26': '京都府', '27': '大阪府', '28': '兵庫県', '29': '奈良県', '30': '和歌山県',
            '31': '鳥取県', '32': '島根県', '33': '岡山県', '34': '広島県', '35': '山口県',
            '36': '徳島県', '37': '香川県', '38': '愛媛県', '39': '高知県', '40': '福岡県',
            '41': '佐賀県', '42': '長崎県', '43': '熊本県', '44': '大分県', '45': '宮崎県',
            '46': '鹿児島県', '47': '沖縄県'
        }
        # サービス種別のダミーマッピング
        service_type_map = {
            '医療型児童発達支援': '医療型児童発達支援',
            '児童発達支援': '児童発達支援',
            '放課後等デイサービス': '放課後等デイサービス',
            '生活介護': '生活介護',
            '短期入所': '短期入所',
            '相談支援事業所': '相談支援事業所',
            '保育所等訪問支援': '保育所等訪問支援'
        }
        service_type_names = list(service_type_map.keys())


        # ダミーのsfkopendataを生成
        sfkopendata = []
        for i in range(1, 100):
            pref_code = np.random.choice(list(prefecture_map.keys()))
            service_type_name = np.random.choice(service_type_names)
            # 事業所番号は都道府県コード2桁 + 8桁のランダムな数字
            office_number = f"{pref_code}{np.random.randint(10000000, 99999999):08d}"

            # 元スプレッドシート名をシンプルな形式で生成 (元に戻す)
            original_spreadsheet_name = f"元スプレッドシート名_{i}"

            sfkopendata.append((
                original_spreadsheet_name, # "元スプレッドシート名"
                pref_code, # "都道府県コード又は市区町村コード"
                f"NO_{i}", # "NO（※システム内の固有の番号、連番）"
                f"指定機関名_{i}", # "指定機関名"
                f"法人名称_{i}", # "法人の名称"
                f"ほうじんめいしょう_{i}", # "法人の名称_かな"
                f"法人番号_{i}", # "法人番号"
                "鹿児島市", # "法人住所（市区町村）"
                f"中央町{i}-1", # "法人住所（番地以降）"
                f"099-123-456{i}", # "法人電話番号"
                f"099-123-457{i}", # "法人FAX番号"
                f"http://example.com/corp{i}", # "法人URL"
                service_type_name, # "サービス種別"
                f"事業所名称_{i}", # "事業所の名称"
                f"じぎょうしょめいしょう_{i}", # "事業所の名称_かな"
                office_number, # "事業所番号"
                "鹿児島市", # "事業所住所（市区町村）"
                f"天文館{i}-2", # "事業所住所（番地以降）"
                f"099-789-012{i}", # "事業所電話番号"
                f"099-789-013{i}", # "事業所FAX番号"
                f"http://example.com/office{i}", # "事業所URL"
                31.59 + np.random.uniform(-0.05, 0.05), # "事業所緯度"
                130.55 + np.random.uniform(-0.05, 0.05), # "事業所経度"
                "9:00-17:00", # "利用可能な時間帯（平日）"
                "9:00-12:00", # "利用可能な時間帯（土曜）"
                "定休日", # "利用可能な時間帯（日曜）"
                "不定休", # "利用可能な時間帯（祝日）"
                "日曜", # "定休日"
                "特記事項", # "利用可能曜日特記事項（留意事項）"
                str(np.random.randint(10, 50)) # "定員" (TEXT型なので文字列に変換)
            ))

        # データを挿入
        cursor.executemany("""
            INSERT INTO sfkopendata (
                "元スプレッドシート名", "都道府県コード又は市区町村コード", "NO（※システム内の固有の番号、連番）",
                "指定機関名", "法人の名称", "法人の名称_かな", "法人番号",
                "法人住所（市区町村）", "法人住所（番地以降）", "法人電話番号", "法人FAX番号", "法人URL",
                "サービス種別", "事業所の名称", "事業所の名称_かな", "事業所番号",
                "事業所住所（市区町村）", "事業所住所（番地以降）", "事業所電話番号", "事業所FAX番号", "事業所URL",
                "事業所緯度", "事業所経度",
                "利用可能な時間帯（平日）", "利用可能な時間帯（土曜）", "利用可能な時間帯（日曜）", "利用可能な時間帯（祝日）",
                "定休日", "利用可能曜日特記事項（留意事項）", "定員"
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sfkopendata)
        st.success("sfkopendataデータがデータベースに投入されました。")

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
    df_school = pd.DataFrame()
    df_sfkopendata = pd.DataFrame()

    try:
        conn = sqlite3.connect(db_name)

        # school_data_tableからidも取得
        query_school_data = "SELECT id, Date, School_Name, Student_Count, Special_Support_Class_Size, lat, lon, City, School_Type FROM school_data_table"
        df_school = pd.read_sql_query(query_school_data, conn)
        df_school['Date'] = pd.to_datetime(df_school['Date']).dt.to_period('M').dt.to_timestamp()

        # sfkopendataからデータを取得
        query_sfkopendata = "SELECT * FROM sfkopendata"
        df_sfkopendata = pd.read_sql_query(query_sfkopendata, conn)
        df_sfkopendata['都道府県コード又は市区町村コード'] = df_sfkopendata['都道府県コード又は市区町村コード'].astype(str)
        df_sfkopendata['元スプレッドシート名'] = df_sfkopendata['元スプレッドシート名'].astype(str)

    except sqlite3.Error as e:
        st.error(f"データベースからのデータロードエラー: {e}")
        df_school = pd.DataFrame()
        df_sfkopendata = pd.DataFrame()
    finally:
        if conn:
            conn.close()

    return df_school, df_sfkopendata # 複数のデータフレームを返す

# 色を計算するヘルパー関数
def get_color_for_students(student_count, min_s, max_s):
    if (max_s - min_s) <= 0:
        normalized_students = 0.5
    else:
        normalized_students = (student_count - min_s) / (max_s - min_s)

    color_val_r = int(255 * (1 - normalized_students))
    color_val_g = int(255 * (1 - normalized_students))
    color_val_b = 255
    return f'#{color_val_r:02x}{color_val_g:02x}{color_val_b:02x}'

# --- 緯度経度をデータベースに保存する関数 ---
def save_coordinates_to_db(edited_schools_dict):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        updated_count = 0
        for school_id, data in edited_schools_dict.items(): # キーがidになる
            cursor.execute(
                "UPDATE school_data_table SET lat = ?, lon = ? WHERE id = ?",
                (data['lat'], data['lon'], school_id) # idで更新
            )
            if cursor.rowcount > 0:
                updated_count += 1
        conn.commit()
        st.success(f"データベースに緯度経度を保存しました！ ({updated_count}件更新)")
    except sqlite3.Error as e:
        st.error(f"データベース更新エラー: {e}")
    finally:
        if conn:
            conn.close()

# --- 緯度経度修正画面の関数 ---
def edit_coordinates_screen(df_school_data_full):
    st.header("学校緯度経度修正")

    # パスワード認証
    if not st.session_state.get('password_correct_edit_screen', False):
        password = st.text_input("パスワードを入力してください", type="password", key="edit_password_input")
        if password == "yR9$91k7VBjnfP*lqtQ$":
            st.session_state.password_correct_edit_screen = True
            st.success("認証成功！")
            st.rerun()
        elif password:
            st.error("パスワードが間違っています。")
        return

    # 認証成功後のコンテンツ
    st.write("学校の緯度と経度を修正できます。")

    st.subheader('検索条件')

    # 検索条件を4列に配置
    col_search1, col_search2, col_search3, col_search4 = st.columns(4)

    with col_search1:
        # 年月セレクトボックス
        unique_months_edit = sorted(df_school_data_full['Date'].unique(), reverse=True)
        month_options_edit = [pd.Timestamp(dt).strftime("%Y年%m月") for dt in unique_months_edit]

        default_month_index_edit = 0
        if 'selected_month_index_edit' not in st.session_state:
            st.session_state.selected_month_index_edit = default_month_index_edit

        selected_month_str_edit = st.selectbox(
            '年月を選択',
            options=month_options_edit,
            index=st.session_state.selected_month_index_edit,
            key='month_selector_edit'
        )
        selected_date_edit = pd.to_datetime(selected_month_str_edit.replace('年', '-').replace('月', ''))

    with col_search2:
        # 学校種別の選択
        unique_school_types_edit = df_school_data_full['School_Type'].unique()
        public_elementary_index_edit = list(unique_school_types_edit).index('公立小学校') if '公立小学校' in unique_school_types_edit else 0
        selected_school_type_edit = st.selectbox('学校種別を選択', unique_school_types_edit, index=public_elementary_index_edit, key='school_type_edit')

    with col_search3:
        # 市町村の選択
        unique_cities_edit = df_school_data_full['City'].unique().tolist()
        unique_cities_edit.insert(0, 'なし')

        default_city_index_edit = 0
        if '鹿児島市' in unique_cities_edit:
            default_city_index_edit = unique_cities_edit.index('鹿児島市')

        selected_city_edit = st.selectbox('市町村を選択', unique_cities_edit, index=default_city_index_edit, key='city_edit')

    with col_search4:
        # School_Name の選択を追加
        df_temp_filtered_for_school_name = df_school_data_full[
            (df_school_data_full['Date'].dt.year == selected_date_edit.year) &
            (df_school_data_full['Date'].dt.month == selected_date_edit.month) &
            (df_school_data_full['School_Type'] == selected_school_type_edit)
        ].copy()
        if selected_city_edit != 'なし':
            df_temp_filtered_for_school_name = df_temp_filtered_for_school_name[df_temp_filtered_for_school_name['City'] == selected_city_edit]

        unique_school_names_edit = df_temp_filtered_for_school_name['School_Name'].unique().tolist()
        unique_school_names_edit.insert(0, 'なし')
        selected_school_name_edit = st.selectbox('学校名を選択', unique_school_names_edit, index=0, key='school_name_edit')


    # フィルター適用後のデータフレーム作成
    df_edit_filtered = df_school_data_full[
        (df_school_data_full['Date'].dt.year == selected_date_edit.year) &
        (df_school_data_full['Date'].dt.month == selected_date_edit.month) &
        (df_school_data_full['School_Type'] == selected_school_type_edit)
    ].copy()

    if selected_city_edit != 'なし':
        df_edit_filtered = df_edit_filtered[df_edit_filtered['City'] == selected_city_edit]

    if selected_school_name_edit != 'なし':
        df_edit_filtered = df_edit_filtered[df_edit_filtered['School_Name'] == selected_school_name_edit]


    st.subheader("該当学校リスト")

    if selected_city_edit == 'なし' or selected_school_name_edit == 'なし':
        st.info("学校リストを表示するには、市町村と学校名を「なし」以外で選択してください。")
    elif df_edit_filtered.empty:
        st.info("選択された条件に合致する学校がありません。")
    else:
        st.info("以下の学校の緯度・経度を修正できます。")
        edited_schools = {}
        for idx, row in df_edit_filtered.iterrows():
            # idをキーとして使用
            school_id = row['id']
            col_list1, col_list2, col_list3 = st.columns(3)
            with col_list1:
                st.markdown(f"**学校名:** {row['School_Name']} ({pd.Timestamp(row['Date']).strftime('%Y年%m月')})")
            with col_list2:
                new_lat = st.number_input(
                    f"新しい緯度",
                    value=float(row['lat']),
                    format="%.6f",
                    key=f"lat_input_{school_id}" # idをキーに使用
                )
            with col_list3:
                new_lon = st.number_input(
                    f"新しい経度",
                    value=float(row['lon']),
                    format="%.6f",
                    key=f"lon_input_{school_id}" # idをキーに使用
                )
            edited_schools[school_id] = { # idをキーとして保存
                'lat': new_lat,
                'lon': new_lon,
                'Date': row['Date'] # Dateは更新には使用しないが、念のため保持
            }

        if st.button("変更を保存", key="save_coordinates_button"):
            save_coordinates_to_db(edited_schools)
            st.cache_data.clear()
            st.rerun()


# --- アプリケーションのメイン処理 ---
DB_NAME = 'school_data.db'

# データベースファイルが存在しない場合、または空の場合に作成・投入
if not os.path.exists(DB_NAME) or os.path.getsize(DB_NAME) == 0:
    st.info(f"'{DB_NAME}' が見つからないか空です。データベースを作成し、データを投入します。")
    create_and_populate_db(DB_NAME)
else:
    # データベースが存在する場合でも、スキーマ変更（idカラム追加）に対応するため、
    # テーブル構造が古い場合は再作成を促すか、自動でマイグレーションを行う必要がある。
    # 今回はシンプルに、idカラムがない場合は再作成を試みる。
    conn_check = None
    try:
        conn_check = sqlite3.connect(DB_NAME)
        cursor_check = conn_check.cursor()
        cursor_check.execute("PRAGMA table_info(school_data_table)")
        columns = [col[1] for col in cursor_check.fetchall()]
        if 'id' not in columns:
            st.warning("既存のデータベースに 'id' カラムが見つかりませんでした。データベースを再作成します。")
            create_and_populate_db(DB_NAME)
    except sqlite3.Error as e:
        st.error(f"データベーススキーマチェックエラー: {e}")
    finally:
        if conn_check:
            conn_check.close()


# データをロード
df_school, df_sfkopendata = load_data_from_sqlite(DB_NAME)

# --- Streamlit UI ---

# セッションステートの初期化
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'map_view'
if 'password_correct_edit_screen' not in st.session_state:
    st.session_state.password_correct_edit_screen = False
if 'selected_month_index' not in st.session_state:
    st.session_state.selected_month_index = 0
if 'playing' not in st.session_state:
    st.session_state.playing = False


# サイドバーのナビゲーション
st.sidebar.title("ナビゲーション")
if st.sidebar.button("地図表示", key="nav_map_view"):
    st.session_state.current_view = 'map_view'
    st.session_state.password_correct_edit_screen = False
    st.rerun()
if st.sidebar.button("緯度経度修正画面", key="nav_edit_view"):
    st.session_state.current_view = 'edit_view'
    st.rerun()


# --- メインコンテンツの表示ロジック ---
if st.session_state.current_view == 'map_view':
    # --- サイドバーの要素 ---
    st.sidebar.subheader('児童生徒数 絞り込み条件')

    # 年月セレクトボックス
    unique_months = sorted(df_school['Date'].unique(), reverse=True)
    if len(unique_months) == 0:
        st.sidebar.error("利用可能な年月データがありません。データベースのデータを確認してください。")
        st.stop()
    else:
        month_options = [pd.Timestamp(dt).strftime("%Y年%m月") for dt in unique_months]
        selected_month_str = st.sidebar.selectbox(
            '年月を選択',
            options=month_options,
            index=st.session_state.selected_month_index,
            key='map_month_selector'
        )
        current_selected_index = month_options.index(selected_month_str)
        if st.session_state.selected_month_index != current_selected_index:
            st.session_state.playing = False
            st.session_state.selected_month_index = current_selected_index
    selected_date = pd.to_datetime(selected_month_str.replace('年', '-').replace('月', ''))


    # 学校種別の選択
    unique_school_types = df_school['School_Type'].unique()
    public_elementary_index = list(unique_school_types).index('公立小学校') if '公立小学校' in unique_school_types else 0
    selected_school_type = st.sidebar.selectbox('学校種別を選択', unique_school_types, index=public_elementary_index, key='map_school_type')

    # 市町村の選択
    unique_cities = df_school['City'].unique().tolist()
    unique_cities.insert(0, 'すべて')
    selected_city = st.sidebar.selectbox('市町村を選択', unique_cities, index=0, key='map_city')

    # 児童生徒数範囲のselectbox
    student_count_options = {
        'すべて': (None, None),
        '100人未満': (0, 99),
        '100人～300人': (100, 300),
        '301人～500人': (301, 500),
        '501人以上': (501, float('inf'))
    }
    selected_student_count_range_label = st.sidebar.selectbox(
        '児童生徒数範囲',
        options=list(student_count_options.keys()),
        index=0,
        key='map_student_count_range'
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
        index=0,
        key='map_special_class_range'
    )
    selected_special_class_min, selected_special_class_max = special_class_options[selected_special_class_range_label]

    st.sidebar.write('---')
    st.sidebar.subheader('事業所情報 絞り込み条件')

    prefecture_codes = {
        '01': '北海道', '02': '青森県', '03': '岩手県', '04': '宮城県', '05': '秋田県',
        '06': '山形県', '07': '福島県', '08': '茨城県', '09': '栃木県', '10': '群馬県',
        '11': '埼玉県', '12': '千葉県', '13': '東京都', '14': '神奈川県', '15': '新潟県',
        '16': '富山県', '17': '石川県', '18': '福井県', '19': '山梨県', '20': '長野県',
        '21': '岐阜県', '22': '静岡県', '23': '愛知県', '24': '三重県', '25': '滋賀県',
        '26': '京都府', '27': '大阪府', '28': '兵庫県', '29': '奈良県', '30': '和歌山県',
        '31': '鳥取県', '32': '島根県', '33': '岡山県', '34': '広島県', '35': '山口県',
        '36': '徳島県', '37': '香川県', '38': '愛媛県', '39': '高知県', '40': '福岡県',
        '41': '佐賀県', '42': '長崎県', '43': '熊本県', '44': '大分県', '45': '宮崎県',
        '46': '鹿児島県', '47': '沖縄県'
    }
    prefecture_options = ['なし'] + ['すべて'] + [f"{code}: {name}" for code, name in prefecture_codes.items()]

    kagoshima_pref_label = "46: 鹿児島県"
    default_kagoshima_index = prefecture_options.index(kagoshima_pref_label) if kagoshima_pref_label in prefecture_options else 0

    selected_prefecture = st.sidebar.selectbox(
        '都道府県を選択',
        prefecture_options,
        index=default_kagoshima_index,
        key='map_prefecture_selector'
    )

    unique_service_types = df_sfkopendata['サービス種別'].unique().tolist()
    service_type_options = ['なし'] + ['すべて'] + unique_service_types
    selected_service_types = st.sidebar.multiselect(
        'サービス種別を選択',
        options=service_type_options,
        default=['なし'],
        key='map_service_types'
    )


    # --- フィルター適用後のデータフレーム作成 ---
    df_filtered = df_school[
        (df_school['Date'].dt.year == selected_date.year) &
        (df_school['Date'].dt.month == selected_date.month) &
        (df_school['School_Type'] == selected_school_type)
    ].copy()

    if selected_student_count_min is not None:
        df_filtered = df_filtered[
            (df_filtered['Student_Count'] >= selected_student_count_min) &
            (df_filtered['Student_Count'] <= selected_student_count_max)
        ]

    if selected_special_class_min is not None:
        df_filtered = df_filtered[
            (df_filtered['Special_Support_Class_Size'] >= selected_special_class_min) &
            (df_filtered['Special_Support_Class_Size'] <= selected_special_class_max)
        ]

    if selected_city != 'すべて':
        df_filtered = df_filtered[df_filtered['City'] == selected_city]

    # --- sfkopendataのフィルター適用 ---
    df_sfkopendata_filtered = df_sfkopendata.copy()

    if selected_prefecture == 'なし':
        df_sfkopendata_filtered = df_sfkopendata_filtered[0:0]
    elif selected_prefecture != 'すべて':
        pref_code = selected_prefecture.split(':')[0]
        df_sfkopendata_filtered = df_sfkopendata_filtered[
            df_sfkopendata_filtered['都道府県コード又は市区町村コード'].str[:2] == pref_code
        ]

    if selected_service_types:
        if 'なし' in selected_service_types:
            df_sfkopendata_filtered = df_sfkopendata_filtered[0:0]
        elif 'すべて' in selected_service_types and len(selected_service_types) == 1:
            pass
        else:
            filter_types = [s for s in selected_service_types if s != 'すべて']
            if filter_types:
                df_sfkopendata_filtered = df_sfkopendata_filtered[df_sfkopendata_filtered['サービス種別'].isin(filter_types)]
            else:
                df_sfkopendata_filtered = df_sfkopendata_filtered[0:0]
    else:
        df_sfkopendata_filtered = df_sfkopendata_filtered[0:0]


    # --- 3. 地図の表示 ---
    df_map = df_filtered[['School_Name', 'Student_Count', 'Special_Support_Class_Size', 'lat', 'lon']]

    map_center = [31.5960, 130.5580]
    m = folium.Map(location=map_center, zoom_start=10)

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
                color='blue', # Changed to blue for schools to distinguish from red for businesses
                weight=1,
                fill=True,
                fill_color=color_hex,
                fill_opacity=0.7,
                tooltip=f"{row['School_Name']}<br>児童生徒数 {row['Student_Count']}人<br>特別支援学級人数 {row['Special_Support_Class_Size']}人"
            ).add_to(m)

    if not df_sfkopendata_filtered.empty:
        for idx, row in df_sfkopendata_filtered.iterrows():
            if pd.notna(row['事業所緯度']) and pd.notna(row['事業所経度']):
                popup_html = f"""
                <b>法人名:</b> {row['法人の名称']}<br>
                <b>事業所名:</b> {row['事業所の名称']}<br>
                <b>サービス種別:</b> {row['サービス種別']}<br>
                <b>住所:</b> {row['事業所住所（市区町村）']}{row['事業所住所（番地以降）']}<br>
                <b>定員:</b> {row['定員']}<br>
                <button onclick="
                    var mapLink = `https://www.google.com/maps/search/?api=1&query={row['事業所緯度']},{row['事業所経度']}`;
                    window.open(mapLink, '_blank');
                ">Googleマップで開く</button>
                """
                folium.CircleMarker(
                    location=[row['事業所緯度'], row['事業所経度']],
                    radius=8,
                    color='red',
                    weight=2,
                    fill=True,
                    fill_color='red',
                    fill_opacity=0.6,
                    tooltip=folium.Tooltip(f"{row['事業所の名称']}"),
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(m)
    else:
        if selected_prefecture != 'なし' and ('なし' not in selected_service_types):
            st.info("選択された条件に合致する事業所情報がないため、地図には表示されません。")

    st_folium(m, width=1366, height=768, returned_objects=[], key="folium_map")

    # --- 凡例の表示 (地図の下に横並びで) ---
    st.markdown("""
        <style>
            .legend-container {
                display: flex;
                flex-wrap: wrap; /* Allow items to wrap to the next line */
                gap: 20px; /* Space between legend items */
                margin-top: 0px;
                margin-bottom: 0px;
            }
            .legend-item {
                display: flex;
                align-items: center;
            }
            .color-box {
                width: 20px;
                height: 20px;
                margin-right: 10px;
                border: 1px solid #ccc;
                border-radius: 50%; /* Make school markers round */
            }
            .red-circle-box {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background-color: red;
                border: 2px solid red;
                margin-right: 10px;
            }
            .blue-circle-box {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background-color: blue; /* Changed to blue for schools */
                border: 2px solid blue;
                margin-right: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="legend-container">', unsafe_allow_html=True)
        st.markdown('凡例')
        # 学校の凡例
        if not df_map.empty:
            st.markdown('<div class="legend-item"><div class="blue-circle-box"></div><span>学校: 児童生徒数 濃/大:多、淡/小:少</span></div>', unsafe_allow_html=True)
        else:
            st.info("地図凡例を表示するための学校データがありません。")

        # 事業所の凡例
        if selected_prefecture != 'なし' and ('なし' not in selected_service_types):
            st.markdown("""
                <div class="legend-item">
                    <div class="red-circle-box"></div>
                    <span>事業所(2025年3月末時点)</span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


    # --- 4. 児童生徒数推移グラフ ---

    df_total_students_over_time = df_school[
        (df_school['School_Type'] == selected_school_type)
    ].copy()

    if selected_city != 'すべて':
        df_total_students_over_time = df_total_students_over_time[df_total_students_over_time['City'] == selected_city]

    if selected_student_count_min is not None:
        df_total_students_over_time = df_total_students_over_time[
            (df_total_students_over_time['Student_Count'] >= selected_student_count_min) &
            (df_total_students_over_time['Student_Count'] <= selected_student_count_max)
        ]

    if selected_special_class_min is not None:
        df_total_students_over_time = df_total_students_over_time[
            (df_total_students_over_time['Special_Support_Class_Size'] >= selected_special_class_min) &
            (df_total_students_over_time['Special_Support_Class_Size'] <= selected_special_class_max)
        ]

    df_total_students_over_time = df_total_students_over_time.groupby('Date')['Student_Count'].sum().reset_index()

    graph_title_city_part = selected_city if selected_city != 'すべて' else '全市町村'
    fig_line_students = px.line(df_total_students_over_time,
                       x='Date',
                       y='Student_Count',
                       title=f'{graph_title_city_part}の{selected_school_type}全体の児童生徒数推移')
    fig_line_students.update_layout(xaxis_title="年月", yaxis_title="児童生徒数", hovermode="x unified")
    st.plotly_chart(fig_line_students, use_container_width=True)

    if not df_filtered.empty:
        selected_school = st.selectbox('詳細を見たい学校を選択', df_filtered['School_Name'].unique())

        if selected_school:
            df_school_data = df_school[
                (df_school['School_Name'] == selected_school) &
                ((df_school['City'] == selected_city) if selected_city != 'すべて' else True) &
                (df_school['School_Type'] == selected_school_type)
            ].sort_values('Date')

            if selected_student_count_min is not None:
                df_school_data = df_school_data[
                    (df_school_data['Student_Count'] >= selected_student_count_min) &
                    (df_school_data['Student_Count'] <= selected_student_count_max)
                ]

            if selected_special_class_min is not None:
                df_school_data = df_school_data[
                    (df_school_data['Special_Support_Class_Size'] >= selected_special_class_min) &
                    (df_school_data['Special_Support_Class_Size'] <= selected_special_class_max)
                ]

            if df_school_data.empty:
                st.info(f"{selected_school}のデータは、選択された市町村または学校種別、または児童生徒数・特別支援学級人数のフィルターに合致しません。")
            else:
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
                                    color_discrete_sequence=['#28a745'])
                    fig_bar_special.update_layout(xaxis_title="年月", yaxis_title="特別支援学級人数")
                    st.plotly_chart(fig_bar_special, use_container_width=True)

    else:
        st.info("選択された条件に合致する児童生徒数推移グラフを表示するためのデータがありません。")

elif st.session_state.current_view == 'edit_view':
    edit_coordinates_screen(df_school)

# --- Disclaimer (moved to the very bottom) ---
st.info("免責事項:本アプリケーションの利用により生じたいかなる種類の損害、損失、不利益に対しても、開発者は一切の責任を負いません。本アプリケーションは現状有姿で提供され、開発者はその完全性、正確性、信頼性、特定の目的への適合性について、いかなる保証も行いません。利用者は、本アプリケーションの利用から生じる可能性のあるすべてのリスクを認識し、自己の責任において利用するものとします。")
