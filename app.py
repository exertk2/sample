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
            cursor = conn.cursor()
            # 職員テーブル (staffs)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS staffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            ''')
            # 申請テーブル (applications)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER NOT NULL,
                    car_name TEXT,
                    color TEXT,
                    number TEXT, -- ナンバーをTEXT型に変更し、ゼロ埋めを考慮 (例: '0001')
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
        st.error(f"データベースの初期化中にエラーが発生しました: {e}")
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
        st.error(f"職員情報の取得中にエラーが発生しました: {e}")
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
            st.rerun() # 登録後にUIを更新し、リストを最新状態にする
    except sqlite3.IntegrityError:
        st.error(f"職員名「**{name}**」は既に登録されています。別の名前を試してください。")
    except sqlite3.Error as e:
        st.error(f"職員登録中に予期せぬエラーが発生しました: {e}")

def find_application(staff_id, fiscal_year, number):
    """
    指定された職員ID、年度、ナンバーに一致する申請データを検索します。
    見つからない場合はNoneを返します。
    """
    try:
        with get_db_connection() as conn:
            query = "SELECT * FROM applications WHERE staff_id = ? AND fiscal_year = ? AND number = ?"
            application = conn.execute(query, (staff_id, fiscal_year, number)).fetchone()
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
            if is_update:
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
                st.success("選択されたナンバーの申請情報を**修正**しました。")
            else:
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
                st.success("新しい申請情報を**登録**しました。")
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
            if number: # ナンバーが空文字やNoneでない場合
                # 部分一致検索
                query += " AND a.number LIKE ?"
                params.append(f"%{number}%") 
            
            query += " ORDER BY a.registration_timestamp DESC"
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
    職員登録ページのUIを表示します。
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
            else:
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
    申請入力ページのUIを表示します。
    既存の申請があればそのデータを読み込み、なければ新規入力として扱います。
    """
    st.header("📝 申請入力")
    st.markdown("車両の申請情報を入力または修正します。職員、年度、ナンバーの組み合わせで既存の申請を検索し、上書きすることが可能です。")
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
        st.session_state.selected_staff_name = staff_names[0] if staff_names else ""
    if 'selected_fiscal_year' not in st.session_state:
        st.session_state.selected_fiscal_year = get_current_fiscal_year()
    if 'input_number_str' not in st.session_state: # `input_number_str`で元の文字列を保持
        st.session_state.input_number_str = ""

    with st.form("application_input_form", clear_on_submit=False):
        st.subheader("1. 申請対象の選択（既存データの検索・上書き）")

        col1, col2, col3 = st.columns(3)
        with col1:
            selected_staff_name = st.selectbox(
                "職員氏名", 
                staff_names, 
                index=staff_names.index(st.session_state.selected_staff_name) if st.session_state.selected_staff_name in staff_names else 0,
                key="staff_name_select",
                help="申請を行う職員を選択してください。"
            )
            # 選択された職員名をセッションステートに保存
            st.session_state.selected_staff_name = selected_staff_name
        
        with col2:
            current_fiscal_year = get_current_fiscal_year()
            # 現在の年度から前後数年間のオプションを生成
            fiscal_year_options = [f"{y}年度" for y in range(current_fiscal_year - 2, current_fiscal_year + 3)]
            default_fy_index = fiscal_year_options.index(f"{st.session_state.selected_fiscal_year}年度") if f"{st.session_state.selected_fiscal_year}年度" in fiscal_year_options else (fiscal_year_options.index(f"{current_fiscal_year}年度") if f"{current_fiscal_year}年度" in fiscal_year_options else 0)
            selected_fiscal_year_str = st.selectbox(
                "年度", 
                fiscal_year_options, 
                index=default_fy_index, 
                key="fiscal_year_select",
                help="申請対象の年度を選択してください。"
            )
            selected_fiscal_year = int(selected_fiscal_year_str.replace("年度", ""))
            # 選択された年度をセッションステートに保存
            st.session_state.selected_fiscal_year = selected_fiscal_year
            
        with col3:
            # ナンバーは4桁の文字列として入力、初期値はセッションステートから
            input_number_str = st.text_input(
                "ナンバー (4桁の数字)", 
                value=st.session_state.input_number_str, # 元の入力文字列を保持
                key="number_input",
                max_chars=4, # 4文字までに制限
                help="車両のナンバープレートの4桁の数字を入力してください。例: 1234"
            )
            # 常に4桁表示にするための整形 (内部処理用、表示は元の文字列)
            # input_number_strが数字でなければそのまま、数字なら4桁ゼロ埋め
            processed_number = input_number_str.zfill(4) if input_number_str.isdigit() else input_number_str
            
            # 入力されたナンバー文字列をセッションステートに保存
            st.session_state.input_number_str = input_number_str

        # 既存データの検索と初期値設定
        selected_staff_id = staff_options.get(selected_staff_name)
        existing_app = None
        is_update_mode = False

        # ナンバーが有効な4桁の数字で、職員と年度が選択されている場合のみ検索
        if selected_staff_id and processed_number.isdigit() and len(processed_number) == 4:
            existing_app = find_application(selected_staff_id, selected_fiscal_year, processed_number)
            if existing_app:
                st.info(f"この職員、年度、ナンバーの組み合わせで**既存の申請情報が見つかりました**。以下のフォームにはその情報が自動入力されています。修正して「登録 / 修正」ボタンを押してください。")
                is_update_mode = True
            else:
                st.info("この組み合わせでは既存の申請情報は見つかりませんでした。新規登録として入力してください。")
        elif selected_staff_id and input_number_str and (not input_number_str.isdigit() or len(input_number_str) != 4):
             st.warning("ナンバーは正確に4桁の数字で入力してください。")
        elif selected_staff_id and not input_number_str:
            # ナンバー未入力の場合
            st.info("ナンバーを入力すると、既存の申請を検索できます。")


        # 初期値の辞書を作成
        # 既存の申請があればその値、なければデフォルト値を使用
        initial_values = {
            'car_name': existing_app['car_name'] if existing_app else "",
            'color': existing_app['color'] if existing_app else "",
            'unlimited_personal': existing_app['unlimited_personal'] if existing_app else False,
            'unlimited_property': existing_app['unlimited_property'] if existing_app else False,
            'commuting_purpose': existing_app['commuting_purpose'] if existing_app else False,
            'purpose_unknown': existing_app['purpose_unknown'] if existing_app else False,
        }

        st.subheader("2. 車両情報・保険情報の入力")

        col_input1, col_input2 = st.columns(2)
        with col_input1:
            car_name = st.text_input("車名", value=initial_values['car_name'], help="車両のメーカー名と車種名を入力してください。例: トヨタ プリウス").strip()
        with col_input2:
            color = st.text_input("色", value=initial_values['color'], help="車両の代表的な色を入力してください。例: 白、黒、シルバー").strip()
        
        st.markdown("---")
        st.subheader("3. 保険・目的情報のチェック")

        col_check1, col_check2, col_check3, col_check4 = st.columns(4)
        with col_check1:
            unlimited_personal = st.checkbox("対人無制限", value=initial_values['unlimited_personal'], help="自動車保険の対人賠償が無制限の場合にチェックしてください。")
        with col_check2:
            unlimited_property = st.checkbox("対物無制限", value=initial_values['unlimited_property'], help="自動車保険の対物賠償が無制限の場合にチェックしてください。")
        with col_check3:
            commuting_purpose = st.checkbox("通勤目的", value=initial_values['commuting_purpose'], help="主に通勤のために車両を使用する場合にチェックしてください。")
        with col_check4:
            purpose_unknown = st.checkbox("目的不明", value=initial_values['purpose_unknown'], help="車両の使用目的が不明確な場合にチェックしてください。")

        st.markdown("---")
        submitted = st.form_submit_button("登録 / 修正")

        if submitted:
            # 必須項目のチェック
            if not selected_staff_name:
                st.error("職員氏名を選択してください。")
            elif not car_name:
                st.error("車名を入力してください。")
            elif not color:
                st.error("色を入力してください。")
            elif not (processed_number.isdigit() and len(processed_number) == 4):
                st.error("ナンバーは正確に4桁の数字で入力してください。例: 1234")
            else:
                application_data = {
                    'staff_id': selected_staff_id,
                    'fiscal_year': selected_fiscal_year,
                    'number': processed_number, # 整形済みの4桁ナンバーを使用
                    'car_name': car_name,
                    'color': color,
                    'unlimited_personal': unlimited_personal,
                    'unlimited_property': unlimited_property,
                    'commuting_purpose': commuting_purpose,
                    'purpose_unknown': purpose_unknown,
                    'timestamp': datetime.now(JST)
                }
                # 新規登録か更新かを判断して処理を実行
                upsert_application(application_data, is_update=is_update_mode)

def show_application_list_page():
    """
    申請一覧ページのUIを表示します。
    検索条件（年度、ナンバー）でフィルタリングして表示できます。
    """
    st.header("📊 申請一覧")
    st.markdown("登録されている全ての申請情報、または検索条件に合致する申請情報を表示します。")
    st.markdown("---")

    st.subheader("検索条件")

    col_search1, col_search2 = st.columns(2)
    with col_search1:
        current_fiscal_year = get_current_fiscal_year()
        # 検索年度のオプションには「すべて」を追加
        fy_options = ["すべて"] + [f"{y}年度" for y in range(current_fiscal_year - 5, current_fiscal_year + 2)]
        
        # セッションステートで選択状態を保持
        if 'search_fiscal_year_selected' not in st.session_state:
            st.session_state.search_fiscal_year_selected = f"{current_fiscal_year}年度"
        
        search_fy_str = st.selectbox(
            "年度", 
            fy_options, 
            index=fy_options.index(st.session_state.search_fiscal_year_selected) if st.session_state.search_fiscal_year_selected in fy_options else 0, 
            key="list_search_fy",
            help="表示する申請の年度を絞り込みます。「すべて」を選択すると全年度の申請を表示します。"
        )
        # 選択された年度をセッションステートに保存
        st.session_state.search_fiscal_year_selected = search_fy_str 
        search_fiscal_year = int(search_fy_str.replace("年度", "")) if search_fy_str != "すべて" else None
    
    with col_search2:
        # セッションステートで選択状態を保持
        if 'search_number_input' not in st.session_state:
            st.session_state.search_number_input = ""
        
        search_number_input = st.text_input(
            "ナンバー (部分一致検索)", 
            value=st.session_state.search_number_input, 
            key="list_search_number",
            help="ナンバーの一部または全部を入力して検索します。例: '12' で '0012' や '1234' を検索。"
        ).strip() # 前後の空白を削除
        # 入力値をセッションステートに保存
        st.session_state.search_number_input = search_number_input 
        search_number = search_number_input if search_number_input else None 

    st.markdown("---")
    st.subheader("検索結果")

    # 検索実行
    applications = search_applications(fiscal_year=search_fiscal_year, number=search_number)

    if applications:
        st.write(f"🔍 **{len(applications)}** 件の申請が見つかりました。")
        df = pd.DataFrame([dict(row) for row in applications])

        # 表示用にデータを加工
        # Boolean値をチェックマークに変換
        df['対人無制限'] = df['unlimited_personal'].apply(lambda x: '✔' if x else '')
        df['対物無制限'] = df['unlimited_property'].apply(lambda x: '✔' if x else '')
        df['通勤目的'] = df['commuting_purpose'].apply(lambda x: '✔' if x else '')
        df['目的不明'] = df['purpose_unknown'].apply(lambda x: '✔' if x else '')
        
        # 年度と登録日時のフォーマット
        df['年度'] = df['fiscal_year'].astype(str) + '年度'
        df['登録日時'] = pd.to_datetime(df['registration_timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

        # 表示するカラムの選択とリネーム
        df_display = df.rename(columns={
            'id': 'ID', 
            'staff_name': '職員氏名', 
            'car_name': '車名', 
            'color': '色', 
            'number': 'ナンバー'
        })
        
        display_columns = [
            'ID', '年度', '職員氏名', '車名', '色', 'ナンバー', '対人無制限', 
            '対物無制限', '通勤目的', '目的不明', '登録日時'
        ]
        
        # Streamlit dataframe with increased height for better view
        st.dataframe(df_display[display_columns], hide_index=True, height=500) # 高さ調整
    else:
        st.info("該当する申請はありません。検索条件を変更して再度お試しください。")
    st.markdown("---")

# ==============================================================================
# メイン処理 (Main Application Logic)
# ==============================================================================

def main():
    """
    アプリケーションのメインエントリポイント
    サイドバーでページを切り替えます。
    """
    st.set_page_config(layout="wide", page_title="通勤車両管理アプリ", page_icon="🚗")
    init_db()  # アプリケーション起動時にDBを初期化

    st.sidebar.title("🚗 通勤車両管理アプリ")
    st.sidebar.markdown("車両の申請情報と職員を管理するシンプルなアプリケーションです。")
    
    # セッションステートで現在の選択メニューを管理
    if 'current_menu' not in st.session_state:
        st.session_state.current_menu = "申請入力"

    menu_options = {
        "申請入力": "📝 申請入力",
        "申請一覧": "📊 申請一覧",
        "職員登録": "👤 職員登録"
    }
    
    choice = st.sidebar.radio(
        "メニュー", 
        list(menu_options.values()),
        index=list(menu_options.values()).index(menu_options[st.session_state.current_menu]),
        key="main_menu_selector"
    )

    # 選択されたメニューのキーを取得
    selected_key = next(key for key, value in menu_options.items() if value == choice)
    st.session_state.current_menu = selected_key

    page_functions = {
        "申請入力": show_application_input_page,
        "申請一覧": show_application_list_page,
        "職員登録": show_staff_registration_page,
    }
    
    # 選択されたメニューに応じた関数を実行
    page_functions[st.session_state.current_menu]()


if __name__ == "__main__":
    main()
