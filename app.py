import streamlit as st
import sqlite3
from datetime import datetime
import pytz # タイムゾーンを扱うためにpytzをインポート
import pandas as pd # データフレーム表示のためにpandasをインポート

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

# --- メニュー (ラジオボタン) ---
menu = ["申請入力", "申請一覧", "職員登録"]
choice = st.sidebar.radio("通勤車両管理アプリ", menu)

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
        # Streamlitのデータフレーム表示を使用
        df_staffs = pd.DataFrame([dict(row) for row in staffs])
        st.dataframe(df_staffs, hide_index=True)
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
            st.subheader("申請対象の選択（上書き対象の検索にも利用）")

            # 現在の年月日から年度を判定
            now = datetime.now(JST)
            if now.month >= 4: # 4月～12月は現在の年
                initial_fiscal_year = now.year
            else: # 1月～3月は前年
                initial_fiscal_year = now.year - 1

            # 年度選択肢と初期値のインデックスを設定
            fiscal_years_options = [f"{year}年度" for year in range(initial_fiscal_year - 2, initial_fiscal_year + 3)]
            try:
                default_fiscal_year_index = fiscal_years_options.index(f"{initial_fiscal_year}年度")
            except ValueError:
                default_fiscal_year_index = 0 # 見つからない場合は最初の要素を選択

            # 申請対象の選択部分を横に並べる
            col_select1, col_select2, col_select3 = st.columns(3)
            with col_select1:
                selected_staff_name = st.selectbox("職員氏名", staff_names, key="search_staff_name")
            with col_select2:
                selected_fiscal_year_str = st.selectbox(
                    "年度",
                    fiscal_years_options,
                    index=default_fiscal_year_index, # 初期値を設定
                    key="search_fiscal_year"
                )
                selected_fiscal_year = int(selected_fiscal_year_str.replace("年度", ""))
            with col_select3:
                input_number = st.number_input("ナンバー (4桁のみ)", min_value=0, max_value=9999, step=1, key="number_input")


            # 職員名が選択されていない場合（初期状態など）のハンドリング
            if selected_staff_name:
                selected_staff_id = staff_options[selected_staff_name]
            else:
                selected_staff_id = None
                st.info("職員氏名を選択してください。")
                st.stop() # 職員が選択されていなければ処理を中断

            # 既存データがあれば、初期値としてフォームにセット
            existing_application = None
            if selected_staff_id is not None and input_number is not None:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM applications WHERE staff_id = ? AND fiscal_year = ? AND number = ?",
                    (selected_staff_id, selected_fiscal_year, input_number)
                )
                existing_application = cursor.fetchone()
                conn.close()

            # 既存データが存在する場合、その値を初期値として設定
            initial_car_name = existing_application['car_name'] if existing_application else ""
            initial_color = existing_application['color'] if existing_application else ""
            initial_unlimited_personal = existing_application['unlimited_personal'] if existing_application else False
            initial_unlimited_property = existing_application['unlimited_property'] if existing_application else False
            initial_commuting_purpose = existing_application['commuting_purpose'] if existing_application else False
            initial_purpose_unknown = existing_application['purpose_unknown'] if existing_application else False


            st.subheader("入力項目")

            # 入力項目部分を横に並べる
            col_input1, col_input2 = st.columns(2)
            with col_input1:
                car_name = st.text_input("車名", value=initial_car_name, key="car_name_input")
            with col_input2:
                color = st.text_input("色", value=initial_color, key="color_input")

            col_checkbox1, col_checkbox2, col_checkbox3, col_checkbox4 = st.columns(4)
            with col_checkbox1:
                unlimited_personal = st.checkbox("対人無制限チェック", value=initial_unlimited_personal, key="unlimited_personal_check")
            with col_checkbox2:
                unlimited_property = st.checkbox("対物無制限チェック", value=initial_property_purpose, key="unlimited_property_check")
            with col_checkbox3:
                commuting_purpose = st.checkbox("通勤目的チェック", value=initial_commuting_purpose, key="commuting_purpose_check")
            with col_checkbox4:
                purpose_unknown = st.checkbox("目的不明チェック", value=initial_purpose_unknown, key="purpose_unknown_check")


            submit_button = st.form_submit_button("登録 / 修正")

            if submit_button:
                if selected_staff_id is None:
                    st.error("職員氏名を選択してください。")
                elif not car_name:
                    st.error("車名を入力してください。")
                elif not color:
                    st.error("色を入力してください。")
                else:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        now_jst = datetime.now(JST)

                        if existing_application:
                            # 既存データが存在する場合、更新
                            cursor.execute(
                                """
                                UPDATE applications
                                SET car_name = ?, color = ?, unlimited_personal = ?, unlimited_property = ?,
                                    commuting_purpose = ?, purpose_unknown = ?, registration_timestamp = ?
                                WHERE staff_id = ? AND fiscal_year = ? AND number = ?
                                """,
                                (car_name, color, unlimited_personal, unlimited_property,
                                 commuting_purpose, purpose_unknown, now_jst,
                                 selected_staff_id, selected_fiscal_year, input_number)
                            )
                            st.success("申請を修正しました。")
                        else:
                            # 新規登録
                            cursor.execute(
                                "INSERT INTO applications (staff_id, car_name, color, number, unlimited_personal, unlimited_property, commuting_purpose, purpose_unknown, registration_timestamp, fiscal_year) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (selected_staff_id, car_name, color, input_number, unlimited_personal, unlimited_property, commuting_purpose, purpose_unknown, now_jst, selected_fiscal_year)
                            )
                            st.success("申請を登録しました。")
                        conn.commit()
                    except Exception as e:
                        st.error(f"処理中にエラーが発生しました: {e}")
                    finally:
                        conn.close()

# --- 申請一覧 ---
elif choice == "申請一覧":
    st.header("申請一覧")

    conn = get_db_connection()
    staffs = conn.execute("SELECT id, name FROM staffs").fetchall()
    conn.close()
    staff_names_map = {staff['id']: staff['name'] for staff in staffs} # IDから名前を引けるように辞書を作成

    # 検索条件
    st.subheader("検索条件")

    # 現在の年月日から年度を判定 (申請入力と同様のロジック)
    now = datetime.now(JST)
    if now.month >= 4: # 4月～12月は現在の年
        initial_fiscal_year_list = now.year
    else: # 1月～3月は前年
        initial_fiscal_year_list = now.year - 1

    # 年度選択肢と初期値のインデックスを設定 (申請一覧では「すべて」オプションがあるため少し異なる)
    search_fiscal_year_options = ["すべて"] + [f"{year}年度" for year in range(initial_fiscal_year_list - 5, initial_fiscal_year_list + 2)]
    try:
        # 「すべて」を除いたリストでインデックスを検索し、+1する
        default_fiscal_year_list_index = search_fiscal_year_options.index(f"{initial_fiscal_year_list}年度")
    except ValueError:
        default_fiscal_year_list_index = 0 # 見つからない場合は「すべて」を選択

    col_list_search1, col_list_search2 = st.columns(2) # 検索条件を横に並べるために2カラムにする

    with col_list_search1:
        search_fiscal_year_str = st.selectbox(
            "年度 (検索)",
            search_fiscal_year_options,
            index=default_fiscal_year_list_index, # 初期値を設定
            key="list_search_fiscal_year"
        )
        search_fiscal_year = int(search_fiscal_year_str.replace("年度", "")) if search_fiscal_year_str != "すべて" else None

    with col_list_search2:
        # ナンバー検索はテキスト入力とし、入力がなければ全件対象
        search_number_str = st.text_input("ナンバー (4桁のみ、検索)", key="list_search_number")
        search_number = int(search_number_str) if search_number_str.isdigit() and len(search_number_str) == 4 else None
        if search_number_str and (not search_number_str.isdigit() or len(search_number_str) != 4):
            st.warning("ナンバーは4桁の数値を入力してください。")


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

    if search_fiscal_year:
        query += " AND a.fiscal_year = ?"
        params.append(search_fiscal_year)
    if search_number is not None: # Noneでない場合のみ条件を追加
        query += " AND a.number = ?"
        params.append(search_number)

    # 登録日時が新しい順にソート
    query += " ORDER BY a.registration_timestamp DESC"

    conn = get_db_connection()
    applications = conn.execute(query, params).fetchall()
    conn.close()

    if applications:
        st.write(f"{len(applications)}件の申請が見つかりました。")

        # データフレームに変換して表示
        df_applications = pd.DataFrame([dict(row) for row in applications])

        # 表示用の加工
        df_applications['対人無制限'] = df_applications['unlimited_personal'].apply(lambda x: '✔' if x else '')
        df_applications['対物無制限'] = df_applications['unlimited_property'].apply(lambda x: '✔' if x else '')
        df_applications['通勤目的'] = df_applications['commuting_purpose'].apply(lambda x: '✔' if x else '')
        df_applications['目的不明'] = df_applications['purpose_unknown'].apply(lambda x: '✔' if x else '')
        df_applications['年度'] = df_applications['fiscal_year'].astype(str) + '年度'

        # 表示するカラムを選択・並び替え
        display_columns = [
            'id',
            'staff_name',
            '年度',
            'car_name',
            'color',
            'number',
            '対人無制限',
            '対物無制限',
            '通勤目的',
            '目的不明',
            'registration_timestamp'
        ]
        df_display = df_applications[display_columns]

        # カラム名を日本語にリネーム
        df_display = df_display.rename(columns={
            'id': 'ID',
            'staff_name': '職員氏名',
            'car_name': '車名',
            'color': '色',
            'number': 'ナンバー',
            'registration_timestamp': '登録日時'
        })

        st.dataframe(df_display, hide_index=True)
    else:
        st.info("該当する申請はありません。")
