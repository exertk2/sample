import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, time
import pytz # Import pytz for timezone handling

# --- データベース設定 ---
DB_FILE = "day_log.db"

# Define Japan Standard Time (JST)
JST = pytz.timezone('Asia/Tokyo')

def get_db_connection():
    """データベース接続を取得する"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """アプリケーションに必要なテーブルを作成する"""
    conn = get_db_connection()
    c = conn.cursor()

    # 職員テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS v_current_employee_information (
            employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL UNIQUE,
            employee_kana TEXT,
            department_code1 INTEGER,
            department_code2 INTEGER,
            department_code3 INTEGER,
            department_code4 INTEGER,
            department_name4 INTEGER,
            department_code5 INTEGER,
            retirement_date TEXT
        )
    ''')

    # 利用者テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_code INTEGER UNIQUE,
            name TEXT NOT NULL,
            kana TEXT,
            birthday DATE,
            gender TEXT,
            patient_category TEXT,
            is_active BOOLEAN,
            start_date DATE,
            end_date DATE,
            use_days TEXT, -- "月,火,水" のようにカンマ区切りで保存
            medication_days TEXT,
            bath_days TEXT
        )
    ''')

    # 日誌テーブル
    # 簡単化のため、仕様書の複数項目を1つのテーブルに統合
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            log_date DATE,
            is_absent BOOLEAN DEFAULT 0,
            temperature REAL,
            pulse INTEGER,
            spo2 INTEGER,
            bp_high INTEGER,
            bp_low INTEGER,
            medication_check BOOLEAN,
            medication_staff_id INTEGER,
            bath_check BOOLEAN,
            bath_start_time TIME,
            bath_start_staff_id INTEGER,
            bath_end_time TIME,
            bath_end_staff_id INTEGER,
            oral_care_check BOOLEAN,
            oral_care_staff_id INTEGER,
            weight REAL,
            health_notes TEXT,
            memo1 TEXT,
            memo2 TEXT,
            UNIQUE(user_id, log_date),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (medication_staff_id) REFERENCES staff (id),
            FOREIGN KEY (bath_start_staff_id) REFERENCES staff (id),
            FOREIGN KEY (bath_end_staff_id) REFERENCES staff (id),
            FOREIGN KEY (oral_care_staff_id) REFERENCES staff (id)
        )
    ''')

    # 排泄記録テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS excretions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER,
            excretion_time TIME,
            type TEXT,
            staff1_id INTEGER,
            staff2_id INTEGER,
            notes TEXT,
            FOREIGN KEY (log_id) REFERENCES daily_logs (id),
            FOREIGN KEY (staff1_id) REFERENCES staff (id),
            FOREIGN KEY (staff2_id) REFERENCES staff (id)
        )
    ''')

    # 欠席記録テーブル
    # ALTER TABLE文をCREATE TABLE文に統合
    c.execute('''
        CREATE TABLE IF NOT EXISTS absences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reception_date DATE,
            reception_staff_id INTEGER,
            contact_person TEXT,
            absence_start_date DATE,
            absence_end_date DATE,
            reason TEXT, -- Original reason field, can be repurposed or removed later
            support_content TEXT,
            reason_self_illness BOOLEAN DEFAULT 0,
            reason_seizure BOOLEAN DEFAULT 0,
            reason_fever BOOLEAN DEFAULT 0,
            reason_vomiting BOOLEAN DEFAULT 0,
            reason_cough BOOLEAN DEFAULT 0,
            reason_runny_nose BOOLEAN DEFAULT 0,
            reason_diarrhea BOOLEAN DEFAULT 0,
            reason_mood_bad BOOLEAN DEFAULT 0,
            reason_rash BOOLEAN DEFAULT 0,
            reason_self_illness_other_text TEXT,
            reason_other_than_self_illness BOOLEAN DEFAULT 0,
            reason_family_convenience BOOLEAN DEFAULT 0,
            reason_family_illness BOOLEAN DEFAULT 0,
            reason_family_illness_who TEXT,
            reason_regular_checkup BOOLEAN DEFAULT 0,
            reason_checkup_place TEXT,
            reason_other_text TEXT,
            support_checked_health_confirm BOOLEAN DEFAULT 0,
            support_content_health_confirm TEXT,
            support_checked_medical_recommend BOOLEAN DEFAULT 0,
            support_content_medical_recommend TEXT,
            support_checked_next_visit BOOLEAN DEFAULT 0,
            support_date_next_visit DATE,
            support_checked_other BOOLEAN DEFAULT 0,
            support_content_other TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (reception_staff_id) REFERENCES staff (id)
        )
    ''')

    conn.commit()
    conn.close()

# --- データベース操作関数 ---

def get_staff_list():
    """職員リストを取得する"""
    conn = get_db_connection()
    staff = conn.execute("""
                        SELECT employee_id, employee_name
                        FROM v_current_employee_information
                        WHERE department_code1 = 1 AND department_code2 = 16 AND department_code3 = 1 AND department_code4 = 3
                        AND retirement_date is null
                        ORDER BY employee_kana
                        """).fetchall()
    conn.close()
    return staff

def get_user_list():
    """利用者リストを取得する"""
    conn = get_db_connection()
    users = conn.execute('SELECT user_code, name FROM users WHERE is_active = 1 ORDER BY kana').fetchall()
    conn.close()
    return users

def get_user_by_id(user_id):
    """IDで利用者情報を取得する"""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_code = ?', (user_id,)).fetchone()
    conn.close()
    return user

def get_or_create_log_id(user_id, log_date):
    """指定日の日誌レコードを取得または作成し、そのIDを返す"""
    conn = get_db_connection()
    c = conn.cursor()
    # Ensure log_date is in 'YYYY-MM-DD' format for database query
    log_date_str = log_date.strftime('%Y-%m-%d') if isinstance(log_date, datetime) or isinstance(log_date, pd.Timestamp) else log_date

    c.execute('SELECT id FROM daily_logs WHERE user_id = ? AND log_date = ?', (user_id, log_date_str))
    log = c.fetchone()
    if log:
        log_id = log['id']
    else:
        c.execute('INSERT INTO daily_logs (user_id, log_date) VALUES (?, ?)', (user_id, log_date_str))
        conn.commit()
        log_id = c.lastrowid
    conn.close()
    return log_id


# --- UI表示関数 ---

def show_staff_page():
    """職員一覧・登録ページ"""
    st.header("職員一覧")
    staff_df = pd.read_sql("""
                        SELECT employee_name AS '氏名', department_name4 AS '所属'
                           FROM v_current_employee_information
                           WHERE department_code1 = 1 AND department_code2 = 16 AND department_code3 = 1 AND department_code4 = 3
                            AND retirement_date is null
                           ORDER BY employee_kana
                           """, get_db_connection())
    st.table(staff_df)

def show_user_info_page():
    """利用者情報登録ページ"""
    st.header("利用者情報登録")

    days_of_week = ["月", "火", "水", "木", "金", "土", "日"]

    # 既存利用者選択ロジック
    users = get_user_list()
    user_options = {"新規利用者登録": None}
    user_options.update({user['name']: user['user_code'] for user in users})

    selected_user_name = st.selectbox(
        "利用者を選択（新規登録または既存の利用者情報を編集）",
        options=list(user_options.keys()),
        index=0, # Default to "新規利用者登録"
        key="user_select_for_edit" # Added key
    )

    selected_user_id_for_edit = user_options[selected_user_name]
    current_user_data = None
    if selected_user_id_for_edit:
        conn = get_db_connection()
        current_user_data = conn.execute('SELECT * FROM users WHERE user_code = ?', (selected_user_id_for_edit,)).fetchone()
        conn.close()

    # フォームの初期値設定
    initial_user_code = current_user_data['user_code'] if current_user_data else 0
    initial_name = current_user_data['name'] if current_user_data else ""
    initial_kana = current_user_data['kana'] if current_user_data else ""
    initial_birthday = datetime.strptime(current_user_data['birthday'], '%Y-%m-%d').date() if current_user_data and current_user_data['birthday'] else None
    initial_gender = current_user_data['gender'] if current_user_data else None
    initial_patient_category = current_user_data['patient_category'] if current_user_data else None
    initial_is_active = current_user_data['is_active'] if current_user_data else True
    initial_start_date = datetime.strptime(current_user_data['start_date'], '%Y-%m-%d').date() if current_user_data and current_user_data['start_date'] else None
    initial_end_date = datetime.strptime(current_user_data['end_date'], '%Y-%m-%d').date() if current_user_data and current_user_data['end_date'] else None

    initial_use_days_list = current_user_data['use_days'].split(',') if current_user_data and current_user_data['use_days'] else []
    initial_medication_days_list = current_user_data['medication_days'].split(',') if current_user_data and current_user_data['medication_days'] else []
    initial_bath_days_list = current_user_data['bath_days'].split(',') if current_user_data and current_user_data['bath_days'] else []


    with st.form("user_info_form"):
        st.write("##### 利用者情報を入力してください")

        c1, c2 = st.columns(2)
        # 既存利用者編集時は利用者コードを読み取り専用にするか、非表示にする
        user_code = c1.number_input("利用者コード", step=1, format="%d", value=initial_user_code, disabled=(selected_user_id_for_edit is not None), key="user_code_input")
        name = c2.text_input("氏名 *", value=initial_name, key="user_name_input")
        kana = c1.text_input("フリガナ", value=initial_kana, key="user_kana_input")

        # 生年月日の入力可能範囲を制限なしにする (1900年1月1日から現在まで)
        birthday = c2.date_input(
            "生年月日",
            value=initial_birthday,
            min_value=datetime(1900, 1, 1).date(), # 1900年1月1日を最小値に設定
            max_value=datetime.now(JST).date(), # 現在の日付を最大値に設定
            key="user_birthday_input" # Added key
        )

        gender = c1.selectbox("性別", ["男", "女", "その他"], index=["男", "女", "その他"].index(initial_gender) if initial_gender else None, key="user_gender_select")
        patient_category = c2.selectbox("患者区分", ["たんぽぽ", "ゆり", "さくら", "すみれ", "なのはな", "療護", "外来"], index=["たんぽぽ", "ゆり", "さくら", "すみれ", "なのはな", "療護", "外来"].index(initial_patient_category) if initial_patient_category else None, key="user_patient_category_select")

        is_active = st.checkbox("在籍中", value=initial_is_active, key="user_is_active_checkbox")
        c1, c2 = st.columns(2)
        start_date = c1.date_input("利用開始日", value=initial_start_date, key="user_start_date_input")
        end_date = c2.date_input("退所年月日", value=initial_end_date, key="user_end_date_input")

        st.write("---")
        st.write("##### 利用曜日")
        use_days_cols = st.columns(7)
        use_days_checkbox_states = {}
        for i, day in enumerate(days_of_week):
            with use_days_cols[i]:
                use_days_checkbox_states[day] = st.checkbox(day, value=(day in initial_use_days_list), key=f"use_{day}_user_info")

        st.write("---")
        st.write("##### 内服曜日")
        medication_days_cols = st.columns(7)
        medication_days_selected = []
        for i, day in enumerate(days_of_week):
            with medication_days_cols[i]:
                # medication_days_selected にはチェックされた曜日のみを追加
                if st.checkbox(day, value=(day in initial_medication_days_list), key=f"medication_{day}_user_info"):
                    medication_days_selected.append(day)

        st.write("---")
        st.write("##### 入浴曜日")
        bath_days_cols = st.columns(7)
        bath_days_selected = []
        for i, day in enumerate(days_of_week):
            with bath_days_cols[i]:
                # bath_days_selected にはチェックされた曜日のみを追加
                if st.checkbox(day, value=(day in initial_bath_days_list), key=f"bath_{day}_user_info"):
                    bath_days_selected.append(day)

        c_submit1, c_submit2 = st.columns(2)

        # Unified submit button logic
        submit_label = "新規登録する" if selected_user_id_for_edit is None else "更新する"
        submitted = c_submit1.form_submit_button(submit_label)

        if submitted:
            if not name:
                st.error("氏名は必須です。")
            else:
                use_days_str = ",".join([day for day, selected in use_days_checkbox_states.items() if selected])
                # Check for errors in medication_days and bath_days
                errors = []
                selected_use_days = set([day for day, selected in use_days_checkbox_states.items() if selected])

                for day in medication_days_selected:
                    if day not in selected_use_days:
                        errors.append(f"内服曜日の'{day}'は利用曜日に含まれていません。")
                for day in bath_days_selected:
                    if day not in selected_use_days:
                        errors.append(f"入浴曜日の'{day}'は利用曜日に含まれていません。")

                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    medication_days_str = ",".join(medication_days_selected)
                    bath_days_str = ",".join(bath_days_selected)

                    conn = get_db_connection()
                    try:
                        if selected_user_id_for_edit is None: # 新規登録
                            conn.execute('''
                                INSERT INTO users (user_code, name, kana, birthday, gender, patient_category, is_active, start_date, end_date, use_days, medication_days, bath_days)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (user_code, name, kana, birthday, gender, patient_category, is_active, start_date, end_date, use_days_str, medication_days_str, bath_days_str))
                            st.success(f"{name}さんの情報を登録しました。")
                        else: # 更新
                            conn.execute('''
                                UPDATE users
                                SET name=?, kana=?, birthday=?, gender=?, patient_category=?, is_active=?, start_date=?, end_date=?, use_days=?, medication_days=?, bath_days=?
                                WHERE user_code=?
                            ''', (name, kana, birthday, gender, patient_category, is_active, start_date, end_date, use_days_str, medication_days_str, bath_days_str, selected_user_id_for_edit))
                            st.success(f"{name}さんの情報を更新しました。")
                        conn.commit()
                    except sqlite3.IntegrityError:
                        st.error("その利用者コードは既に登録されています。")
                    except Exception as e:
                        st.error(f"処理中にエラーが発生しました: {e}")
                    finally:
                        conn.close()


def show_log_list_page():
    """日誌一覧ページ"""
    st.header("日誌一覧")

    # Get current date in JST
    current_jst_date = datetime.now(JST).date()
    log_date = st.date_input("対象日を選択", current_jst_date, key="log_list_date_select")
    weekday_map = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
    selected_weekday = weekday_map[log_date.weekday()]
    st.info(f"{log_date.strftime('%Y年%m月%d日')} は **{selected_weekday}曜日** です。")

    conn = get_db_connection()
    # 利用曜日に基づいて利用者をフィルタリング
    query = f"SELECT user_code, name FROM users WHERE is_active = 1 AND use_days LIKE '%{selected_weekday}%' ORDER BY kana"
    today_users = conn.execute(query).fetchall()
    conn.close()

    st.write("---")

    if not today_users:
        st.warning("本日の利用予定者はいません。")
    else:
        st.write(f"##### {len(today_users)}名の利用予定者")

        # Create columns for display and buttons
        cols = st.columns([0.5, 0.2, 0.1, 0.1, 0.1])
        with cols[0]:
            st.write("**氏名**")
        with cols[1]:
            st.write("**日誌**")
        with cols[2]:
            st.write("**排泄**")
        with cols[3]:
            st.write("**欠席**")

        for user in today_users:
            user_id = user["user_code"] # Use user_code as ID for session state
            user_name = user["name"]

            # Use separate columns for each row's elements
            col_name, col_log, col_excretion, col_absence = st.columns([0.5, 0.2, 0.1, 0.1])

            with col_name:
                st.write(user_name)

            # Daily Log button
            if col_log.button("✏️", key=f"log_button_{user_id}"): # Added key suffix
                st.session_state.page = "日誌入力"
                st.session_state.selected_user_id_for_log = user_id
                st.session_state.selected_log_date = log_date
                st.rerun()

            # Excretion button
            if col_excretion.button("🚽", key=f"excretion_button_{user_id}"): # Added key suffix
                st.session_state.page = "排泄入力"
                st.session_state.selected_user_id_for_excretion = user_id
                st.session_state.selected_log_date = log_date
                st.rerun()

            # Absence button
            if col_absence.button("❌", key=f"absence_button_{user_id}"): # Added key suffix
                st.session_state.page = "欠席入力"
                st.session_state.selected_user_id_for_absence = user_id
                st.session_state.selected_log_date = log_date
                st.rerun()

    st.write("---")
    with st.expander("臨時利用者の追加"):
        users = get_user_list()
        user_options = {user['user_code']: user['name'] for user in users}

        selected_user_id_temp = st.selectbox(
            "臨時で利用する利用者を選択",
            options=list(user_options.keys()),
            format_func=lambda x: user_options[x],
            index=None,
            key="temp_user_select"
        )
        if st.button("臨時利用を追加", key="add_temp_user_btn"):
            if selected_user_id_temp:
                # Ensure a log entry is created for the temporary user
                get_or_create_log_id(selected_user_id_temp, log_date)
                st.success(f"{user_options[selected_user_id_temp]}さんを臨時利用者として追加しました。（日誌エントリを作成済み）")


def show_log_input_page():
    """日誌入力ページ"""
    st.header("日誌入力")

    users = get_user_list()
    user_options = {user['user_code']: user['name'] for user in users}

    staff = get_staff_list()
    staff_options = {s['employee_id']: s['employee_name'] for s in staff}

    # Get current date in JST
    current_jst_date = datetime.now(JST).date()

    # Pre-select user and date if coming from log list
    initial_user_id = st.session_state.get('selected_user_id_for_log', None)
    initial_log_date = st.session_state.get('selected_log_date', current_jst_date)

    c1, c2 = st.columns(2)

    # Safely determine the index for the user selectbox
    selected_user_index = None
    if initial_user_id is not None and initial_user_id in user_options:
        try:
            selected_user_index = list(user_options.keys()).index(initial_user_id)
        except ValueError:
            selected_user_index = None # Fallback if not found for some reason

    selected_user_id = c1.selectbox(
        "利用者を選択",
        options=list(user_options.keys()),
        format_func=lambda x: user_options.get(x, "選択してください"),
        index=selected_user_index,
        key="log_input_user_select" # Added key
    )
    log_date = c2.date_input("利用日", initial_log_date, key="log_input_date_select") # Added key

    if selected_user_id and log_date:
        st.subheader(f"{user_options[selected_user_id]}さんの日誌 ({log_date.strftime('%Y/%m/%d')})")

        log_id = get_or_create_log_id(selected_user_id, log_date)

        # 既存データを読み込む
        conn = get_db_connection()
        log_data = conn.execute('SELECT * FROM daily_logs WHERE id = ?', (log_id,)).fetchone()

        # 利用者情報を取得して利用曜日を確認
        user_info = get_user_by_id(selected_user_id)
        user_use_days_list = user_info['use_days'].split(',') if user_info and user_info['use_days'] else []
        weekday_map_full = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
        selected_weekday = weekday_map_full[log_date.weekday()]

        # 臨時利用者（利用曜日ではない日に利用）の判定
        is_temporary_user_for_log_date = selected_weekday not in user_use_days_list

        conn.close()

        with st.form("log_input_form"):
            # Populate form with existing data, handling None values
            is_absent = log_data['is_absent'] if log_data and log_data['is_absent'] is not None else False
            st.checkbox("欠席", value=is_absent, key="log_is_absent_checkbox") # Added key

            st.write("---")
            st.write("##### バイタル")
            c1, c2, c3, c4, c5 = st.columns(5)
            temperature = c1.number_input("体温", min_value=30.0, max_value=45.0, step=0.1, format="%.1f",
                                value=log_data['temperature'] if log_data and log_data['temperature'] is not None else 36.5, key="temperature_input")
            pulse = c2.number_input("脈", min_value=0, max_value=200, step=1,
                                value=log_data['pulse'] if log_data and log_data['pulse'] is not None else 70, key="pulse_input")
            spo2 = c3.number_input("SPO2", min_value=0, max_value=100, step=1,
                                value=log_data['spo2'] if log_data and log_data['spo2'] is not None else 98, key="spo2_input")
            bp_high = c4.number_input("最高血圧", min_value=0, max_value=300, step=1,
                                value=log_data['bp_high'] if log_data and log_data['bp_high'] is not None else 120, key="bp_high_input")
            bp_low = c5.number_input("最低血圧", min_value=0, max_value=200, step=1,
                                value=log_data['bp_low'] if log_data and log_data['bp_low'] is not None else 80, key="bp_low_input")
            weight = c1.number_input("体重", min_value=0.0, max_value=200.0, step=0.1, format="%.1f",
                                value=log_data['weight'] if log_data and log_data['weight'] is not None else 50.0, key="weight_input")

            st.write("---")
            st.write("##### 内服・口腔ケア")
            c1, c2 = st.columns(2)
            medication_check = c1.checkbox("内服実施", value=log_data['medication_check'] if log_data and log_data['medication_check'] is not None else False, key="medication_check_checkbox") # Added key

            medication_staff_index = None
            if log_data and log_data['medication_staff_id'] is not None and log_data['medication_staff_id'] in staff_options:
                try:
                    medication_staff_index = list(staff_options.keys()).index(log_data['medication_staff_id'])
                except ValueError:
                    pass

            # 内服実施が未チェックの場合、または臨時利用者ではない場合のみ disabled
            # disable_med_staff_input = (not medication_check) and (not is_temporary_user_for_log_date) # Original line
            medication_staff_id = c2.selectbox(
                "内服実施職員",
                options=list(staff_options.keys()),
                format_func=lambda x: staff_options.get(x),
                index=medication_staff_index,
                # disabled=disable_med_staff_input, # MODIFICATION: Removed disabled attribute
                key="medication_staff_select" # Added key
            )

            c1, c2 = st.columns(2)
            oral_care_check = c1.checkbox("口腔ケア実施", value=log_data['oral_care_check'] if log_data and log_data['oral_care_check'] is not None else False, key="oral_care_check_checkbox") # Added key

            oral_care_staff_index = None
            if log_data and log_data['oral_care_staff_id'] is not None and log_data['oral_care_staff_id'] in staff_options:
                try:
                    oral_care_staff_index = list(staff_options.keys()).index(log_data['oral_care_staff_id'])
                except ValueError:
                    pass

            # 口腔ケア実施が未チェックの場合、または臨時利用者ではない場合のみ disabled
            # disable_oral_staff_input = (not oral_care_check) and (not is_temporary_user_for_log_date) # Original line
            oral_care_staff_id = c2.selectbox(
                "口腔ケア実施職員",
                options=list(staff_options.keys()),
                format_func=lambda x: staff_options.get(x),
                index=oral_care_staff_index,
                # disabled=disable_oral_staff_input, # MODIFICATION: Removed disabled attribute
                key="oral_care_staff_select" # Added key
            )

            st.write("---")
            st.write("##### 入浴")
            bath_check = st.checkbox("入浴実施", value=log_data['bath_check'] if log_data and log_data['bath_check'] is not None else False, key="bath_check_checkbox") # Added key
            c1, c2, c3, c4 = st.columns(4)

            # Convert stored time string to datetime.time object for time_input
            bath_start_time_val = None
            if log_data and log_data['bath_start_time']:
                try:
                    bath_start_time_val = datetime.strptime(log_data['bath_start_time'], '%H:%M:%S').time()
                except ValueError:
                    bath_start_time_val = time(9, 0) # Default if parsing fails
            else:
                bath_start_time_val = time(9, 0) # Default if None from DB

            bath_end_time_val = None
            if log_data and log_data['bath_end_time']:
                try:
                    bath_end_time_val = datetime.strptime(log_data['bath_end_time'], '%H:%M:%S').time()
                except ValueError:
                    bath_end_time_val = time(10, 0) # Default if parsing fails
            else:
                bath_end_time_val = time(10, 0) # Default if None from DB

            # 入浴実施が未チェックの場合、または臨時利用者ではない場合のみ disabled
            # disable_bath_input = (not bath_check) and (not is_temporary_user_for_log_date) # Original line

            bath_start_time = c1.time_input("入浴開始時間", value=bath_start_time_val, # MODIFICATION: Removed disabled attribute
                                            key="bath_start_time_input") # Added key

            bath_start_staff_index = None
            if log_data and log_data['bath_start_staff_id'] is not None and log_data['bath_start_staff_id'] in staff_options:
                try:
                    bath_start_staff_index = list(staff_options.keys()).index(log_data['bath_start_staff_id'])
                except ValueError:
                    pass
            bath_start_staff_id = c2.selectbox(
                "開始記録職員",
                options=list(staff_options.keys()),
                format_func=lambda x: staff_options.get(x),
                index=bath_start_staff_index,
                key="bath_start_staff_select", # Renamed key for consistency
                # disabled=disable_bath_input # MODIFICATION: Removed disabled attribute
            )

            bath_end_time = c3.time_input("入浴終了時間", value=bath_end_time_val, # MODIFICATION: Removed disabled attribute
                                          key="bath_end_time_input") # Added key

            bath_end_staff_index = None
            if log_data and log_data['bath_end_staff_id'] is not None and log_data['bath_end_staff_id'] in staff_options:
                try:
                    bath_end_staff_index = list(staff_options.keys()).index(log_data['bath_end_staff_id'])
                except ValueError:
                    pass
            bath_end_staff_id = c4.selectbox(
                "終了記録職員",
                options=list(staff_options.keys()),
                format_func=lambda x: staff_options.get(x),
                index=bath_end_staff_index,
                key="bath_end_staff_select", # Renamed key for consistency
                # disabled=disable_bath_input # MODIFICATION: Removed disabled attribute
            )

            st.write("---")
            health_notes = st.text_area("特記（体調面）", value=log_data['health_notes'] if log_data and log_data['health_notes'] is not None else "", key="health_notes_input") # Added key
            memo1 = st.text_area("その他１", value=log_data['memo1'] if log_data and log_data['memo1'] is not None else "", key="memo1_input") # Added key
            memo2 = st.text_area("その他２", value=log_data['memo2'] if log_data and log_data['memo2'] is not None else "", key="memo2_input") # Added key

            # Removed 'key' argument from st.form_submit_button
            submitted = st.form_submit_button("日誌を保存")
            if submitted:
                conn = get_db_connection()
                # Use current values from Streamlit widgets, not log_data, as they reflect user input
                conn.execute('''
                    UPDATE daily_logs
                    SET is_absent=?, temperature=?, pulse=?, spo2=?, bp_high=?, bp_low=?,
                        medication_check=?, medication_staff_id=?, bath_check=?, bath_start_time=?,
                        bath_start_staff_id=?, bath_end_time=?, bath_end_staff_id=?, oral_care_check=?,
                        oral_care_staff_id=?, weight=?, health_notes=?, memo1=?, memo2=?
                    WHERE id = ?
                ''', (is_absent, temperature, pulse, spo2, bp_high, bp_low,
                      medication_check, medication_staff_id,
                      bath_check, bath_start_time.strftime('%H:%M:%S') if bath_start_time else None, # Store time as string
                      bath_start_staff_id, bath_end_time.strftime('%H:%M:%S') if bath_end_time else None, # Store time as string
                      bath_end_staff_id, oral_care_check,
                      oral_care_staff_id, weight, health_notes, memo1, memo2, log_id))
                conn.commit()
                conn.close()
                st.success("日誌を保存しました。")
    else:
        st.info("利用者と利用日を選択してください。")

def show_excretion_page():
    """排泄入力ページ"""
    st.header("排泄入力")

    users = get_user_list()
    user_options = {user['user_code']: user['name'] for user in users}

    staff = get_staff_list()
    staff_options = {s['employee_id']: s['employee_name'] for s in staff}
    # Ensure None is a key if it's a possible selection, and handle its index
    if None not in staff_options:
        staff_options[None] = "なし"

    # Get current date and time in JST
    current_jst_date = datetime.now(JST).date()
    current_jst_time = datetime.now(JST).time()

    # Pre-select user and date if coming from log list
    initial_user_id = st.session_state.get('selected_user_id_for_excretion', None)
    initial_log_date = st.session_state.get('selected_log_date', current_jst_date)

    c1, c2 = st.columns(2)

    # Safely determine the index for the user selectbox
    selected_user_index = None
    if initial_user_id is not None and initial_user_id in user_options:
        try:
            selected_user_index = list(user_options.keys()).index(initial_user_id)
        except ValueError:
            pass # index remains None

    selected_user_id = c1.selectbox(
        "利用者を選択",
        options=list(user_options.keys()),
        format_func=lambda x: user_options.get(x),
        index=selected_user_index,
        key="excretion_user_select" # Added key
    )
    log_date = c2.date_input("利用日", initial_log_date, key="excretion_date_input") # Added key

    if selected_user_id and log_date:
        log_id = get_or_create_log_id(selected_user_id, log_date)

        with st.form("excretion_form"):
            st.write(f"##### {user_options[selected_user_id]}さんの排泄記録")

            c1, c2 = st.columns(2)
            excretion_time = c1.time_input("排泄時間", value=current_jst_time, key="excretion_time_input") # Added key
            excretion_type = c2.selectbox("分類", ["尿", "便"], index=None, key="excretion_type_select") # Added key

            c1, c2 = st.columns(2)
            # Safely determine index for staff selectboxes
            staff1_index = None
            # No initial value from DB for new excretion record, so index remains None

            staff1_id = c1.selectbox("排泄介助職員1", options=list(staff_options.keys()), format_func=lambda x: staff_options.get(x), index=staff1_index, key="excretion_staff1_select") # Added key

            staff2_index = None
            # If the option for 'None' exists and we want it as default, find its index.
            if None in staff_options:
                 try:
                     staff2_index = list(staff_options.keys()).index(None)
                 except ValueError:
                     pass # Should not happen if None is in staff_options

            staff2_id = c2.selectbox("排泄介助職員2", options=list(staff_options.keys()), format_func=lambda x: staff_options.get(x), index=staff2_index, key="excretion_staff2_select") # Added key

            notes = st.text_area("特記事項（体調面）", key="excretion_notes_input") # Added key

            # Removed 'key' argument from st.form_submit_button
            submitted = st.form_submit_button("記録を追加")

            if submitted:
                if excretion_type and staff1_id:
                    conn = get_db_connection()
                    conn.execute(
                        'INSERT INTO excretions (log_id, excretion_time, type, staff1_id, staff2_id, notes) VALUES (?, ?, ?, ?, ?, ?)',
                        (log_id, excretion_time.strftime('%H:%M:%S'), excretion_type, staff1_id, staff2_id, notes)
                    )
                    conn.commit()
                    conn.close()
                    st.success("排泄記録を追加しました。")
                    st.rerun() # Rerun to refresh the list of records
                else:
                    st.error("分類と介助職員1は必須です。")

        # 記録一覧の表示
        st.write("---")
        st.write("##### 本日の記録一覧")
        conn = get_db_connection()
        records_df = pd.read_sql_query(f'''
            SELECT
                e.excretion_time AS '時間',
                e.type AS '分類',
                s1.name AS '介助職員1',
                s2.name AS '介助職員2',
                e.notes AS '特記事項'
            FROM excretions e
            LEFT JOIN staff s1 ON e.staff1_id = s1.id
            LEFT JOIN staff s2 ON e.staff2_id = s2.id
            WHERE e.log_id = {log_id}
            ORDER BY e.excretion_time
        ''', conn)
        conn.close()
        st.dataframe(records_df, use_container_width=True)

def show_absence_page():
    """欠席入力ページ"""
    st.header("欠席入力")

    users = get_user_list()
    user_options = {user['user_code']: user['name'] for user in users}
    # Add a "選択してください" (Please select) option for initial state
    # This list will contain dicts like {'id': None, 'name': '選択してください'} and one {'id': None, 'name': '選択してください'}
    user_options_list_for_select = [{'user_code': None, 'name': '選択してください'}] + list(users)


    staff = get_staff_list()
    staff_options = {s['employee_id']: s['employee_name'] for s in staff}
    # Ensure None is a key if it's a possible selection, and handle its index
    if None not in staff_options:
        staff_options[None] = "なし"

    # Get current date in JST
    current_jst_date = datetime.now(JST).date()

    # Pre-select user if coming from log list
    initial_user_id = st.session_state.get('selected_user_id_for_absence', None)
    initial_log_date = st.session_state.get('selected_log_date', current_jst_date)

    # 1. 欠席者を選択 (This remains outside the form for initial selection)
    # Find the index of the initial_user_id or default to the "選択してください" option (index 0)
    selected_user_index = 0 # Default to "選択してください"
    if initial_user_id is not None:
        try:
            # Find the actual index of the initial_user_id in the options list (including the placeholder)
            for i, user_dict in enumerate(user_options_list_for_select):
                if user_dict['user_code'] == initial_user_id:
                    selected_user_index = i
                    break
        except ValueError:
            pass # Keep default index 0 if not found

    selected_user_id = st.selectbox(
        "欠席者を選択",
        options=[u['user_code'] for u in user_options_list_for_select], # Use IDs as options
        format_func=lambda x: next((u['name'] for u in user_options_list_for_select if u['user_code'] == x), "選択してください"), # Use format_func for display
        index=selected_user_index,
        key="absence_user_select"
    )

    # Determine if the form should be disabled
    # Form is disabled if no user is selected (selected_user_id is None)
    form_disabled = selected_user_id is None

    # Load existing data only if a user is selected
    existing_absence_data = None
    if selected_user_id is not None:
        conn = get_db_connection()
        # Ensure log_date is correctly formatted for the query
        log_date_str = initial_log_date.strftime('%Y-%m-%d')
        existing_absence_data = conn.execute(
            'SELECT * FROM absences WHERE user_id = ? AND absence_start_date <= ? AND absence_end_date >= ?',
            (selected_user_id, log_date_str, log_date_str)
        ).fetchone()
        conn.close()

    # Initialize form fields with existing data or defaults
    initial_reception_date = datetime.strptime(existing_absence_data['reception_date'], '%Y-%m-%d').date() if existing_absence_data and existing_absence_data['reception_date'] else current_jst_date
    initial_reception_staff_id = existing_absence_data['reception_staff_id'] if existing_absence_data and existing_absence_data['reception_staff_id'] else None
    initial_contact_person = existing_absence_data['contact_person'] if existing_absence_data and existing_absence_data['contact_person'] is not None else ""
    initial_absence_start_date = datetime.strptime(existing_absence_data['absence_start_date'], '%Y-%m-%d').date() if existing_absence_data and existing_absence_data['absence_start_date'] else current_jst_date
    initial_absence_end_date = datetime.strptime(existing_absence_data['absence_end_date'], '%Y-%m-%d').date() if existing_absence_data and existing_absence_data['end_date'] else current_jst_date
    initial_support_content = existing_absence_data['support_content'] if existing_absence_data and existing_absence_data['support_content'] is not None else "" # Ensure empty string not None for text_area

    # Detailed reason initial values
    initial_reason_self_illness = existing_absence_data['reason_self_illness'] if existing_absence_data and existing_absence_data['reason_self_illness'] is not None else False
    initial_reason_seizure = existing_absence_data['reason_seizure'] if existing_absence_data and existing_absence_data['reason_seizure'] is not None else False
    initial_reason_fever = existing_absence_data['reason_fever'] if existing_absence_data and existing_absence_data['reason_fever'] is not None else False
    initial_reason_vomiting = existing_absence_data['reason_vomiting'] if existing_absence_data and existing_absence_data['reason_vomiting'] is not None else False
    initial_reason_cough = existing_absence_data['reason_cough'] if existing_absence_data and existing_absence_data['reason_cough'] is not None else False
    initial_reason_runny_nose = existing_absence_data['reason_runny_nose'] if existing_absence_data and existing_absence_data['reason_runny_nose'] is not None else False
    initial_reason_diarrhea = existing_absence_data['reason_diarrhea'] if existing_absence_data and existing_absence_data['reason_diarrhea'] is not None else False
    initial_reason_mood_bad = existing_absence_data['reason_mood_bad'] if existing_absence_data and existing_absence_data['reason_mood_bad'] is not None else False
    initial_reason_rash = existing_absence_data['reason_rash'] if existing_absence_data and existing_absence_data['reason_rash'] is not None else False
    initial_reason_self_illness_other_text = existing_absence_data['reason_self_illness_other_text'] if existing_absence_data and existing_absence_data['reason_self_illness_other_text'] is not None else ""
    initial_reason_other_than_self_illness = existing_absence_data['reason_other_than_self_illness'] if existing_absence_data and existing_absence_data['reason_other_than_self_illness'] is not None else False
    initial_reason_family_convenience = existing_absence_data['reason_family_convenience'] if existing_absence_data and existing_absence_data['reason_family_convenience'] is not None else False
    initial_reason_family_illness = existing_absence_data['reason_family_illness'] if existing_absence_data and existing_absence_data['reason_family_illness'] is not None else False
    initial_reason_family_illness_who = existing_absence_data['reason_family_illness_who'] if existing_absence_data and existing_absence_data['reason_family_illness_who'] is not None else ""
    initial_reason_regular_checkup = existing_absence_data['reason_regular_checkup'] if existing_absence_data and existing_absence_data['reason_regular_checkup'] is not None else False
    initial_reason_checkup_place = existing_absence_data['reason_checkup_place'] if existing_absence_data and existing_absence_data['reason_checkup_place'] is not None else ""
    initial_reason_other_text = existing_absence_data['reason_other_text'] if existing_absence_data and existing_absence_data['reason_other_text'] is not None else ""

    # New initial values for detailed support content
    initial_support_checked_health_confirm = existing_absence_data['support_checked_health_confirm'] if existing_absence_data and existing_absence_data['support_checked_health_confirm'] is not None else False
    initial_support_content_health_confirm = existing_absence_data['support_content_health_confirm'] if existing_absence_data and existing_absence_data['support_content_health_confirm'] is not None else ""
    initial_support_checked_medical_recommend = existing_absence_data['support_checked_medical_recommend'] if existing_absence_data and existing_absence_data['support_checked_medical_recommend'] is not None else False
    # Corrected variable name from initial_content_medical_recommend
    initial_support_content_medical_recommend = existing_absence_data['support_content_medical_recommend'] if existing_absence_data and existing_absence_data['support_content_medical_recommend'] is not None else ""
    initial_support_checked_next_visit = existing_absence_data['support_checked_next_visit'] if existing_absence_data and existing_absence_data['support_checked_next_visit'] is not None else False
    initial_support_date_next_visit = datetime.strptime(existing_absence_data['support_date_next_visit'], '%Y-%m-%d').date() if existing_absence_data and existing_absence_data['support_date_next_visit'] else None
    initial_support_checked_other = existing_absence_data['support_checked_other'] if existing_absence_data and existing_absence_data['support_checked_other'] is not None else False
    initial_support_content_other = existing_absence_data['support_content_other'] if existing_absence_data and existing_absence_data['support_content_other'] is not None else ""


    # Display a subheader that changes based on user selection
    if selected_user_id:
        st.write(f"##### {next((u['name'] for u in user_options_list_for_select if u['user_code'] == selected_user_id), '利用者情報')}さんの欠席情報")
    else:
        st.info("欠席者を選択してください。") # Inform user to select a user first

    # Wrap the form elements within st.form
    with st.form(key="absence_entry_form"):
        # 2. 受付職員, 3. 受付日
        c1, c2 = st.columns(2)
        reception_staff_index = None
        if initial_reception_staff_id is not None and initial_reception_staff_id in staff_options:
            try:
                reception_staff_index = list(staff_options.keys()).index(initial_reception_staff_id)
            except ValueError:
                pass
        reception_staff_id = c1.selectbox("受付職員", options=list(staff_options.keys()), format_func=lambda x: staff_options.get(x), index=reception_staff_index, key="reception_staff_select", disabled=form_disabled)
        reception_date = c2.date_input("受付日", value=initial_reception_date, key="reception_date_input", disabled=form_disabled)

        # 4. 欠席の連絡者
        contact_person = st.text_input("欠席の連絡者", value=initial_contact_person, key="contact_person_input", disabled=form_disabled)

        # 5. 欠席期間（開始）, 6. 欠席期間（終了）
        c1, c2 = st.columns(2)
        absence_start_date = c1.date_input("欠席期間（開始）", value=initial_absence_start_date, key="absence_start_date_input", disabled=form_disabled)
        absence_end_date = c2.date_input("欠席期間（終了）", value=initial_absence_end_date, key="absence_end_date_input", disabled=form_disabled)

        st.write("---")
        st.write("##### 欠席理由")

        # 7. 本人の体調不良 (チェックボックス)
        reason_self_illness = st.checkbox("本人の体調不良", value=initial_reason_self_illness, key="reason_self_illness_checkbox", disabled=form_disabled)

        # 8. 発作, 9. 咳, 10. 発熱, 11. 鼻水, 12. 嘔吐, 13. 下痢, 14. 機嫌不良, 15. 発疹
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        with col_b1:
            reason_seizure = st.checkbox("発作", value=initial_reason_seizure, key="reason_seizure_checkbox", disabled=form_disabled)
            reason_cough = st.checkbox("咳", value=initial_reason_cough, key="reason_cough_checkbox", disabled=form_disabled)
        with col_b2:
            reason_fever = st.checkbox("発熱", value=initial_reason_fever, key="reason_fever_checkbox", disabled=form_disabled)
            reason_runny_nose = st.checkbox("鼻水", value=initial_reason_runny_nose, key="reason_runny_nose_checkbox", disabled=form_disabled)
        with col_b3:
            reason_vomiting = st.checkbox("嘔吐", value=initial_reason_vomiting, key="reason_vomiting_checkbox", disabled=form_disabled)
            reason_diarrhea = st.checkbox("下痢", value=initial_reason_diarrhea, key="reason_diarrhea_checkbox", disabled=form_disabled)
        with col_b4:
            reason_mood_bad = st.checkbox("機嫌不良", value=initial_reason_mood_bad, key="reason_mood_bad_checkbox", disabled=form_disabled)
            reason_rash = st.checkbox("発疹", value=initial_reason_rash, key="reason_rash_checkbox", disabled=form_disabled)
        # 16. その他（本人の体調不良）
        reason_self_illness_other_text = st.text_area("その他（本人の体調不良）", value=initial_reason_self_illness_other_text, key="reason_self_illness_other_text_input", disabled=form_disabled)


        # 17. 本人の体調不良以外 (チェックボックス)
        reason_other_than_self_illness = st.checkbox("本人の体調不良以外", value=initial_reason_other_than_self_illness, key="reason_other_than_self_illness_checkbox", disabled=form_disabled)

        col_c1, col_c2, col_c3 = st.columns(3)
        # 18. 家族の都合 (チェックボックス)
        with col_c1:
            reason_family_convenience = st.checkbox("家族の都合", value=initial_reason_family_convenience, key="reason_family_convenience_checkbox", disabled=form_disabled)
        # 19. 家族の体調不良 (チェックボックス)
        with col_c2:
            reason_family_illness = st.checkbox("家族の体調不良", value=initial_reason_family_illness, key="reason_family_illness_checkbox", disabled=form_disabled) # 修正
        # 20. 誰が？ (1行入力)
        with col_c3:
            reason_family_illness_who = st.text_input("誰が？", value=initial_reason_family_illness_who, key="reason_family_illness_who_input", disabled=form_disabled) # 修正

        # 21. 定期受診 (チェックボックス)
        reason_regular_checkup = st.checkbox("定期受診", value=initial_reason_regular_checkup, key="reason_regular_checkup_checkbox", disabled=form_disabled)
        # 22. 受診先 (1行入力)
        reason_checkup_place = st.text_input("受診先", value=initial_reason_checkup_place, key="reason_checkup_place_input", disabled=form_disabled)

        # 23. その他（本人の体調不良以外）
        reason_other_text = st.text_area("その他（本人の体調不良以外）", value=initial_reason_other_text, key="reason_other_text_input", disabled=form_disabled)

        st.write("---")
        st.write("##### 援助内容")

        # 24. 体調を確認した (チェックボックス)
        support_checked_health_confirm = st.checkbox("体調を確認した", value=initial_support_checked_health_confirm, key="support_checked_health_confirm_checkbox", disabled=form_disabled)
        # 25. 内容（体調確認）
        support_content_health_confirm = st.text_area("内容（体調確認）", value=initial_support_content_health_confirm, key="support_content_health_confirm_input", disabled=form_disabled)

        # 26. 医療機関の受診を勧めた (チェックボックス)
        support_checked_medical_recommend = st.checkbox("医療機関の受診を勧めた", value=initial_support_checked_medical_recommend, key="support_checked_medical_recommend_checkbox", disabled=form_disabled)
        # 27. 内容（医療機関の受診）
        support_content_medical_recommend = st.text_input("内容（医療機関の受診）", value=initial_support_content_medical_recommend, key="support_content_medical_recommend_input", disabled=form_disabled)

        # 28. 次回利用日を確認した (チェックボックス)
        support_checked_next_visit = st.checkbox("次回利用日を確認した", value=initial_support_checked_next_visit, key="support_checked_next_visit_checkbox", disabled=form_disabled)
        # 29. 日付（次回利用日）
        default_next_visit_date = initial_support_date_next_visit if initial_support_date_next_visit else current_jst_date
        support_date_next_visit = st.date_input("日付（次回利用日）", value=default_next_visit_date, key="support_date_next_visit_input", disabled=form_disabled)

        # 30. その他（援助内容） (チェックボックス)
        support_checked_other = st.checkbox("その他（援助内容）", value=initial_support_checked_other, key="support_checked_other_checkbox", disabled=form_disabled)
        # 31. 内容（その他援助）
        support_content_other = st.text_area("内容（その他援助）", value=initial_support_content_other, key="support_content_other_input", disabled=form_disabled)

        # 32. 援助内容（詳細を記入 - 旧フィールド）
        support_content = st.text_area("援助内容（詳細を記入 - 旧フィールド）", value=initial_support_content, help="例：体調確認、医療機関の受診を勧めた。", key="support_content_old_input", disabled=form_disabled)


        # 33. 欠席情報を登録/更新 (ボタン)
        # Removed 'key' argument from st.form_submit_button
        submitted = st.form_submit_button("欠席情報を登録/更新", disabled=form_disabled)
        if submitted:
            if selected_user_id is None:
                st.error("欠席者を選択してください。")
            else:
                conn = get_db_connection()

                # Convert datetime.date objects to string for database storage
                support_date_next_visit_str = None
                if support_checked_next_visit and support_date_next_visit:
                    support_date_next_visit_str = support_date_next_visit.strftime('%Y-%m-%d')
                elif not support_checked_next_visit: # If checkbox is off, ensure no date is saved
                    support_date_next_visit_str = None

                # Check if an existing record needs to be updated or a new one inserted
                if existing_absence_data:
                    conn.execute('''
                        UPDATE absences
                        SET reception_date=?, reception_staff_id=?, contact_person=?,
                            absence_start_date=?, absence_end_date=?,
                            reason_self_illness=?, reason_seizure=?, reason_fever=?, reason_vomiting=?,
                            reason_cough=?, reason_runny_nose=?, reason_diarrhea=?, reason_mood_bad=?,
                            reason_rash=?, reason_self_illness_other_text=?,
                            reason_other_than_self_illness=?, reason_family_convenience=?,
                            reason_family_illness=?, reason_family_illness_who=?,
                            reason_regular_checkup=?, reason_checkup_place=?,
                            reason_other_text=?, support_content=?, -- Original support content
                            support_checked_health_confirm=?, support_content_health_confirm=?,
                            support_checked_medical_recommend=?, support_content_medical_recommend=?,
                            support_checked_next_visit=?, support_date_next_visit=?,
                            support_checked_other=?, support_content_other=?
                        WHERE id = ?
                    ''', (reception_date, reception_staff_id, contact_person,
                          absence_start_date, absence_end_date,
                          reason_self_illness, reason_seizure, reason_fever, reason_vomiting,
                          reason_cough, reason_runny_nose, reason_diarrhea, reason_mood_bad,
                          reason_rash, reason_self_illness_other_text,
                          reason_other_than_self_illness, reason_family_convenience,
                          reason_family_illness, reason_family_illness_who, # Use direct widget value
                          reason_regular_checkup, reason_checkup_place, # Use direct widget value
                          reason_other_text, support_content, # Original support content
                          support_checked_health_confirm, support_content_health_confirm, # Use direct widget value
                          support_checked_medical_recommend, support_content_medical_recommend, # Use direct widget value
                          support_checked_next_visit, support_date_next_visit_str, # Store date as string
                          support_checked_other, support_content_other, # Use direct widget value
                          existing_absence_data['id']))
                    st.success("欠席情報を更新しました。")
                else:
                    # If no user is selected, or no existing data, but submitted:
                    # Insert logic should be here if it's a new entry (i.e., existing_absence_data is None)
                    # But if selected_user_id is None, this block won't be reached as submit button is disabled.
                    # So this 'else' implies selected_user_id IS NOT None but existing_absence_data IS None (new record for selected user).
                    conn.execute('''
                        INSERT INTO absences (user_id, reception_date, reception_staff_id, contact_person,
                                            absence_start_date, absence_end_date,
                                            reason_self_illness, reason_seizure, reason_fever, reason_vomiting,
                                            reason_cough, reason_runny_nose, reason_diarrhea, reason_mood_bad,
                                            reason_rash, reason_self_illness_other_text,
                                            reason_other_than_self_illness, reason_family_convenience,
                                            reason_family_illness, reason_family_illness_who,
                                            reason_regular_checkup, reason_checkup_place,
                                            reason_other_text, support_content, -- Original support content
                                            support_checked_health_confirm, support_content_health_confirm,
                                            support_checked_medical_recommend, support_content_medical_recommend,
                                            support_checked_next_visit, support_date_next_visit,
                                            support_checked_other, support_content_other)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (selected_user_id, reception_date, reception_staff_id, contact_person,
                          absence_start_date, absence_end_date,
                          reason_self_illness, reason_seizure, reason_fever, reason_vomiting,
                          reason_cough, reason_runny_nose, reason_diarrhea, reason_mood_bad,
                          reason_rash, reason_self_illness_other_text,
                          reason_other_than_self_illness, reason_family_convenience,
                          reason_family_illness, reason_family_illness_who, # Use direct widget value
                          reason_regular_checkup, reason_checkup_place, # Use direct widget value
                          reason_other_text, support_content, # Original support content
                          support_checked_health_confirm, support_content_health_confirm, # Use direct widget value
                          support_checked_medical_recommend, support_content_medical_recommend, # Use direct widget value
                          support_checked_next_visit, support_date_next_visit_str, # Store date as string
                          support_checked_other, support_content_other)) # Use direct widget value
                conn.commit()
                conn.close()
                st.rerun() # Refresh to show updated data if any, or clear form for new entry.


# --- メインのアプリケーション実行部分 ---
def main():
    """メイン関数"""
    create_tables() # データベースとテーブルの存在確認・作成

    st.set_page_config(page_title="通所日誌アプリ", layout="wide")
    st.sidebar.title("メニュー")

    # セッション状態でページを管理
    if 'page' not in st.session_state:
        st.session_state.page = "日誌一覧"

    menu_options = ["日誌一覧", "日誌入力", "排泄入力", "欠席入力", "利用者情報登録", "職員一覧"]

    # サイドバーのラジオボタンでページを切り替える
    selected_option = st.sidebar.radio(
        "ページを選択してください",
        menu_options,
        index=menu_options.index(st.session_state.page), # 現在のページをデフォルトで選択
        key="main_menu_radio"
    )

    # ラジオボタンの選択が変更された場合
    if selected_option != st.session_state.page:
        st.session_state.page = selected_option
        # Clear specific session state variables when navigating from sidebar
        # to prevent pre-filling forms unexpectedly when not coming from list page
        if selected_option != "日誌入力":
            if 'selected_user_id_for_log' in st.session_state:
                del st.session_state.selected_user_id_for_log
        if selected_option != "排泄入力":
            if 'selected_user_id_for_excretion' in st.session_state:
                del st.session_state.selected_user_id_for_excretion
        if selected_option != "欠席入力":
            if 'selected_user_id_for_absence' in st.session_state:
                del st.session_state.selected_user_id_for_absence
        # Always clear selected_log_date unless staying on a related page (though input pages will set it)
        if 'selected_log_date' in st.session_state:
            del st.session_state.selected_log_date
        st.rerun()


    # 選択されたページを表示
    page = st.session_state.page

    if page == "日誌一覧":
        show_log_list_page()
    elif page == "日誌入力":
        show_log_input_page()
    elif page == "排泄入力":
        show_excretion_page()
    elif page == "欠席入力":
        show_absence_page()
    elif page == "利用者情報登録":
        show_user_info_page()
    elif page == "職員一覧":
        show_staff_page()

if __name__ == "__main__":
    main()
