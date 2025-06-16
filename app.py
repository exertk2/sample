import streamlit as st
import sqlite3
from datetime import datetime
import pytz # タイムゾーンを扱うためにpytzをインポート

# データベース接続
def get_db_connection():
    conn = sqlite3.connect('commute_app.db')
    conn.row_factory = sqlite3.Row
    return conn

# データベース初期化
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
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
    conn.close()

# アプリケーション起動時にDB初期化
init_db()

# 日本時間のタイムゾーンを設定
JST = pytz.timezone('Asia/Tokyo')

st.set_page_config(layout="wide")
st.title("通勤申請アプリ")

# --- メニュー ---
menu = ["申請入力", "申請一覧", "職員登録"]
choice = st.sidebar.selectbox("メニュー", menu)

# --- 職員登録 ---
if choice == "職員登録":
    st.header("職員登録")
    with st.form("staff_registration_form"):
        staff_name = st.text_input("氏名")
        submit_button = st.form_submit_button("登録")

        if submit_button:
            if staff_name:
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO staffs (name) VALUES (?)", (staff_name,))
                    conn.commit()
                    st.success(f"職員「{staff_name}」を登録しました。")
                except sqlite3.IntegrityError:
                    st.error("この職員名は既に登録されています。")
                finally:
                    conn.close()
            else:
                st.warning("氏名を入力してください。")

    st.subheader("登録済職員一覧")
    conn = get_db_connection()
    staffs = conn.execute("SELECT * FROM staffs").fetchall()
    conn.close()
    if staffs:
        for staff in staffs:
            st.write(f"- {staff['name']}")
    else:
        st.info("登録されている職員はいません。")

# --- 申請入力 ---
elif choice == "申請入力":
    st.header("申請入力")

    conn = get_db_connection()
    staffs = conn.execute("SELECT id, name FROM staffs").fetchall()
    conn.close()
    staff_options = {staff['name']: staff['id'] for staff in staffs}
    staff_names = list(staff_options.keys())

    if not staff_names:
        st.warning("先に職員登録を行ってください。")
    else:
        with st.form("application_input_form"):
            st.subheader("検索条件 (申請の重複チェックに使用)")
            selected_staff_name = st.selectbox("職員氏名", staff_names, key="search_staff_name")
            selected_staff_id = staff_options[selected_staff_name]

            current_year = datetime.now().year
            fiscal_years = [f"{year}年度" for year in range(current_year - 2, current_year + 3)]
            selected_fiscal_year_str = st.selectbox("年度", fiscal_years, key="search_fiscal_year")
            selected_fiscal_year = int(selected_fiscal_year_str.replace("年度", ""))


            st.subheader("入力項目")
            car_name = st.text_input("車名", key="car_name_input")
            color = st.text_input("色", key="color_input")
            number = st.number_input("ナンバー (4桁のみ)", min_value=0, max_value=9999, step=1, key="number_input")

            col1, col2, col3 = st.columns(3)
            with col1:
                unlimited_personal = st.checkbox("対人無制限チェック", key="unlimited_personal_check")
            with col2:
                unlimited_property = st.checkbox("対物無制限チェック", key="unlimited_property_check")
            with col3:
                commuting_purpose = st.checkbox("通勤目的チェック", key="commuting_purpose_check")
                if commuting_purpose: # 「通勤目的チェック」がONの場合のみ表示
                    purpose_unknown = st.checkbox("目的不明チェック", key="purpose_unknown_check")
                else:
                    purpose_unknown = False # 「通勤目的チェック」がOFFなら目的不明は常にFalse

            submit_button = st.form_submit_button("登録")

            if submit_button:
                # 重複チェック: 同一職員、同一年度、同一ナンバーのレコードがないか確認
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM applications WHERE staff_id = ? AND fiscal_year = ? AND number = ?",
                    (selected_staff_id, selected_fiscal_year, number)
                )
                duplicate_count = cursor.fetchone()[0]

                if duplicate_count > 0:
                    st.warning("この職員、年度、ナンバーの組み合わせは既に登録されています。")
                else:
                    try:
                        # 登録日時 (日本時間)
                        now_jst = datetime.now(JST)

                        # 年度換算 (登録日時の年度を使用)
                        # fiscal_year_from_registration = now_jst.year if now_jst.month >= 4 else now_jst.year - 1 # 4月始まりの年度

                        cursor.execute(
                            "INSERT INTO applications (staff_id, car_name, color, number, unlimited_personal, unlimited_property, commuting_purpose, purpose_unknown, registration_timestamp, fiscal_year) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (selected_staff_id, car_name, color, number, unlimited_personal, unlimited_property, commuting_purpose, purpose_unknown, now_jst, selected_fiscal_year)
                        )
                        conn.commit()
                        st.success("申請を登録しました。")
                    except Exception as e:
                        st.error(f"登録中にエラーが発生しました: {e}")
                    finally:
                        conn.close()

# --- 申請一覧 ---
elif choice == "申請一覧":
    st.header("申請一覧")

    conn = get_db_connection()
    staffs = conn.execute("SELECT id, name FROM staffs").fetchall()
    conn.close()
    staff_names = {staff['id']: staff['name'] for staff in staffs} # IDから名前を引けるように辞書を作成

    # 検索条件
    st.subheader("検索条件")
    search_staff_name = st.selectbox("職員氏名 (検索)", [""] + list(staff_names.values()), key="list_search_staff_name")
    search_fiscal_year_options = [""] + [f"{year}年度" for year in range(datetime.now().year - 5, datetime.now().year + 2)]
    search_fiscal_year_str = st.selectbox("年度 (検索)", search_fiscal_year_options, key="list_search_fiscal_year")
    search_fiscal_year = int(search_fiscal_year_str.replace("年度", "")) if search_fiscal_year_str else None


    query = """
        SELECT
            a.id,
            s.name AS staff_name,
            a.car_name,
            a.color,
            a.number,
            a.unlimited_personal,
            a.unlimited_property,
            a.commuting_purpose,
            a.purpose_unknown,
            a.registration_timestamp,
            a.fiscal_year
        FROM applications a
        JOIN staffs s ON a.staff_id = s.id
        WHERE 1=1
    """
    params = []

    if search_staff_name:
        query += " AND s.name = ?"
        params.append(search_staff_name)
    if search_fiscal_year:
        query += " AND a.fiscal_year = ?"
        params.append(search_fiscal_year)

    conn = get_db_connection()
    applications = conn.execute(query, params).fetchall()
    conn.close()

    if applications:
        st.write(f"{len(applications)}件の申請が見つかりました。")
        for app in applications:
            st.markdown(f"---")
            st.write(f"**申請ID:** {app['id']}")
            st.write(f"**職員氏名:** {app['staff_name']}")
            st.write(f"**車名:** {app['car_name']}")
            st.write(f"**色:** {app['color']}")
            st.write(f"**ナンバー:** {app['number']}")
            st.write(f"**対人無制限:** {'✔' if app['unlimited_personal'] else ' '}")
            st.write(f"**対物無制限:** {'✔' if app['unlimited_property'] else ' '}")
            st.write(f"**通勤目的:** {'✔' if app['commuting_purpose'] else ' '}")
            if app['commuting_purpose']: # 通勤目的がチェックされている場合のみ表示
                st.write(f"**目的不明:** {'✔' if app['purpose_unknown'] else ' '}")
            st.write(f"**登録日時:** {app['registration_timestamp']}")
            st.write(f"**年度:** {app['fiscal_year']}年度")
    else:
        st.info("該当する申請はありません。")
