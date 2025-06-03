import streamlit as st
import sqlite3
import hashlib

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

    # 文書テーブルの作成
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT,
            issuer TEXT,
            remarks TEXT
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

    conn.commit()
    conn.close()

# パスワードのハッシュ化
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ログイン機能
def login():
    st.subheader("ログイン")
    employee_id = st.text_input("職員番号")
    password = st.text_input("パスワード", type="password")

    if st.button("ログイン"):
        conn = sqlite3.connect('document_management.db')
        c = conn.cursor()
        c.execute("SELECT password FROM employees WHERE employee_id = ?", (employee_id,))
        result = c.fetchone()
        conn.close()

        if result and result[0] == hash_password(password):
            st.session_state['logged_in'] = True
            st.session_state['employee_id'] = employee_id
            st.success("ログインしました")
            st.rerun()
        else:
            st.error("職員番号またはパスワードが間違っています")

# 文書登録機能
def document_registration():
    st.subheader("文書登録")
    document_name = st.text_input("文書名")
    issuer = st.text_input("発行元")
    remarks = st.text_area("備考")

    if st.button("文書を登録"):
        conn = sqlite3.connect('document_management.db')
        c = conn.cursor()
        c.execute("INSERT INTO documents (document_name, issuer, remarks) VALUES (?, ?, ?)",
                  (document_name, issuer, remarks))
        document_id = c.lastrowid
        conn.commit()
        conn.close()
        st.success(f"文書 '{document_name}' を文書番号 {document_id} で登録しました。")
        st.session_state['current_document_id'] = document_id
        st.session_state['current_document_name'] = document_name
        st.session_state['show_access_registration'] = True

    if st.session_state.get('show_access_registration', False):
        st.markdown(f"---")
        st.subheader(f"閲覧先登録 (文書番号: {st.session_state['current_document_id']}, 文書名: {st.session_state['current_document_name']})")

        access_type = st.radio("閲覧先タイプを選択", ["職員番号別", "部署別", "委員会名等別"])
        access_value = st.text_input(f"{access_type}を入力")

        if st.button("閲覧先を追加"):
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
                st.write(f"- {access['type']}: {access['value']}")
            if st.button("閲覧先を確定して保存"):
                conn = sqlite3.connect('document_management.db')
                c = conn.cursor()
                for access in st.session_state['access_list']:
                    c.execute("INSERT INTO document_access (document_id, access_type, access_value) VALUES (?, ?, ?)",
                              (st.session_state['current_document_id'], access['type'], access['value']))
                conn.commit()
                conn.close()
                st.success("全ての閲覧先を保存しました。")
                st.session_state['show_access_registration'] = False
                st.session_state['access_list'] = [] # リストをクリア

# 文書一覧機能
def document_list():
    st.subheader("文書一覧")
    conn = sqlite3.connect('document_management.db')
    c = conn.cursor()

    # ログイン中のユーザーの情報を取得
    current_employee_id = st.session_state.get('employee_id')
    employee_info = None
    if current_employee_id:
        c.execute("SELECT department, committee1, committee2, committee3, committee4, committee5 FROM employees WHERE employee_id = ?", (current_employee_id,))
        employee_info = c.fetchone()

    # 全ての文書を取得
    c.execute("SELECT document_id, document_name, issuer, remarks FROM documents")
    documents = c.fetchall()

    # 各文書の閲覧先情報を取得
    document_details = []
    for doc_id, doc_name, issuer, remarks in documents:
        c.execute("SELECT access_type, access_value FROM document_access WHERE document_id = ?", (doc_id,))
        accesses = c.fetchall()
        access_info = []
        for access_type, access_value in accesses:
            access_info.append(f"{access_type}:{access_value}")

        # 閲覧権限のチェック
        can_view = False
        if not accesses: # 閲覧先が登録されていない文書は全員閲覧可能とする
            can_view = True
        elif employee_info:
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
        else: # ログインしていない場合は閲覧不可
            can_view = False

        if can_view:
            document_details.append({
                "文書番号": doc_id,
                "文書名": doc_name,
                "発行元": issuer,
                "備考": remarks,
                "閲覧先": ", ".join(access_info) if access_info else "全員"
            })
    conn.close()

    if document_details:
        st.table(document_details)
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


# メインアプリケーション
def main():
    init_db()

    st.sidebar.title("メニュー")

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['show_access_registration'] = False
        st.session_state['access_list'] = []

    if not st.session_state['logged_in']:
        login()
    else:
        st.sidebar.write(f"ログイン中: {st.session_state['employee_id']}")
        if st.sidebar.button("ログアウト"):
            st.session_state['logged_in'] = False
            st.session_state['employee_id'] = None
            st.session_state['show_access_registration'] = False
            st.session_state['access_list'] = []
            st.success("ログアウトしました")
            st.rerun()

        menu_options = [
            "文書登録",
            "文書一覧",
            "社員登録",
            "社員一覧",
            "委員会等登録",
            "委員会等一覧"
        ]
        choice = st.sidebar.radio("機能を選択", menu_options)

        if choice == "文書登録":
            document_registration()
        elif choice == "文書一覧":
            document_list()
        elif choice == "社員登録":
            employee_registration()
        elif choice == "社員一覧":
            employee_list()
        elif choice == "委員会等登録":
            committee_registration()
        elif choice == "委員会等一覧":
            committee_list()

if __name__ == "__main__":
    main()
