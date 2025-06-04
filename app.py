import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

# アップロードファイルの保存先ディレクトリ
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# データベースの初期化
def init_db():
    conn = sqlite3.connect('document_management.db')
    c = conn.cursor()

    # 社員テーブルの作成
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            department TEXT,
            committee1 TEXT,
            committee2 TEXT,
            committee3 TEXT,
            committee4 TEXT,
            committee5 TEXT,
            password TEXT
        )
    ''')

    # 文書テーブルの作成 (file_path カラムを追加)
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT,
            issuer TEXT,
            remarks TEXT,
            file_path TEXT
        )
    ''')

    # 閲覧先テーブルの作成
    c.execute('''
        CREATE TABLE IF NOT EXISTS document_access (
            access_id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            access_type TEXT, -- 'employee', 'department', 'committee'
            access_value TEXT,
            FOREIGN KEY (document_id) REFERENCES documents(document_id)
        )
    ''')

    # 委員会等テーブルの作成
    c.execute('''
        CREATE TABLE IF NOT EXISTS committees (
            committee_name TEXT PRIMARY KEY
        )
    ''')

    # 閲覧ログテーブルの作成
    c.execute('''
        CREATE TABLE IF NOT EXISTS view_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            employee_id TEXT,
            view_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(document_id),
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    ''')

    conn.commit()
    conn.close()

# パスワードのハッシュ化
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 文書登録機能
def document_registration():
    st.subheader("文書登録・編集")

    conn = sqlite3.connect('document_management.db')
    c = conn.cursor()
    c.execute("SELECT document_id, document_name FROM documents")
    existing_documents = c.fetchall()
    conn.close()

    doc_options = ["新規文書"] + [f"{doc[0]}: {doc[1]}" for doc in existing_documents]
    selected_doc_option = st.selectbox("編集する文書を選択、または新規文書を作成", doc_options, key='doc_select')

    editing_document_id = None
    if selected_doc_option != "新規文書":
        editing_document_id = int(selected_doc_option.split(":")[0])
        st.session_state['editing_document_id'] = editing_document_id
    else:
        st.session_state['editing_document_id'] = None

    document_name = ""
    issuer = ""
    remarks = ""
    current_file_path = None

    # access_listの初期化と管理を改善
    # selected_doc_optionが変更されたとき、または初めてページがロードされたときにのみaccess_listをロード/クリアする
    if 'current_doc_select_id' not in st.session_state or \
       st.session_state['current_doc_select_id'] != selected_doc_option:
        
        st.session_state['current_doc_select_id'] = selected_doc_option # 選択されたオプションを記録
        
        if editing_document_id:
            st.info(f"文書番号 {editing_document_id} を編集します。")
            conn = sqlite3.connect('document_management.db')
            c = conn.cursor()
            c.execute("SELECT document_name, issuer, remarks, file_path FROM documents WHERE document_id = ?", (editing_document_id,))
            doc_data = c.fetchone()
            if doc_data:
                document_name, issuer, remarks, current_file_path = doc_data

            c.execute("SELECT access_type, access_value FROM document_access WHERE document_id = ?", (editing_document_id,))
            existing_accesses = c.fetchall()
            st.session_state['access_list'] = [{'type': acc[0], 'value': acc[1]} for acc in existing_accesses]
            conn.close()
            
            # フォームの初期値を設定
            st.session_state['doc_name_input'] = document_name
            st.session_state['issuer_input'] = issuer
            st.session_state['remarks_input'] = remarks
            st.session_state['current_document_id'] = editing_document_id
            st.session_state['current_document_name'] = document_name
        else: # 新規文書の場合
            # フォームをクリア
            if 'doc_name_input' in st.session_state:
                del st.session_state['doc_name_input']
            if 'issuer_input' in st.session_state:
                del st.session_state['issuer_input']
            if 'remarks_input' in st.session_state:
                del st.session_state['remarks_input']
            st.session_state['access_list'] = [] # 新規文書の場合はアクセスリストをクリア
            st.session_state['current_document_id'] = None
            st.session_state['current_document_name'] = None
    
    # 既存文書選択時のフォーム値の再設定（セレクトボックスの変更で再描画されるため）
    if editing_document_id:
        conn = sqlite3.connect('document_management.db')
        c = conn.cursor()
        c.execute("SELECT document_name, issuer, remarks, file_path FROM documents WHERE document_id = ?", (editing_document_id,))
        doc_data = c.fetchone()
        if doc_data:
            document_name, issuer, remarks, current_file_path = doc_data
        conn.close()


    document_name = st.text_input("文書名", value=st.session_state.get('doc_name_input', document_name), key='doc_name_input_key')
    issuer = st.text_input("発行元", value=st.session_state.get('issuer_input', issuer), key='issuer_input_key')
    remarks = st.text_area("備考", value=st.session_state.get('remarks_input', remarks), key='remarks_input_key')

    if current_file_path and os.path.exists(current_file_path):
        st.write(f"現在の添付ファイル: {os.path.basename(current_file_path)}")
        if st.checkbox("既存の添付ファイルを削除", key='delete_file_checkbox'):
            current_file_path = None # ファイルパスをNoneにして削除フラグとする
    uploaded_file = st.file_uploader("新しい添付ファイル (既存のファイルを置き換える場合)", type=["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"])


    submit_button_label = "文書を更新" if st.session_state['editing_document_id'] else "文書を登録"
    if st.button(submit_button_label):
        file_path_to_save = current_file_path

        if uploaded_file is not None:
            # 新しいファイルがアップロードされた場合
            if current_file_path and os.path.exists(current_file_path):
                os.remove(current_file_path) # 古いファイルを削除
            file_name = uploaded_file.name
            file_path_to_save = os.path.join(UPLOAD_DIR, file_name)
            with open(file_path_to_save, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"ファイル '{file_name}' を保存しました。")
        elif st.session_state.get('delete_file_checkbox', False):
            # 既存ファイル削除がチェックされた場合
            if current_file_path and os.path.exists(current_file_path):
                os.remove(current_file_path)
                st.success("既存の添付ファイルを削除しました。")
            file_path_to_save = None


        conn = sqlite3.connect('document_management.db')
        c = conn.cursor()

        if st.session_state['editing_document_id']:
            # 更新
            c.execute("UPDATE documents SET document_name = ?, issuer = ?, remarks = ?, file_path = ? WHERE document_id = ?",
                      (document_name, issuer, remarks, file_path_to_save, st.session_state['editing_document_id']))
            document_id = st.session_state['editing_document_id']
            st.success(f"文書番号 {document_id} を更新しました。")
        else:
            # 新規登録
            c.execute("INSERT INTO documents (document_name, issuer, remarks, file_path) VALUES (?, ?, ?, ?)",
                      (document_name, issuer, remarks, file_path_to_save))
            document_id = c.lastrowid
            st.success(f"文書 '{document_name}' を文書番号 {document_id} で登録しました。")
            st.session_state['current_document_id'] = document_id
            st.session_state['current_document_name'] = document_name

        # 閲覧先登録の処理
        # 既存の閲覧先を全て削除してから再登録
        c.execute("DELETE FROM document_access WHERE document_id = ?", (document_id,))
        for access in st.session_state.get('access_list', []):
            c.execute("INSERT INTO document_access (document_id, access_type, access_value) VALUES (?, ?, ?)",
                      (document_id, access['type'], access['value']))
        conn.commit()
        conn.close()
        st.success("閲覧先を保存しました。")
        
        # 処理完了後、編集モードを解除し、閲覧先リストをクリア
        st.session_state['editing_document_id'] = None
        st.session_state['access_list'] = [] # 保存後にセッションステートのリストをクリア
        st.session_state['current_document_id'] = None
        st.session_state['current_document_name'] = None
        st.session_state['current_doc_select_id'] = None # 選択状態もリセット
        st.rerun() # 画面をリフレッシュしてフォームをクリア

    st.markdown(f"---")
    st.subheader(f"閲覧先登録 (文書番号: {st.session_state.get('current_document_id', '未選択')}, 文書名: {st.session_state.get('current_document_name', '未選択')})")
    
    if st.session_state.get('current_document_id'): # 文書が選択されている場合のみ閲覧先登録を表示
        access_type = st.radio("閲覧先タイプを選択", ["職員番号別", "部署別", "委員会名等別"], key='access_type_radio')
        access_value = st.text_input(f"{access_type}を入力", key='access_value_input')

        if st.button("閲覧先を追加", key='add_access_button'):
            if access_type == "職員番号別":
                conn = sqlite3.connect('document_management.db')
                c = conn.cursor()
                c.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (access_value,))
                if not c.fetchone():
                    st.warning("指定された職員番号は存在しません。")
                    conn.close()
                    return
                conn.close()
                st.session_state.setdefault('access_list', []).append({'type': 'employee', 'value': access_value})
            elif access_type == "部署別":
                st.session_state.setdefault('access_list', []).append({'type': 'department', 'value': access_value})
            elif access_type == "委員会名等別":
                conn = sqlite3.connect('document_management.db')
                c = conn.cursor()
                c.execute("SELECT committee_name FROM committees WHERE committee_name = ?", (access_value,))
                if not c.fetchone():
                    st.warning("指定された委員会名等は存在しません。")
                    conn.close()
                    return
                conn.close()
                st.session_state.setdefault('access_list', []).append({'type': 'committee', 'value': access_value})
            st.success(f"{access_type}: {access_value} を追加しました。")

        if st.session_state.get('access_list'):
            st.write("登録済み閲覧先:")
            for i, access in enumerate(st.session_state['access_list']):
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.write(f"- {access['type']}: {access['value']}")
                with col2:
                    if st.button("削除", key=f"delete_access_{i}"):
                        st.session_state['access_list'].pop(i)
                        st.rerun() # リスト更新のため再描画

    else:
        st.info("文書を登録または選択すると、閲覧先を登録できます。")


# 文書詳細表示と閲覧ログ記録
def view_document_details(document_id, document_name, issuer, remarks, file_path):
    st.subheader(f"文書詳細: {document_name}")
    st.write(f"**文書番号:** {document_id}")
    st.write(f"**発行元:** {issuer}")
    st.write(f"**備考:** {remarks}")
    if file_path and os.path.exists(file_path):
        st.download_button(
            label="添付ファイルをダウンロード",
            data=open(file_path, "rb").read(),
            file_name=os.path.basename(file_path),
            mime="application/octet-stream"
        )
    elif file_path:
        st.warning("添付ファイルが見つかりません。")
    else:
        st.info("添付ファイルはありません。")

    # 閲覧ログの記録
    conn = sqlite3.connect('document_management.db')
    c = conn.cursor()
    employee_id = st.session_state.get('employee_id', 'guest') # ログインしていない場合は'guest'
    try:
        # 同じ文書を同じユーザーが短時間で複数回閲覧してもログが重複しないようにチェック
        # 例: 過去1分以内に同じ文書を閲覧している場合は記録しない
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        c.execute("SELECT COUNT(*) FROM view_logs WHERE document_id = ? AND employee_id = ? AND view_timestamp > ?",
                  (document_id, employee_id, one_minute_ago))
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO view_logs (document_id, employee_id) VALUES (?, ?)", (document_id, employee_id))
            conn.commit()
            st.success(f"文書 '{document_name}' の閲覧ログを記録しました。")
        else:
            st.info("この文書は最近閲覧されました。")
    except Exception as e:
        st.error(f"閲覧ログの記録中にエラーが発生しました: {e}")
    finally:
        conn.close()

# 文書一覧機能
def document_list():
    st.subheader("文書一覧")
    conn = sqlite3.connect('document_management.db')
    c = conn.cursor()

    current_employee_id = st.session_state.get('employee_id')
    employee_info = None
    if current_employee_id and current_employee_id != "guest": # 'guest' ではない場合に社員情報を取得
        c.execute("SELECT department, committee1, committee2, committee3, committee4, committee5 FROM employees WHERE employee_id = ?", (current_employee_id,))
        employee_info = c.fetchone()

    # 全ての文書を取得
    c.execute("SELECT document_id, document_name, issuer, remarks, file_path FROM documents")
    documents = c.fetchall()

    document_display_list = []
    for doc_id, doc_name, issuer, remarks, file_path in documents:
        c.execute("SELECT access_type, access_value FROM document_access WHERE document_id = ?", (doc_id,))
        accesses = c.fetchall()
        access_info = []
        for access_type, access_value in accesses:
            access_info.append(f"{access_type}:{access_value}")

        # 閲覧権限のチェック
        can_view = False
        if not accesses: # 閲覧先が登録されていない文書は全員閲覧可能とする
            can_view = True
        elif employee_info: # ログイン中の社員情報がある場合
            # 職員番号別参照
            if ('employee', current_employee_id) in accesses:
                can_view = True
            # 部署別参照
            if employee_info[0] and ('department', employee_info[0]) in accesses:
                can_view = True
            # 委員会名等別参照
            for i in range(1, 6):
                if employee_info[i] and ('committee', employee_info[i]) in accesses:
                    can_view = True
        # else: accesses が存在し、employee_info が None (guest または未ログイン) の場合、can_view は False のまま

        if can_view:
            document_display_list.append({
                "文書番号": doc_id,
                "文書名": doc_name,
                "発行元": issuer,
                "備考": remarks,
                "添付ファイル": os.path.basename(file_path) if file_path else "なし",
                "閲覧先": ", ".join(access_info) if access_info else "全員",
                "file_path_raw": file_path # 詳細表示用に元のパスを保持
            })
    conn.close()

    if document_display_list:
        st.write("### 文書一覧")
        # 列の幅を調整
        cols = st.columns([0.1, 0.2, 0.2, 0.3, 0.1, 0.1])
        headers = ["文書番号", "文書名", "発行元", "閲覧先", "添付", "操作"]
        for col, header in zip(cols, headers):
            col.write(f"**{header}**")

        # 各文書の行を表示
        for i, doc in enumerate(document_display_list):
            cols = st.columns([0.1, 0.2, 0.2, 0.3, 0.1, 0.1])
            with cols[0]:
                st.write(doc["文書番号"])
            with cols[1]:
                st.write(doc["文書名"])
            with cols[2]:
                st.write(doc["発行元"])
            with cols[3]:
                st.write(doc["閲覧先"])
            with cols[4]:
                st.write("あり" if doc["添付ファイル"] != "なし" else "なし")
            with cols[5]:
                # 閲覧ボタン
                # ボタンが押されたらview_document_detailsを直接呼び出す
                if st.button("閲覧", key=f"view_doc_{doc['文書番号']}"):
                    # セッションステートに選択された文書IDを保存し、再描画後に詳細を表示
                    st.session_state['selected_doc_for_view'] = doc["文書番号"]
                    st.rerun() # 画面を再描画して詳細表示をトリガー

        # 閲覧ボタンが押された場合にのみ詳細を表示
        if 'selected_doc_for_view' in st.session_state and st.session_state['selected_doc_for_view'] is not None:
            selected_doc_id = st.session_state['selected_doc_for_view']
            selected_doc = next((doc for doc in document_display_list if doc["文書番号"] == selected_doc_id), None)
            if selected_doc:
                st.markdown("---")
                view_document_details(
                    selected_doc["文書番号"],
                    selected_doc["文書名"],
                    selected_doc["発行元"],
                    selected_doc["備考"],
                    selected_doc["file_path_raw"]
                )
            # 詳細表示後、セッションステートをクリアして次回の閲覧に備える
            st.session_state['selected_doc_for_view'] = None

    else:
        st.info("表示できる文書がありません。")

# 社員登録機能
def employee_registration():
    st.subheader("社員登録")
    employee_id = st.text_input("職員番号")
    department = st.text_input("部署名")
    committee1 = st.text_input("委員会等名１")
    committee2 = st.text_input("委員会等名２")
    committee3 = st.text_input("委員会等名３")
    committee4 = st.text_input("委員会等名４")
    committee5 = st.text_input("委員会等名５")
    password = st.text_input("パスワード", type="password")

    if st.button("社員を登録"):
        hashed_password = hash_password(password)
        conn = sqlite3.connect('document_management.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO employees (employee_id, department, committee1, committee2, committee3, committee4, committee5, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (employee_id, department, committee1, committee2, committee3, committee4, committee5, hashed_password))
            conn.commit()
            st.success(f"社員 '{employee_id}' を登録しました。")
        except sqlite3.IntegrityError:
            st.error("この職員番号は既に登録されています。")
        conn.close()

# 社員一覧機能
def employee_list():
    st.subheader("社員一覧")
    conn = sqlite3.connect('document_management.db')
    c = conn.cursor()
    c.execute("SELECT employee_id, department, committee1, committee2, committee3, committee4, committee5 FROM employees")
    employees = c.fetchall()
    conn.close()

    if employees:
        employee_details = []
        for emp_id, dept, c1, c2, c3, c4, c5 in employees:
            employee_details.append({
                "職員番号": emp_id,
                "部署名": dept,
                "委員会等名１": c1,
                "委員会等名２": c2,
                "委員会等名３": c3,
                "委員会等名４": c4,
                "委員会等名５": c5
            })
        st.table(employee_details)
    else:
        st.info("登録されている社員がいません。")

# 委員会等登録機能
def committee_registration():
    st.subheader("委員会等登録")
    committee_name = st.text_input("委員会等名")

    if st.button("委員会等を登録"):
        conn = sqlite3.connect('document_management.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO committees (committee_name) VALUES (?)", (committee_name,))
            conn.commit()
            st.success(f"委員会等 '{committee_name}' を登録しました。")
        except sqlite3.IntegrityError:
            st.error("この委員会等名は既に登録されています。")
        conn.close()

# 委員会等一覧機能
def committee_list():
    st.subheader("委員会等一覧")
    conn = sqlite3.connect('document_management.db')
    c = conn.cursor()
    c.execute("SELECT committee_name FROM committees")
    committees = c.fetchall()
    conn.close()

    if committees:
        committee_details = [{"委員会等名": name[0]} for name in committees]
        st.table(committee_details)
    else:
        st.info("登録されている委員会等はありません。")

# 閲覧ログ一覧機能
def view_log_list():
    st.subheader("閲覧ログ一覧")
    conn = sqlite3.connect('document_management.db')
    c = conn.cursor()
    # document_name も取得するために JOIN を使用
    c.execute('''
        SELECT
            vl.log_id,
            d.document_name,
            vl.employee_id,
            vl.view_timestamp
        FROM view_logs vl
        JOIN documents d ON vl.document_id = d.document_id
        ORDER BY vl.view_timestamp DESC
    ''')
    logs = c.fetchall()
    conn.close()

    if logs:
        log_details = []
        for log_id, doc_name, emp_id, timestamp in logs:
            log_details.append({
                "ログID": log_id,
                "文書名": doc_name,
                "閲覧職員番号": emp_id,
                "閲覧日時": timestamp
            })
        st.table(log_details)
    else:
        st.info("閲覧ログはありません。")


# メインアプリケーション
def main():
    init_db()

    st.sidebar.title("メニュー")

    # セッションステートの初期化
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False # 初期状態は未ログイン
        st.session_state['employee_id'] = None
        st.session_state['show_access_registration'] = False
        st.session_state['access_list'] = []
        st.session_state['current_document_id'] = None
        st.session_state['current_document_name'] = None
        st.session_state['editing_document_id'] = None # 編集中の文書ID
        st.session_state['selected_doc_for_view'] = None # 閲覧ボタンで選択された文書ID
        st.session_state['current_page'] = "ログイン" # 初期表示ページをログイン画面に設定
        st.session_state['current_doc_select_id'] = None # 選択された文書オプションを追跡

    # ログイン画面
    if not st.session_state['logged_in']:
        st.title("文書管理システム ログイン")
        employee_id_input = st.text_input("職員番号", key="login_employee_id")
        password_input = st.text_input("パスワード", type="password", key="login_password")

        if st.button("ログイン"):
            conn = sqlite3.connect('document_management.db')
            c = conn.cursor()
            c.execute("SELECT password FROM employees WHERE employee_id = ?", (employee_id_input,))
            result = c.fetchone()
            conn.close()

            if result:
                hashed_password_in_db = result[0]
                if hashed_password_in_db == hash_password(password_input):
                    st.session_state['logged_in'] = True
                    st.session_state['employee_id'] = employee_id_input
                    st.session_state['current_page'] = "文書一覧" # ログイン成功後、文書一覧へ
                    st.success(f"職員番号 '{employee_id_input}' でログインしました。")
                    st.rerun()
                else:
                    st.error("パスワードが間違っています。")
            else:
                st.error("職員番号が見つかりません。")
        
        # ログイン画面から社員登録へのリンク
        st.markdown("---")
        st.info("アカウントをお持ちでない場合は、社員登録を行ってください。")
        if st.button("社員登録へ"):
            st.session_state['current_page'] = "社員登録"
            st.rerun()

    else: # ログイン済みの場合
        st.sidebar.write(f"現在のユーザー: {st.session_state['employee_id']}")

        # ログアウトボタン
        if st.sidebar.button("ログアウト"):
            st.session_state['logged_in'] = False
            st.session_state['employee_id'] = None
            st.session_state['current_page'] = "ログイン" # ログアウト後、ログイン画面へ
            st.session_state['editing_document_id'] = None
            st.session_state['access_list'] = []
            st.session_state['current_document_id'] = None
            st.session_state['current_document_name'] = None
            st.session_state['selected_doc_for_view'] = None
            st.session_state['current_doc_select_id'] = None # ログアウト時もリセット
            st.success("ログアウトしました。")
            st.rerun()

        menu_options = [
            "文書登録",
            "文書一覧",
            "社員登録",
            "社員一覧",
            "委員会等登録",
            "委員会等一覧",
            "閲覧ログ一覧"
        ]

        # サイドバーのラジオボタンでページを切り替える
        selected_menu = st.sidebar.radio("機能を選択", menu_options, index=menu_options.index(st.session_state['current_page']))

        # ラジオボタンで選択されたら、current_pageを更新
        if selected_menu != st.session_state['current_page']:
            st.session_state['current_page'] = selected_menu
            # ページ遷移時に編集状態をリセット
            st.session_state['editing_document_id'] = None
            st.session_state['access_list'] = []
            st.session_state['current_document_id'] = None
            st.session_state['current_document_name'] = None
            st.session_state['selected_doc_for_view'] = None # ページ遷移時に閲覧状態をリセット
            st.session_state['current_doc_select_id'] = None # ページ遷移時に選択状態をリセット
            st.rerun() # ページ遷移を反映

        # current_pageに基づいて適切な関数を呼び出す
        if st.session_state['current_page'] == "文書登録":
            document_registration()
        elif st.session_state['current_page'] == "文書一覧":
            document_list()
        elif st.session_state['current_page'] == "社員登録":
            employee_registration()
        elif st.session_state['current_page'] == "社員一覧":
            employee_list()
        elif st.session_state['current_page'] == "委員会等登録":
            committee_registration()
        elif st.session_state['current_page'] == "委員会等一覧":
            committee_list()
        elif st.session_state['current_page'] == "閲覧ログ一覧":
            view_log_list()

if __name__ == "__main__":
    main()
