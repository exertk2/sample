import streamlit as st
import sqlite3
from datetime import datetime
import pytz
import pandas as pd

# ==============================================================================
# 定数・初期設定 (Constants & Initial Setup)
# ==============================================================================
DB_NAME = 'commute_app.db'
JST = pytz.timezone('Asia/Tokyo')

# ==============================================================================
# データベース関連の関数 (Database Functions)
# ==============================================================================

def get_db_connection():
    """データベース接続を取得します。"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """データベーステーブルを初期化します。存在しない場合のみ作成されます。"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 職員テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS staffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            ''')
            # 申請テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER NOT NULL,
                    car_name TEXT,
                    color TEXT,
                    number INTEGER,
                    unlimited_personal BOOLEAN,
                    unlimited_property BOOLEAN,
                    commuting_purpose BOOLEAN,
                    purpose_unknown BOOLEAN,
                    registration_timestamp DATETIME,
                    fiscal_year INTEGER,
                    FOREIGN KEY (staff_id) REFERENCES staffs (id)
                )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        st.error(f"データベース初期化中にエラーが発生しました: {e}")

def get_all_staffs():
    """登録済みの全職員を取得します。"""
    try:
        with get_db_connection() as conn:
            staffs = conn.execute("SELECT id, name FROM staffs ORDER BY id").fetchall()
            return staffs
    except sqlite3.Error as e:
        st.error(f"職員情報の取得中にエラーが発生しました: {e}")
        return []

def add_staff(name):
    """新しい職員をデータベースに登録します。"""
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO staffs (name) VALUES (?)", (name,))
            conn.commit()
            st.success(f"職員「{name}」を登録しました。")
    except sqlite3.IntegrityError:
        st.error("この職員名は既に登録されています。")
    except sqlite3.Error as e:
        st.error(f"職員登録中にエラーが発生しました: {e}")

def find_application(staff_id, fiscal_year, number):
    """指定された条件に一致する申請データを検索します。"""
    try:
        with get_db_connection() as conn:
            query = "SELECT * FROM applications WHERE staff_id = ? AND fiscal_year = ? AND number = ?"
            application = conn.execute(query, (staff_id, fiscal_year, number)).fetchone()
            return application
    except sqlite3.Error as e:
        st.error(f"申請データの検索中にエラーが発生しました: {e}")
        return None

def upsert_application(data, is_update):
    """申請データを新規登録または更新します。"""
    try:
        with get_db_connection() as conn:
            if is_update:
                # 更新処理
                query = """
                    UPDATE applications
                    SET car_name = ?, color = ?, unlimited_personal = ?, unlimited_property = ?,
                        commuting_purpose = ?, purpose_unknown = ?, registration_timestamp = ?
                    WHERE staff_id = ? AND fiscal_year = ? AND number = ?
                """
                params = (
                    data['car_name'], data['color'], data['unlimited_personal'], data['unlimited_property'],
                    data['commuting_purpose'], data['purpose_unknown'], data['timestamp'],
                    data['staff_id'], data['fiscal_year'], data['number']
                )
                conn.execute(query, params)
                st.success("申請を修正しました。")
            else:
                # 新規登録処理
                query = """
                    INSERT INTO applications 
                    (staff_id, car_name, color, number, unlimited_personal, unlimited_property, 
                     commuting_purpose, purpose_unknown, registration_timestamp, fiscal_year) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    data['staff_id'], data['car_name'], data['color'], data['number'], 
                    data['unlimited_personal'], data['unlimited_property'], data['commuting_purpose'], 
                    data['purpose_unknown'], data['timestamp'], data['fiscal_year']
                )
                conn.execute(query, params)
                st.success("申請を登録しました。")
            conn.commit()
    except sqlite3.Error as e:
        st.error(f"申請の登録/修正中にエラーが発生しました: {e}")

def search_applications(fiscal_year=None, number=None):
    """条件に基づいて申請一覧を検索します。"""
    try:
        with get_db_connection() as conn:
            query = """
                SELECT a.id, s.name AS staff_name, a.car_name, a.color, a.number,
                       a.unlimited_personal, a.unlimited_property, a.commuting_purpose,
                       a.purpose_unknown, a.registration_timestamp, a.fiscal_year
                FROM applications a JOIN staffs s ON a.staff_id = s.id
                WHERE 1=1
            """
            params = []
            if fiscal_year:
                query += " AND a.fiscal_year = ?"
                params.append(fiscal_year)
            if number is not None:
                query += " AND a.number = ?"
                params.append(number)
            
            query += " ORDER BY a.registration_timestamp DESC"
            return conn.execute(query, params).fetchall()
    except sqlite3.Error as e:
        st.error(f"申請一覧の検索中にエラーが発生しました: {e}")
        return []

# ==============================================================================
# ヘルパー関数 (Helper Functions)
# ==============================================================================

def get_current_fiscal_year():
    """現在の日本の日付に基づいて年度を返します。"""
    now = datetime.now(JST)
    return now.year if now.month >= 4 else now.year - 1

# ==============================================================================
# UI表示関連の関数 (UI Display Functions)
# ==============================================================================

def show_staff_registration_page():
    """職員登録ページのUIを表示します。"""
    st.header("職員登録")
    with st.form("staff_registration_form"):
        staff_name = st.text_input("氏名")
        submitted = st.form_submit_button("登録")

        if submitted and staff_name:
            add_staff(staff_name)
        elif submitted:
            st.warning("氏名を入力してください。")

    st.subheader("登録済職員一覧")
    staffs = get_all_staffs()
    if staffs:
        df_staffs = pd.DataFrame([dict(s) for s in staffs])
        st.dataframe(df_staffs, hide_index=True)
    else:
        st.info("登録されている職員はいません。")


def show_application_input_page():
    """申請入力ページのUIを表示します。"""
    st.header("申請入力")

    staffs = get_all_staffs()
    if not staffs:
        st.warning("先に職員登録を行ってください。")
        return

    staff_options = {staff['name']: staff['id'] for staff in staffs}
    staff_names = list(staff_options.keys())

    with st.form("application_input_form"):
        st.subheader("申請対象の選択（上書き対象の検索）")

        # --- 申請対象の選択（タブ遷移：左->右）---
        # 1. 職員氏名, 2. 年度, 3. ナンバー
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_staff_name = st.selectbox("職員氏名", staff_names, key="staff_name_select")
        
        with col2:
            current_fiscal_year = get_current_fiscal_year()
            fiscal_year_options = [f"{y}年度" for y in range(current_fiscal_year - 2, current_fiscal_year + 3)]
            default_fy_index = fiscal_year_options.index(f"{current_fiscal_year}年度") if f"{current_fiscal_year}年度" in fiscal_year_options else 0
            selected_fiscal_year_str = st.selectbox("年度", fiscal_year_options, index=default_fy_index, key="fiscal_year_select")
            selected_fiscal_year = int(selected_fiscal_year_str.replace("年度", ""))
            
        with col3:
            input_number = st.number_input("ナンバー (4桁)", min_value=0, max_value=9999, step=1, key="number_input")

        # 既存データの検索と初期値設定
        selected_staff_id = staff_options.get(selected_staff_name)
        existing_app = None
        if selected_staff_id is not None and input_number is not None:
            existing_app = find_application(selected_staff_id, selected_fiscal_year, input_number)
        
        # 初期値の辞書を作成
        initial_values = {
            'car_name': existing_app['car_name'] if existing_app else "",
            'color': existing_app['color'] if existing_app else "",
            'unlimited_personal': existing_app['unlimited_personal'] if existing_app else False,
            'unlimited_property': existing_app['unlimited_property'] if existing_app else False,
            'commuting_purpose': existing_app['commuting_purpose'] if existing_app else False,
            'purpose_unknown': existing_app['purpose_unknown'] if existing_app else False,
        }

        st.subheader("入力項目")

        # --- 入力項目（タブ遷移：左->右）---
        # 4. 車名, 5. 色
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            car_name = st.text_input("車名", value=initial_values['car_name'])
        with col_input2:
            color = st.text_input("色", value=initial_values['color'])
        
        # --- チェックボックス（タブ遷移：左->右）---
        # 6. 対人, 7. 対物, 8. 通勤, 9. 不明
        col_check1, col_check2, col_check3, col_check4 = st.columns(4)
        with col_check1:
            unlimited_personal = st.checkbox("対人無制限", value=initial_values['unlimited_personal'])
        with col_check2:
            unlimited_property = st.checkbox("対物無制限", value=initial_values['unlimited_property'])
        with col_check3:
            commuting_purpose = st.checkbox("通勤目的", value=initial_values['commuting_purpose'])
        with col_check4:
            purpose_unknown = st.checkbox("目的不明", value=initial_values['purpose_unknown'])

        # 10. 登録/修正ボタン
        submitted = st.form_submit_button("登録 / 修正")

        if submitted:
            if not all([selected_staff_id, car_name, color]):
                st.error("職員氏名、車名、色は必須項目です。")
            else:
                application_data = {
                    'staff_id': selected_staff_id,
                    'fiscal_year': selected_fiscal_year,
                    'number': input_number,
                    'car_name': car_name,
                    'color': color,
                    'unlimited_personal': unlimited_personal,
                    'unlimited_property': unlimited_property,
                    'commuting_purpose': commuting_purpose,
                    'purpose_unknown': purpose_unknown,
                    'timestamp': datetime.now(JST)
                }
                upsert_application(application_data, is_update=existing_app is not None)

def show_application_list_page():
    """申請一覧ページのUIを表示します。"""
    st.header("申請一覧")
    st.subheader("検索条件")

    # --- 検索条件（タブ遷移：左->右）---
    col_search1, col_search2 = st.columns(2)
    with col_search1:
        current_fiscal_year = get_current_fiscal_year()
        fy_options = ["すべて"] + [f"{y}年度" for y in range(current_fiscal_year - 5, current_fiscal_year + 2)]
        default_fy_index = fy_options.index(f"{current_fiscal_year}年度") if f"{current_fiscal_year}年度" in fy_options else 0
        search_fy_str = st.selectbox("年度", fy_options, index=default_fy_index, key="list_search_fy")
        search_fiscal_year = int(search_fy_str.replace("年度", "")) if search_fy_str != "すべて" else None
    
    with col_search2:
        search_number_str = st.text_input("ナンバー (4桁で検索)", key="list_search_number")
        search_number = None
        if search_number_str:
            if search_number_str.isdigit() and len(search_number_str) == 4:
                search_number = int(search_number_str)
            else:
                st.warning("ナンバーは4桁の数値を入力してください。")

    # --- 検索結果 ---
    applications = search_applications(fiscal_year=search_fiscal_year, number=search_number)

    if applications:
        st.write(f"{len(applications)}件の申請が見つかりました。")
        df = pd.DataFrame([dict(row) for row in applications])

        # 表示用にデータを加工
        df['対人無制限'] = df['unlimited_personal'].apply(lambda x: '✔' if x else '')
        df['対物無制限'] = df['unlimited_property'].apply(lambda x: '✔' if x else '')
        df['通勤目的'] = df['commuting_purpose'].apply(lambda x: '✔' if x else '')
        df['目的不明'] = df['purpose_unknown'].apply(lambda x: '✔' if x else '')
        df['年度'] = df['fiscal_year'].astype(str) + '年度'
        df['登録日時'] = pd.to_datetime(df['registration_timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

        # 表示するカラムの選択とリネーム
        df_display = df.rename(columns={
            'id': 'ID', 'staff_name': '職員氏名', 'car_name': '車名', 'color': '色', 'number': 'ナンバー'
        })
        
        display_columns = [
            'ID', '年度', '職員氏名', '車名', '色', 'ナンバー', '対人無制限', 
            '対物無制限', '通勤目的', '目的不明', '登録日時'
        ]
        st.dataframe(df_display[display_columns], hide_index=True)

    else:
        st.info("該当する申請はありません。")

# ==============================================================================
# メイン処理 (Main Application Logic)
# ==============================================================================

def main():
    """アプリケーションのメインエントリポイント"""
    st.set_page_config(layout="wide")
    init_db()  # アプリケーション起動時にDBを初期化

    st.sidebar.title("通勤車両管理アプリ")
    menu_options = ["申請入力", "申請一覧", "職員登録"]
    choice = st.sidebar.radio("メニュー", menu_options)

    page_functions = {
        "申請入力": show_application_input_page,
        "申請一覧": show_application_list_page,
        "職員登録": show_staff_registration_page,
    }
    
    # 選択されたメニューに応じた関数を実行
    page_functions[choice]()


if __name__ == "__main__":
    main()
