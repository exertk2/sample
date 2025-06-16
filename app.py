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
    """
    データベース接続を取得します。
    行を辞書のようにアクセスできるようrow_factoryを設定します。
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    データベーステーブルを初期化します。
    テーブルが存在しない場合のみ作成されます。
    """
    try:
        with get_db_connection() as conn:
            [span_1](start_span)cursor = conn.cursor()[span_1](end_span)
            # 職員テーブル (staffs)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS staffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    [span_2](start_span)name TEXT NOT NULL UNIQUE[span_2](end_span)
                )
            ''')
            # 申請テーブル (applications)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    [span_3](start_span)id INTEGER PRIMARY KEY AUTOINCREMENT,[span_3](end_span)
                    staff_id INTEGER NOT NULL,
                    [span_4](start_span)fiscal_year INTEGER NOT NULL,[span_4](end_span)
                    vehicle_seq_num INTEGER NOT NULL, -- 新しく追加: 職員と年度ごとの車両連番
                    car_name TEXT,
                    color TEXT,
                    [span_5](start_span)number TEXT, -- ナンバーをTEXT型に変更し、ゼロ埋めを考慮 (例: '0001')[span_5](end_span)
                    [span_6](start_span)unlimited_personal BOOLEAN,[span_6](end_span)
                    [span_7](start_span)unlimited_property BOOLEAN,[span_7](end_span)
                    [span_8](start_span)commuting_purpose BOOLEAN,[span_8](end_span)
                    [span_9](start_span)purpose_unknown BOOLEAN,[span_9](end_span)
                    [span_10](start_span)registration_timestamp DATETIME,[span_10](end_span)
                    FOREIGN KEY (staff_id) REFERENCES staffs (id),
                    UNIQUE (staff_id, fiscal_year, vehicle_seq_num) -- ユニーク制約を変更
                )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        [span_11](start_span)st.error(f"データベースの初期化中にエラーが発生しました: {e}")[span_11](end_span)
        st.info("アプリケーションを再起動してみてください。")

def get_all_staffs():
    """
    登録済みの全職員を取得します。
    エラー発生時は空のリストを返します。
    """
    try:
        with get_db_connection() as conn:
            # 名前でソートして表示順を改善
            staffs = conn.execute("SELECT id, name FROM staffs ORDER BY name ASC").fetchall()
            return staffs
    except sqlite3.Error as e:
        [span_12](start_span)st.error(f"職員情報の取得中にエラーが発生しました: {e}")[span_12](end_span)
        return []

def add_staff(name):
    """
    新しい職員をデータベースに登録します。
    既に登録されている場合はエラーメッセージを表示します。
    """
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO staffs (name) VALUES (?)", (name,))
            conn.commit()
            st.success(f"職員「**{name}**」を登録しました。")
            [span_13](start_span)st.rerun()[span_13](end_span) # 登録後にUIを更新し、リストを最新状態にする
    except sqlite3.IntegrityError:
        st.error(f"職員名「**{name}」は既に登録されています。別の名前を試してください。")
    except sqlite3.Error as e:
        st.error(f"職員登録中に予期せぬエラーが発生しました: {e}")

def _get_next_vehicle_seq_num(staff_id, fiscal_year):
    """
    指定された職員と年度の次の車両連番を取得します。
    既存の車両がない場合は1を返します。
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(vehicle_seq_num) FROM applications WHERE staff_id = ? AND fiscal_year = ?",
                (staff_id, fiscal_year)
            )
            max_seq_num = cursor.fetchone()[0]
            return (max_seq_num or 0) + 1
    except sqlite3.Error as e:
        st.error(f"次の車両連番の取得中にエラーが発生しました: {e}")
        return 1 # エラー時はデフォルトで1を返すか、適切なエラーハンドリングを行う

def find_applications_by_staff_and_year(staff_id, fiscal_year):
    """
    指定された職員IDと年度に一致する全ての申請データを検索します。
    見つからない場合は空のリストを返します。
    """
    try:
        with get_db_connection() as conn:
            query = "SELECT * FROM applications WHERE staff_id = ? AND fiscal_year = ? ORDER BY vehicle_seq_num ASC"
            applications = conn.execute(query, (staff_id, fiscal_year)).fetchall()
            return applications
    except sqlite3.Error as e:
        st.error(f"申請データの検索中にエラーが発生しました: {e}")
        return []

def find_application_by_seq_num(staff_id, fiscal_year, vehicle_seq_num):
    """
    指定された職員ID、年度、車両連番に一致する申請データを検索します。
    見つからない場合はNoneを返します。
    """
    try:
        with get_db_connection() as conn:
            query = "SELECT * FROM applications WHERE staff_id = ? AND fiscal_year = ? AND vehicle_seq_num = ?"
            application = conn.execute(query, (staff_id, fiscal_year, vehicle_seq_num)).fetchone()
            return application
    except sqlite3.Error as e:
        st.error(f"申請データの検索中にエラーが発生しました: {e}")
        return None

def upsert_application(data, is_update):
    """
    申請データを新規登録または更新します。
    is_updateがTrueの場合は更新、Falseの場合は新規登録を行います。
    """
    try:
        with get_db_connection() as conn:
            [span_14](start_span)if is_update:[span_14](end_span)
                query = """
                    UPDATE applications
                    [span_15](start_span)SET car_name = ?, color = ?, number = ?, unlimited_personal = ?, unlimited_property = ?,[span_15](end_span)
                    commuting_purpose = ?, purpose_unknown = ?, registration_timestamp = ?
                    WHERE staff_id = ? AND fiscal_year = ? AND vehicle_seq_num = ?
                """
                params = (
                    data['car_name'], data['color'], data['number'], data['unlimited_personal'], data['unlimited_property'],
                    data['commuting_purpose'], data['purpose_unknown'], data['timestamp'],
                    data['staff_id'], data['fiscal_year'], data['vehicle_seq_num']
                [span_16](start_span))
                conn.execute(query, params)
                st.success(f"職員「{data['staff_name']}」の「{data['fiscal_year']}年度 第{data['vehicle_seq_num']}車両」の申請情報を**修正**しました。")
            else:
                query = """
                    INSERT INTO applications
                    (staff_id, fiscal_year, vehicle_seq_num, car_name, color, number, unlimited_personal, unlimited_property,
                     commuting_purpose, purpose_unknown, registration_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """[span_16](end_span)
                params = (
                    data['staff_id'], data['fiscal_year'], data['vehicle_seq_num'], data['car_name'], data['color'], data['number'],
                    data['unlimited_personal'], data['unlimited_property'], data['commuting_purpose'],
                    data['purpose_unknown'], data['timestamp']
                [span_17](start_span))
                conn.execute(query, params)[span_17](end_span)
                st.success(f"職員「{data['staff_name']}」の「{data['fiscal_year']}年度 第{data['vehicle_seq_num']}車両」として新しい申請情報を**登録**しました。")
            conn.commit()
            st.rerun() # 登録/修正後にUIを更新
    except sqlite3.Error as e:
        st.error(f"申請の登録または修正中にエラーが発生しました: {e}")

def search_applications(fiscal_year=None, number=None):
    """
    条件に基づいて申請一覧を検索します。
    年度またはナンバー、あるいは両方でフィルタリング可能です。
    ナンバーは部分一致検索をサポートします。
    """
    try:
        [span_18](start_span)with get_db_connection() as conn:[span_18](end_span)
            query = """
                SELECT a.id, s.name AS staff_name, a.car_name, a.color, a.number, a.vehicle_seq_num,
                       a.unlimited_personal, a.unlimited_property, a.commuting_purpose,
                       a.purpose_unknown, a.registration_timestamp, a.fiscal_year
                [span_19](start_span)FROM applications a JOIN staffs s ON a.staff_id = s.id[span_19](end_span)
                WHERE 1=1
            """
            params = []
            if fiscal_year:
                [span_20](start_span)query += " AND a.fiscal_year = ?"[span_20](end_span)
                [span_21](start_span)params.append(fiscal_year)[span_21](end_span)
            if number: # ナンバーが空文字やNoneでない場合
                # 部分一致検索
                query += " AND a.number LIKE ?"
                params.append(f"%{number}%")
            
            [span_22](start_span)query += " ORDER BY a.registration_timestamp DESC"[span_22](end_span)
            return conn.execute(query, params).fetchall()
    except sqlite3.Error as e:
        st.error(f"申請一覧の検索中にエラーが発生しました: {e}")
        return []

# ==============================================================================
# ヘルパー関数 (Helper Functions)
# ==============================================================================

def get_current_fiscal_year():
    """
    現在の日本の日付に基づいて年度を返します。
    (4月始まり)
    """
    now = datetime.now(JST)
    return now.year if now.month >= 4 else now.year - 1

# ==============================================================================
# UI表示関連の関数 (UI Display Functions)
# ==============================================================================

def show_staff_registration_page():
    """
    [span_23](start_span)職員登録ページのUIを表示します。[span_23](end_span)
    """
    st.header("👤 職員登録")
    st.markdown("新しい職員の氏名を登録します。登録された職員は申請時に選択できるようになります。")
    st.markdown("---")

    with st.form("staff_registration_form"):
        staff_name = st.text_input("氏名", help="登録する職員のフルネームを入力してください。").strip() # 前後の空白を削除
        submitted = st.form_submit_button("職員を登録")

        if submitted:
            if staff_name:
                add_staff(staff_name)
            [span_24](start_span)else:[span_24](end_span)
                st.warning("氏名を入力してください。")

    st.subheader("📚 登録済職員一覧")
    staffs = get_all_staffs()
    if staffs:
        df_staffs = pd.DataFrame([dict(s) for s in staffs])
        # カラム名をより分かりやすくする
        df_staffs.rename(columns={'id': '職員ID', 'name': '氏名'}, inplace=True)
        st.dataframe(df_staffs, hide_index=True)
    else:
        st.info("現在、登録されている職員はいません。上記のフォームから新しい職員を登録してください。")
    st.markdown("---")


def show_application_input_page():
    """
    [span_25](start_span)申請入力ページのUIを表示します。[span_25](end_span)
    既存の申請があればそのデータを読み込み、なければ新規入力として扱います。
    """
    st.header("📝 申請入力")
    st.markdown("車両の申請情報を入力または修正します。職員、年度、第●車両の組み合わせで既存の申請を検索し、上書きすることが可能です。")
    st.markdown("---")

    staffs = get_all_staffs()
    if not staffs:
        st.warning("職員が一人も登録されていません。先に「職員登録」ページで職員を登録してください。")
        return

    # 職員名とIDのマッピング
    staff_options = {staff['name']: staff['id'] for staff in staffs}
    staff_names = list(staff_options.keys())

    # Streamlitのセッションステートでフォームの入力値を保持し、UIの再レンダリング時に値を維持
    if 'selected_staff_name' not in st.session_state:
        [span_26](start_span)st.session_state.selected_staff_name = staff_names[0] if staff_names else ""[span_26](end_span)
    if 'selected_fiscal_year' not in st.session_state:
        [span_27](start_span)st.session_state.selected_fiscal_year = get_current_fiscal_year()[span_27](end_span)
    if 'selected_vehicle_seq_num' not in st.session_state:
        st.session_state.selected_vehicle_seq_num = "新規登録"
    if 'input_number_str' not in st.session_state: # `input_number_str`で元の文字列を保持
        [span_28](start_span)st.session_state.input_number_str = ""[span_28](end_span)


    with st.form("application_input_form", clear_on_submit=False):
        [span_29](start_span)st.subheader("1. 申請対象の選択（既存データの検索・上書き）")[span_29](end_span)

        col1, col2, col3 = st.columns(3)
        with col1:
            selected_staff_name = st.selectbox(
                "職員氏名",
                staff_names,
                [span_30](start_span)index=staff_names.index(st.session_state.selected_staff_name) if st.session_state.selected_staff_name in staff_names else 0,[span_30](end_span)
                key="staff_name_select",
                help="申請を行う職員を選択してください。"
            )
            # 選択された職員名をセッションステートに保存
            st.session_state.selected_staff_name = selected_staff_name
        
        with col2:
            [span_31](start_span)current_fiscal_year = get_current_fiscal_year()[span_31](end_span)
            # 現在の年度から前後数年間のオプションを生成
            fiscal_year_options = [f"{y}年度" for y in range(current_fiscal_year - 2, current_fiscal_year + 3)]
            default_fy_index = fiscal_year_options.index(f"{st.session_state.selected_fiscal_year}年度") if f"{st.session_state.selected_fiscal_year}年度" in fiscal_year_options else (fiscal_year_options.index(f"{current_fiscal_year}年度") if f"{current_fiscal_year}年度" in fiscal_year_options else 0)
            selected_fiscal_year_str = st.selectbox(
                "年度",
                [span_32](start_span)fiscal_year_options,[span_32](end_span)
                index=default_fy_index,
                key="fiscal_year_select",
                help="申請対象の年度を選択してください。"
            )
            selected_fiscal_year = int(selected_fiscal_year_str.replace("年度", ""))
            # 選択された年度をセッションステートに保存
            [span_33](start_span)st.session_state.selected_fiscal_year = selected_fiscal_year[span_33](end_span)

        selected_staff_id = staff_options.get(selected_staff_name)

        # 職員と年度が選択されたら、その組み合わせの既存車両を取得
        existing_vehicles_for_staff_year = []
        if selected_staff_id and selected_fiscal_year:
            existing_apps = find_applications_by_staff_and_year(selected_staff_id, selected_fiscal_year)
            existing_vehicles_for_staff_year = [f"第{app['vehicle_seq_num']}車両" for app in existing_apps]

        # 新規登録オプションを追加
        vehicle_seq_num_options = ["新規登録"] + existing_vehicles_for_staff_year

        with col3:
            selected_vehicle_seq_num_str = st.selectbox(
                "車両選択",
                vehicle_seq_num_options,
                index=vehicle_seq_num_options.index(st.session_state.selected_vehicle_seq_num) if st.session_state.selected_vehicle_seq_num in vehicle_seq_num_options else 0,
                key="vehicle_seq_num_select",
                help="既存の車両を選択して修正するか、新規登録を選択してください。"
            )
            st.session_state.selected_vehicle_seq_num = selected_vehicle_seq_num_str

        is_update_mode = False
        existing_app_data = None
        current_vehicle_seq_num = None

        if selected_vehicle_seq_num_str != "新規登録":
            is_update_mode = True
            current_vehicle_seq_num = int(selected_vehicle_seq_num_str.replace("第", "").replace("車両", ""))
            existing_app_data = find_application_by_seq_num(selected_staff_id, selected_fiscal_year, current_vehicle_seq_num)
            if existing_app_data:
                st.info(f"この職員、年度、車両の組み合わせで**既存の申請情報が見つかりました**。以下のフォームにはその情報が自動入力されています。修正して「登録 / 修正」ボタンを押してください。")
            else:
                st.warning("選択された車両情報が見つかりませんでした。")
        else:
            # 新規登録モードの場合、次の連番を決定
            current_vehicle_seq_num = _get_next_vehicle_seq_num(selected_staff_id, selected_fiscal_year)
            st.info(f"新規登録モードです。この申請は「第{current_vehicle_seq_num}車両」として登録されます。")


        # 初期値の辞書を作成
        initial_values = {
            [span_34](start_span)'car_name': existing_app_data['car_name'] if existing_app_data else "",[span_34](end_span)
            [span_35](start_span)'color': existing_app_data['color'] if existing_app_data else "",[span_35](end_span)
            'number': existing_app_data['number'] if existing_app_data else "",
            [span_36](start_span)'unlimited_personal': existing_app_data['unlimited_personal'] if existing_app_data else False,[span_36](end_span)
            [span_37](start_span)'unlimited_property': existing_app_data['unlimited_property'] if existing_app_data else False,[span_37](end_span)
            [span_38](start_span)'commuting_purpose': existing_app_data['commuting_purpose'] if existing_app_data else False,[span_38](end_span)
            [span_39](start_span)'purpose_unknown': existing_app_data['purpose_unknown'] if existing_app_data else False,[span_39](end_span)
        }

        [span_40](start_span)st.subheader("2. 車両情報・保険情報の入力")[span_40](end_span)

        col_input1, col_input2 = st.columns(2)
        with col_input1:
            car_name = st.text_input("車名", value=initial_values['car_name'], help="車両のメーカー名と車種名を入力してください。例: トヨタ プリウス").strip()
        with col_input2:
            color = st.text_input("色", value=initial_values['color'], help="車両の代表的な色を入力してください。例: 白、黒、シルバー").strip()

        # ナンバー入力は引き続き必要だが、検索キーからは外れる
        input_number_str = st.text_input(
            "ナンバー (4桁の数字)",
            value=initial_values['number'], # ここもinitial_valuesから設定
            [span_41](start_span)key="number_input",[span_41](end_span)
            max_chars=4, # 4文字までに制限
            help="車両のナンバープレートの4桁の数字を入力してください。例: 1234"
        )
        # 常に4桁表示にするための整形 (内部処理用、表示は元の文字列)
        processed_number = input_number_str.zfill(4) if input_number_str.isdigit() else input_number_str
        st.session_state.input_number_str = input_number_str # セッションステートに元の入力文字列を保存


        st.markdown("---")
        [span_42](start_span)st.subheader("3. 保険・目的情報のチェック")[span_42](end_span)

        col_check1, col_check2, col_check3, col_check4 = st.columns(4)
        with col_check1:
            unlimited_personal = st.checkbox("対人無制限", value=initial_values['unlimited_personal'], help="自動車保険の対人賠償が無制限の場合にチェックしてください。")
        with col_check2:
            unlimited_property = st.checkbox("対物無制限", value=initial_values['unlimited_property'], help="自動車保険の対物賠償が無制限の場合にチェックしてください。")
        with col_check3:
            commuting_purpose = st.checkbox("通勤目的", value=initial_values['commuting_purpose'], help="主に通勤のために車両を使用する場合にチェックしてください。")
        with col_check4:
            [span_43](start_span)purpose_unknown = st.checkbox("目的不明", value=initial_values['purpose_unknown'], help="車両の使用目的が不明確な場合にチェックしてください。")[span_43](end_span)

        st.markdown("---")
        submitted = st.form_submit_button("登録 / 修正")

        if submitted:
            # 必須項目のチェック
            if not selected_staff_name:
                st.error("職員氏名を選択してください。")
            elif not car_name:
                [span_44](start_span)st.error("車名を入力してください。")[span_44](end_span)
            elif not color:
                st.error("色を入力してください。")
            elif not (processed_number.isdigit() and len(processed_number) == 4):
                st.error("ナンバーは正確に4桁の数字で入力してください。例: 1234")
            else:
                application_data = {
                    'staff_id': selected_staff_id,
                    'staff_name': selected_staff_name, # 成功メッセージ用に職員名も渡す
                    'fiscal_year': selected_fiscal_year,
                    'vehicle_seq_num': current_vehicle_seq_num, # 連番を使用
                    [span_45](start_span)'number': processed_number, # 整形済みの4桁ナンバーを使用[span_45](end_span)
                    [span_46](start_span)'car_name': car_name,[span_46](end_span)
                    [span_47](start_span)'color': color,[span_47](end_span)
                    [span_48](start_span)'unlimited_personal': unlimited_personal,[span_48](end_span)
                    [span_49](start_span)'unlimited_property': unlimited_property,[span_49](end_span)
                    [span_50](start_span)'commuting_purpose': commuting_purpose,[span_50](end_span)
                    [span_51](start_span)'purpose_unknown': purpose_unknown,[span_51](end_span)
                    [span_52](start_span)'timestamp': datetime.now(JST)[span_52](end_span)
                }
                # 新規登録か更新かを判断して処理を実行
                upsert_application(application_data, is_update=is_update_mode)


def show_applicat