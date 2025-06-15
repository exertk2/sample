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
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            department TEXT DEFAULT '通所支援Ⅰ係'
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
    
    # 欠席記録テーブル（仕様が複雑なため主要項目のみ実装）
    c.execute('''
        CREATE TABLE IF NOT EXISTS absences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reception_date DATE,
            reception_staff_id INTEGER,
            contact_person TEXT,
            absence_start_date DATE,
            absence_end_date DATE,
            reason TEXT, -- 簡略化のためテキストエリアで一括入力
            support_content TEXT, -- 簡略化のためテキストエリアで一括入力
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
    staff = conn.execute('SELECT id, name FROM staff ORDER BY name').fetchall()
    conn.close()
    return staff

def get_user_list():
    """利用者リストを取得する"""
    conn = get_db_connection()
    users = conn.execute('SELECT id, name FROM users WHERE is_active = 1 ORDER BY kana').fetchall()
    conn.close()
    return users

def get_user_by_id(user_id):
    """IDで利用者情報を取得する"""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
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
    st.header("職員一覧・登録")

    with st.form("new_staff_form", clear_on_submit=True):
        st.write("##### 新規職員登録")
        new_staff_name = st.text_input("職員氏名")
        submitted = st.form_submit_button("登録")
        if submitted and new_staff_name:
            try:
                conn = get_db_connection()
                conn.execute('INSERT INTO staff (name) VALUES (?)', (new_staff_name,))
                conn.commit()
                conn.close()
                st.success(f"{new_staff_name}さんを登録しました。")
            except sqlite3.IntegrityError:
                st.error("この職員は既に登録されています。")

    st.write("---")
    st.write("##### 登録済み職員")
    staff_df = pd.read_sql("SELECT name AS '氏名', department AS '所属' FROM staff WHERE department = '通所支援Ⅰ係' ORDER BY name", get_db_connection())
    st.dataframe(staff_df, use_container_width=True)


def show_user_info_page():
    """利用者情報登録ページ"""
    st.header("利用者情報登録")

    days_of_week = ["月", "火", "水", "木", "金", "土", "日"]
    
    # 既存利用者選択ロジック
    users = get_user_list()
    user_options = {"新規利用者登録": None}
    user_options.update({user['name']: user['id'] for user in users})
    
    selected_user_name = st.selectbox(
        "利用者を選択（新規登録または既存の利用者情報を編集）",
        options=list(user_options.keys()),
        index=0 # Default to "新規利用者登録"
    )
    
    selected_user_id_for_edit = user_options[selected_user_name]
    current_user_data = None
    if selected_user_id_for_edit:
        current_user_data = get_user_by_id(selected_user_id_for_edit)

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
        name = c2.text_input("氏名 *", value=initial_name)
        kana = c1.text_input("フリガナ", value=initial_kana)
        
        # 生年月日の入力可能範囲を制限なしにする (1900年1月1日から現在まで)
        birthday = c2.date_input(
            "生年月日", 
            value=initial_birthday, 
            min_value=datetime(1900, 1, 1).date(), # 1900年1月1日を最小値に設定
            max_value=datetime.now(JST).date() # 現在の日付を最大値に設定
        )
        
        gender = c1.selectbox("性別", ["男", "女", "その他"], index=["男", "女", "その他"].index(initial_gender) if initial_gender else None)
        patient_category = c2.selectbox("患者区分", ["たんぽぽ", "ゆり", "さくら", "すみれ", "なのはな", "療護", "外来"], index=["たんぽぽ", "ゆり", "さくら", "すみれ", "なのはな", "療護", "外来"].index(initial_patient_category) if initial_patient_category else None)

        is_active = st.checkbox("在籍中", value=initial_is_active)
        c1, c2 = st.columns(2)
        start_date = c1.date_input("利用開始日", value=initial_start_date)
        end_date = c2.date_input("退所年月日", value=initial_end_date)
        
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
                disabled_med_day = not use_days_checkbox_states.get(day, False)
                # If a checkbox is disabled, its value will be False by default if not explicitly set
                if st.checkbox(day, value=(day in initial_medication_days_list), key=f"medication_{day}_user_info", disabled=disabled_med_day):
                    medication_days_selected.append(day)
        
        st.write("---")
        st.write("##### 入浴曜日")
        bath_days_cols = st.columns(7)
        bath_days_selected = []
        for i, day in enumerate(days_of_week):
            with bath_days_cols[i]:
                disabled_bath_day = not use_days_checkbox_states.get(day, False)
                # If a checkbox is disabled, its value will be False by default if not explicitly set
                if st.checkbox(day, value=(day in initial_bath_days_list), key=f"bath_{day}_user_info", disabled=disabled_bath_day):
                    bath_days_selected.append(day)
        
        c_submit1, c_submit2 = st.columns(2)

        if selected_user_id_for_edit is None: # 新規登録モード
            submitted = c_submit1.form_submit_button("新規登録する")
        else: # 更新モード
            submitted = c_submit1.form_submit_button("更新する")
            
        if submitted:
            if not name:
                st.error("氏名は必須です。")
            else:
                use_days_str = ",".join([day for day, selected in use_days_checkbox_states.items() if selected])
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
                            WHERE id=?
                        ''', (name, kana, birthday, gender, patient_category, is_active, start_date, end_date, use_days_str, medication_days_str, bath_days_str, selected_user_id_for_edit))
                        st.success(f"{name}さんの情報を更新しました。")
                    conn.commit()
                except sqlite3.IntegrityError:
                    st.error("その利用者コードは既に使用されています。")
                except Exception as e:
                    st.error(f"処理中にエラーが発生しました: {e}")
                finally:
                    conn.close()


def show_log_list_page():
    """日誌一覧ページ"""
    st.header("日誌一覧")
    
    # Get current date in JST
    current_jst_date = datetime.now(JST).date()
    log_date = st.date_input("対象日を選択", current_jst_date)
    weekday_map = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
    selected_weekday = weekday_map[log_date.weekday()]
    st.info(f"{log_date.strftime('%Y年%m月%d日')} は **{selected_weekday}曜日** です。")

    conn = get_db_connection()
    # 利用曜日に基づいて利用者をフィルタリング
    query = f"SELECT id, name FROM users WHERE is_active = 1 AND use_days LIKE '%{selected_weekday}%' ORDER BY kana"
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
            user_id = user["id"]
            user_name = user["name"]
            
            # Use separate columns for each row's elements
            col_name, col_log, col_excretion, col_absence = st.columns([0.5, 0.2, 0.1, 0.1])
            
            with col_name:
                st.write(user_name)
            
            # Daily Log button
            with col_log:
                if st.button("✏️", key=f"log_{user_id}"):
                    st.session_state.page = "日誌入力"
                    st.session_state.selected_user_id_for_log = user_id
                    st.session_state.selected_log_date = log_date
                    st.rerun() 
            
            # Excretion button
            with col_excretion:
                if st.button("🚽", key=f"excretion_{user_id}"):
                    st.session_state.page = "排泄入力"
                    st.session_state.selected_user_id_for_excretion = user_id
                    st.session_state.selected_log_date = log_date
                    st.rerun() 
                    
            # Absence button
            with col_absence:
                if st.button("❌", key=f"absence_{user_id}"):
                    st.session_state.page = "欠席入力"
                    st.session_state.selected_user_id_for_absence = user_id
                    st.session_state.selected_log_date = log_date
                    st.rerun()

    st.write("---")
    with st.expander("臨時利用者の追加"):
        users = get_user_list()
        user_options = {user['id']: user['name'] for user in users}
        
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
    user_options = {user['id']: user['name'] for user in users}
    
    staff = get_staff_list()
    staff_options = {s['id']: s['name'] for s in staff}
    
    # Get current date in JST
    current_jst_date = datetime.now(JST).date()

    # Pre-select user and date if coming from log list
    initial_user_id = st.session_state.get('selected_user_id_for_log', None)
    initial_log_date = st.session_state.get('selected_log_date', current_jst_date)

    c1, c2 = st.columns(2)

    # Safely determine the index for the user selectbox
    selected_user_index = None
    user_keys = list(user_options.keys())
    if initial_user_id is not None and initial_user_id in user_keys:
        try:
            selected_user_index = user_keys.index(initial_user_id)
        except ValueError:
            selected_user_index = None # Fallback if not found for some reason

    selected_user_id = c1.selectbox(
        "利用者を選択",
        options=user_keys,
        format_func=lambda x: user_options.get(x, "選択してください"),
        index=selected_user_index
    )
    log_date = c2.date_input("利用日", initial_log_date)

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
            is_absent = st.checkbox("欠席", value=bool(log_data['is_absent'])) 

            st.write("---")
            st.write("##### バイタル")
            c1, c2, c3, c4, c5 = st.columns(5)
            temperature = c1.number_input("体温", min_value=30.0, max_value=45.0, step=0.1, format="%.1f", 
                                value=log_data['temperature'] if log_data and log_data['temperature'] is not None else 36.5)
            pulse = c2.number_input("脈", min_value=0, max_value=200, step=1, 
                                value=log_data['pulse'] if log_data and log_data['pulse'] is not None else 70)
            spo2 = c3.number_input("SPO2", min_value=0, max_value=100, step=1, 
                                value=log_data['spo2'] if log_data and log_data['spo2'] is not None else 98)
            bp_high = c4.number_input("最高血圧", min_value=0, max_value=300, step=1, 
                                value=log_data['bp_high'] if log_data and log_data['bp_high'] is not None else 120)
            bp_low = c5.number_input("最低血圧", min_value=0, max_value=200, step=1, 
                                value=log_data['bp_low'] if log_data and log_data['bp_low'] is not None else 80)
            weight = c1.number_input("体重", min_value=0.0, max_value=200.0, step=0.1, format="%.1f", 
                                value=log_data['weight'] if log_data and log_data['weight'] is not None else 50.0)

            st.write("---")
            st.write("##### 内服・口腔ケア")
            c1, c2 = st.columns(2)
            medication_check = c1.checkbox("内服実施", value=bool(log_data['medication_check']))
            
            staff_keys = list(staff_options.keys())
            medication_staff_index = None
            if log_data and log_data['medication_staff_id'] is not None and log_data['medication_staff_id'] in staff_keys:
                try:
                    medication_staff_index = staff_keys.index(log_data['medication_staff_id'])
                except ValueError:
                    pass
            
            disable_med_staff_input = not medication_check
            medication_staff_id = c2.selectbox(
                "内服実施職員", 
                options=staff_keys, 
                format_func=lambda x: staff_options.get(x), 
                index=medication_staff_index,
                disabled=disable_med_staff_input
            )
            
            c1, c2 = st.columns(2)
            oral_care_check = c1.checkbox("口腔ケア実施", value=bool(log_data['oral_care_check']))
            
            oral_care_staff_index = None
            if log_data and log_data['oral_care_staff_id'] is not None and log_data['oral_care_staff_id'] in staff_keys:
                try:
                    oral_care_staff_index = staff_keys.index(log_data['oral_care_staff_id'])
                except ValueError:
                    pass

            disable_oral_staff_input = not oral_care_check
            oral_care_staff_id = c2.selectbox(
                "口腔ケア実施職員", 
                options=staff_keys, 
                format_func=lambda x: staff_options.get(x), 
                index=oral_care_staff_index,
                disabled=disable_oral_staff_input
            )

            st.write("---")
            st.write("##### 入浴")
            bath_check = st.checkbox("入浴実施", value=bool(log_data['bath_check']))
            c1, c2, c3, c4 = st.columns(4)
            
            # Convert stored time string to datetime.time object for time_input
            bath_start_time_val = time(9, 0)
            if log_data and log_data['bath_start_time']:
                try:
                    bath_start_time_val = datetime.strptime(log_data['bath_start_time'], '%H:%M:%S').time()
                except (ValueError, TypeError):
                    pass # Keep default

            bath_end_time_val = time(10, 0)
            if log_data and log_data['bath_end_time']:
                try:
                    bath_end_time_val = datetime.strptime(log_data['bath_end_time'], '%H:%M:%S').time()
                except (ValueError, TypeError):
                    pass # Keep default

            disable_bath_input = not bath_check

            bath_start_time = c1.time_input("入浴開始時間", value=bath_start_time_val, disabled=disable_bath_input)
            
            bath_start_staff_index = None
            if log_data and log_data['bath_start_staff_id'] is not None and log_data['bath_start_staff_id'] in staff_keys:
                try:
                    bath_start_staff_index = staff_keys.index(log_data['bath_start_staff_id'])
                except ValueError:
                    pass
            bath_start_staff_id = c2.selectbox(
                "開始記録職員", 
                options=staff_keys, 
                format_func=lambda x: staff_options.get(x), 
                index=bath_start_staff_index, 
                key="bath_start_staff",
                disabled=disable_bath_input
            )
            
            bath_end_time = c3.time_input("入浴終了時間", value=bath_end_time_val, disabled=disable_bath_input)
            
            bath_end_staff_index = None
            if log_data and log_data['bath_end_staff_id'] is not None and log_data['bath_end_staff_id'] in staff_keys:
                try:
                    bath_end_staff_index = staff_keys.index(log_data['bath_end_staff_id'])
                except ValueError:
                    pass
            bath_end_staff_id = c4.selectbox(
                "終了記録職員", 
                options=staff_keys, 
                format_func=lambda x: staff_options.get(x), 
                index=bath_end_staff_index, 
                key="bath_end_staff",
                disabled=disable_bath_input
            )

            st.write("---")
            health_notes = st.text_area("特記（体調面）", value=log_data['health_notes'] or "")
            memo1 = st.text_area("その他１", value=log_data['memo1'] or "")
            memo2 = st.text_area("その他２", value=log_data['memo2'] or "")

            submitted = st.form_submit_button("日誌を保存")
            if submitted:
                conn = get_db_connection()
                try:
                    conn.execute('''
                        UPDATE daily_logs 
                        SET is_absent=?, temperature=?, pulse=?, spo2=?, bp_high=?, bp_low=?, 
                            medication_check=?, medication_staff_id=?, bath_check=?, bath_start_time=?, 
                            bath_start_staff_id=?, bath_end_time=?, bath_end_staff_id=?, oral_care_check=?, 
                            oral_care_staff_id=?, weight=?, health_notes=?, memo1=?, memo2=?
                        WHERE id = ?
                    ''', (is_absent, temperature, pulse, spo2, bp_high, bp_low, 
                          medication_check, medication_staff_id if medication_check else None, 
                          bath_check, bath_start_time.strftime('%H:%M:%S') if bath_check else None,
                          bath_start_staff_id if bath_check else None, 
                          bath_end_time.strftime('%H:%M:%S') if bath_check else None,
                          bath_end_staff_id if bath_check else None, 
                          oral_care_check, oral_care_staff_id if oral_care_check else None, 
                          weight, health_notes, memo1, memo2, log_id))
                    conn.commit()
                    st.success("日誌を保存しました。")
                except Exception as e:
                    st.error(f"保存中にエラーが発生しました: {e}")
                finally:
                    conn.close()
    else:
        st.info("利用者と利用日を選択してください。")

def show_excretion_page():
    """排泄入力ページ"""
    st.header("排泄入力")
    
    users = get_user_list()
    user_options = {user['id']: user['name'] for user in users}
    
    staff = get_staff_list()
    staff_options = {s['id']: s['name'] for s in staff}
    staff_options_with_none = {None: "なし"}
    staff_options_with_none.update(staff_options)


    # Get current date and time in JST
    now_jst = datetime.now(JST)
    current_jst_date = now_jst.date()
    current_jst_time = now_jst.time()

    # Pre-select user and date if coming from log list
    initial_user_id = st.session_state.get('selected_user_id_for_excretion', None)
    initial_log_date = st.session_state.get('selected_log_date', current_jst_date)

    c1, c2 = st.columns(2)

    # Safely determine the index for the user selectbox
    user_keys = list(user_options.keys())
    selected_user_index = None
    if initial_user_id is not None and initial_user_id in user_keys:
        try:
            selected_user_index = user_keys.index(initial_user_id)
        except ValueError:
            pass # index remains None

    selected_user_id = c1.selectbox(
        "利用者を選択",
        options=user_keys,
        format_func=lambda x: user_options.get(x),
        index=selected_user_index
    )
    log_date = c2.date_input("利用日", initial_log_date)
    
    if selected_user_id and log_date:
        log_id = get_or_create_log_id(selected_user_id, log_date)
        
        with st.form("excretion_form", clear_on_submit=True):
            st.write(f"##### {user_options[selected_user_id]}さんの排泄記録")
            
            c1, c2 = st.columns(2)
            excretion_time = c1.time_input("排泄時間", value=current_jst_time)
            excretion_type = c2.selectbox("分類", ["尿", "便"], index=None)
            
            c1, c2 = st.columns(2)
            
            staff1_id = c1.selectbox("排泄介助職員1", options=list(staff_options.keys()), format_func=lambda x: staff_options.get(x), index=None)
            
            staff2_id = c2.selectbox("排泄介助職員2", options=list(staff_options_with_none.keys()), format_func=lambda x: staff_options_with_none.get(x), index=0)
            
            notes = st.text_area("特記事項")
            
            submitted = st.form_submit_button("記録を追加")
            
            if submitted:
                if excretion_type and staff1_id:
                    conn = get_db_connection()
                    try:
                        conn.execute(
                            'INSERT INTO excretions (log_id, excretion_time, type, staff1_id, staff2_id, notes) VALUES (?, ?, ?, ?, ?, ?)',
                            (log_id, excretion_time.strftime('%H:%M:%S'), excretion_type, staff1_id, staff2_id, notes)
                        )
                        conn.commit()
                        st.success("排泄記録を追加しました。")
                    except Exception as e:
                        st.error(f"登録中にエラーが発生しました: {e}")
                    finally:
                        conn.close()
                else:
                    st.error("分類と介助職員1は必須です。")

        # Rerun is handled by form clear_on_submit, but manual success message helps.
        # To refresh the list below, we must read data after the form submission.

        # 記録一覧の表示
        st.write("---")
        st.write("##### 本日の記録一覧")
        conn = get_db_connection()
        try:
            records_df = pd.read_sql_query(f'''
                SELECT 
                    e.id,
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
            ''', conn, index_col='id')
            
            if not records_df.empty:
              st.dataframe(records_df, use_container_width=True)
            else:
              st.info("この利用者の本日の排泄記録はまだありません。")

        except Exception as e:
            st.error(f"記録の読み込み中にエラーが発生しました: {e}")
        finally:
             conn.close()


def show_absence_page():
    """欠席入力ページ"""
    st.header("欠席入力")

    users = get_user_list()
    user_options = {user['id']: user['name'] for user in users}
    
    staff = get_staff_list()
    staff_options = {s['id']: s['name'] for s in staff}

    # Get current date in JST
    current_jst_date = datetime.now(JST).date()

    # Pre-select user if coming from log list
    initial_user_id = st.session_state.get('selected_user_id_for_absence', None)
    initial_log_date = st.session_state.get('selected_log_date', current_jst_date)
    
    user_keys = list(user_options.keys())
    # Safely determine the index for the user selectbox
    selected_user_index = None
    if initial_user_id is not None and initial_user_id in user_keys:
        try:
            selected_user_index = user_keys.index(initial_user_id)
        except ValueError:
            pass # index remains None

    selected_user_id = st.selectbox(
        "欠席者を選択",
        options=user_keys,
        format_func=lambda x: user_options.get(x),
        index=selected_user_index,
        placeholder="利用者を選択してください"
    )

    if selected_user_id:
        with st.form("absence_form", clear_on_submit=True):
            st.write(f"##### {user_options[selected_user_id]}さんの欠席情報")
            c1, c2 = st.columns(2)
            
            staff_keys = list(staff_options.keys())
            reception_staff_id = c1.selectbox("受付職員", options=staff_keys, format_func=lambda x: staff_options.get(x), index=None, placeholder="職員を選択してください")
            reception_date = c2.date_input("受付日", initial_log_date)

            contact_person = st.text_input("欠席の連絡者")
            
            c1, c2 = st.columns(2)
            absence_start_date = c1.date_input("欠席期間（開始）", initial_log_date)
            absence_end_date = c2.date_input("欠席期間（終了）", initial_log_date)
            
            reason = st.text_area("欠席理由（詳細を記入）", help="例：本人の体調不良（発熱38.0℃、咳あり）のため。")
            support = st.text_area("援助内容（詳細を記入）", help="例：体調確認、医療機関の受診を勧めた。")

            submitted = st.form_submit_button("欠席情報を登録")
            if submitted:
                if reception_staff_id and reason:
                    try:
                        # データベースへの保存処理
                        conn = get_db_connection()
                        conn.execute('''
                            INSERT INTO absences (user_id, reception_date, reception_staff_id, contact_person, absence_start_date, absence_end_date, reason, support_content)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (selected_user_id, reception_date, reception_staff_id, contact_person, absence_start_date, absence_end_date, reason, support))
                        
                        # 同日の日誌を欠席に更新
                        log_id = get_or_create_log_id(selected_user_id, absence_start_date)
                        conn.execute('UPDATE daily_logs SET is_absent = 1 WHERE id = ?', (log_id,))
                        
                        conn.commit()
                        st.success("欠席情報を登録し、該当日誌を「欠席」に更新しました。")
                    except Exception as e:
                        st.error(f"登録中にエラーが発生しました: {e}")
                    finally:
                        if conn:
                            conn.close()
                else:
                    st.error("受付職員と欠席理由は必須です。")


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
    
    # サイドバーのボタンでページを切り替える
    for option in menu_options:
        if st.sidebar.button(option, key=f"menu_{option}"):
            st.session_state.page = option
            # Clear specific session state variables when navigating from sidebar
            # to prevent pre-filling forms unexpectedly when not coming from list page
            for key in ['selected_user_id_for_log', 'selected_user_id_for_excretion', 'selected_user_id_for_absence', 'selected_log_date']:
                if key in st.session_state:
                    del st.session_state[key]
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
