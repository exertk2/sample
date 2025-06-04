import streamlit as st
from datetime import datetime
import pandas as pd

# --- 初期設定 ---
# 事前に定義されたユーザー (本番環境ではもっと安全な方法で管理してください)
# この辞書はアプリケーションの起動時に初期ユーザーを設定するために使用します。
# 実行中にユーザーが追加されると、st.session_state.registered_users が更新されます。
INITIAL_USERS = {
    "admin": "password123",
    "user1": "testuser1",
    "user2": "testuser2"
}

# アプリのセッション状態の初期化
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
if 'documents' not in st.session_state:
    # 'access' はユーザー名のリストになります
    st.session_state.documents = [] 
    # {'id': int, 'name': str, 'description': str, 'uploader': str, 'filename': str, 
    #  'data': bytes, 'uploaded_at': datetime, 'access': list[str]}
if 'logs' not in st.session_state:
    st.session_state.logs = [] 
    # {'timestamp': datetime, 'user': str, 'action': str, 'document_name': str}
if 'doc_id_counter' not in st.session_state:
    st.session_state.doc_id_counter = 0
if 'registered_users' not in st.session_state:
    # 実行中のユーザー情報を管理。初期ユーザーで初期化。
    st.session_state.registered_users = INITIAL_USERS.copy()

# --- ユーティリティ関数 ---
def add_log(user, action, document_name):
    """閲覧ログを追加する関数"""
    st.session_state.logs.append({
        'timestamp': datetime.now(),
        'user': user,
        'action': action,
        'document_name': document_name
    })

def get_next_doc_id():
    """新しいドキュメントIDを生成する関数"""
    st.session_state.doc_id_counter += 1
    return st.session_state.doc_id_counter

# --- ログイン処理 ---
def login_page():
    """ログインページを表示する関数"""
    st.header("ログイン")
    username = st.text_input("ユーザー名")
    password = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        # st.session_state.registered_users を使用して認証
        if username in st.session_state.registered_users and st.session_state.registered_users[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"{username}としてログインしました。")
            add_log(username, "ログイン", "-")
            st.rerun() 
        else:
            st.error("ユーザー名またはパスワードが正しくありません。")

# --- メインアプリ ---
def main_app():
    """メインアプリケーションのUIを表示する関数"""
    st.sidebar.header(f"ようこそ、{st.session_state.username}さん")
    if st.sidebar.button("ログアウト"):
        add_log(st.session_state.username, "ログアウト", "-")
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    # ユーザーの役割に基づいてメニューを動的に変更
    menu = ["文書一覧・閲覧", "文書登録"]
    if st.session_state.username == 'admin':
        menu.extend(["ユーザー登録", "ユーザー一覧"])
    menu.append("閲覧ログ確認")
    
    choice = st.sidebar.selectbox("メニュー", menu)

    if choice == "文書一覧・閲覧":
        display_documents()
    elif choice == "文書登録":
        upload_document_page()
    elif choice == "ユーザー登録" and st.session_state.username == 'admin':
        user_registration_page()
    elif choice == "ユーザー一覧" and st.session_state.username == 'admin':
        display_users_page()
    elif choice == "閲覧ログ確認":
        display_logs()
    elif choice in ["ユーザー登録", "ユーザー一覧"] and st.session_state.username != 'admin':
        st.error("この機能へのアクセス権限がありません。")


def user_registration_page():
    """新しいユーザーを登録するページ（管理者のみ）"""
    st.subheader("ユーザー登録")
    if st.session_state.username != 'admin':
        st.error("管理者のみがユーザーを登録できます。")
        return

    with st.form("user_registration_form"):
        new_username = st.text_input("新しいユーザー名")
        new_password = st.text_input("新しいパスワード", type="password")
        confirm_password = st.text_input("パスワード確認", type="password")
        submitted = st.form_submit_button("登録")

        if submitted:
            if not new_username or not new_password:
                st.warning("ユーザー名とパスワードを入力してください。")
            elif new_password != confirm_password:
                st.error("パスワードが一致しません。")
            elif new_username in st.session_state.registered_users:
                st.error("このユーザー名は既に使用されています。")
            else:
                st.session_state.registered_users[new_username] = new_password
                add_log(st.session_state.username, "ユーザー登録", new_username)
                st.success(f"ユーザー「{new_username}」を登録しました。")

def display_users_page():
    """登録されているユーザーの一覧を表示するページ（管理者のみ）"""
    st.subheader("ユーザー一覧")
    if st.session_state.username != 'admin':
        st.error("管理者のみがユーザー一覧を閲覧できます。")
        return

    if not st.session_state.registered_users:
        st.info("登録されているユーザーはいません。")
        return

    users_data = [{"ユーザー名": user} for user in st.session_state.registered_users.keys()]
    df_users = pd.DataFrame(users_data)
    st.dataframe(df_users, use_container_width=True)


def upload_document_page():
    """文書登録ページを表示する関数"""
    st.subheader("文書登録")
    doc_name = st.text_input("文書名*", help="必須項目です。")
    doc_description = st.text_area("説明")
    uploaded_file = st.file_uploader("PDFファイルをアップロード", type="pdf")
    
    # 閲覧権限の設定: 登録ユーザーから複数選択
    all_users = list(st.session_state.registered_users.keys())
    # アップロード者自身はデフォルトで選択状態にしない（選択されなければアクセス権が付与される）
    # adminは常にアクセス可能なので、選択肢に含める必要はないが、含めても問題はない
    
    allowed_users = st.multiselect(
        "閲覧を許可するユーザーを選択 (複数選択可):",
        options=all_users,
        help="選択しない場合、アップロード者と管理者のみが閲覧できます。"
    )

    if st.button("登録"):
        if not doc_name:
            st.warning("文書名を入力してください。")
        elif uploaded_file is not None:
            file_data = uploaded_file.read()
            doc_id = get_next_doc_id()
            
            # アクセスリストが空の場合、アップロード者のみに設定することも検討できるが、
            # ここでは選択されたユーザーのみとする。アップロード者と管理者は常にアクセス可能。
            access_list = list(set(allowed_users)) # 重複除去

            new_document = {
                'id': doc_id,
                'name': doc_name,
                'description': doc_description,
                'uploader': st.session_state.username,
                'filename': uploaded_file.name,
                'data': file_data,
                'uploaded_at': datetime.now(),
                'access': access_list 
            }
            st.session_state.documents.append(new_document)
            add_log(st.session_state.username, "文書登録", doc_name)
            st.success(f"文書「{doc_name}」を登録しました。")
        else:
            st.warning("PDFファイルをアップロードしてください。")

def display_documents():
    """文書一覧を表示し、ダウンロード機能を提供する関数"""
    st.subheader("文書一覧")

    if not st.session_state.documents:
        st.info("登録されている文書はありません。")
        return

    search_term = st.text_input("文書名で検索")

    display_docs = []
    current_user = st.session_state.username
    for doc in st.session_state.documents:
        can_view = False
        # 1. 管理者は常に閲覧可能
        if current_user == 'admin':
            can_view = True
        # 2. アップロード者自身は常に閲覧可能
        elif doc['uploader'] == current_user:
            can_view = True
        # 3. アクセスリストに含まれているユーザーは閲覧可能
        elif current_user in doc['access']:
            can_view = True
        
        if can_view:
            if search_term.lower() in doc['name'].lower():
                display_docs.append(doc)
    
    if not display_docs:
        st.info("条件に合う文書はありません。")
        return

    docs_for_df = []
    for doc in display_docs:
        # アクセス許可ユーザーの表示名を整形
        access_display = []
        if doc['uploader'] not in doc['access'] and 'admin' not in doc['access']: # アップローダーとadminは暗黙の権限
             access_display.extend(doc['access'])
        elif doc['uploader'] in doc['access'] and 'admin' not in doc['access']:
             access_display.extend(u for u in doc['access'] if u != doc['uploader'])
        elif doc['uploader'] not in doc['access'] and 'admin' in doc['access']:
             access_display.extend(u for u in doc['access'] if u != 'admin')
        else: #両方含まれる場合
             access_display.extend(u for u in doc['access'] if u not in [doc['uploader'], 'admin'])


        explicit_users = ", ".join(sorted(list(set(doc['access'])))) if doc['access'] else "アップロード者のみ"
        if not doc['access'] and doc['uploader'] != 'admin':
            access_str = f"アップロード者 ({doc['uploader']})"
        elif not doc['access'] and doc['uploader'] == 'admin':
             access_str = "管理者のみ"
        else:
            access_str = ", ".join(sorted(list(set(doc['access']))))
        
        # より正確な表示
        granted_to = sorted(list(set(doc['access'])))
        display_access = []
        if doc['uploader'] == current_user and current_user not in granted_to: #自分がアップローダー
             pass # 表示上は明示的な権限のみ
        
        final_access_display = []
        if doc['uploader'] not in granted_to: # アップローダーは暗黙の権限
            final_access_display.append(f"{doc['uploader']} (アップロード者)")
        
        final_access_display.extend(granted_to)
        if 'admin' not in granted_to and doc['uploader'] != 'admin': # adminは暗黙の権限
             final_access_display.append("admin (管理者)")
        
        # 重複を除きソート
        final_access_display = sorted(list(set(final_access_display)))


        docs_for_df.append({
            "ID": doc['id'],
            "文書名": doc['name'],
            "説明": doc['description'],
            "アップロード者": doc['uploader'],
            "ファイル名": doc['filename'],
            "登録日時": doc['uploaded_at'].strftime("%Y-%m-%d %H:%M"),
            "閲覧許可": ", ".join(granted_to) if granted_to else doc['uploader'] # 表示用
        })
    
    df = pd.DataFrame(docs_for_df)
    
    if not df.empty:
        st.dataframe(df.set_index("ID"), use_container_width=True)

        st.markdown("---")
        st.subheader("文書ダウンロード")
        
        doc_options = {doc['id']: f"{doc['name']} (ID: {doc['id']})" for doc in display_docs}
        
        if not doc_options:
            st.write("ダウンロード可能な文書がありません。")
            return

        selected_doc_id = st.selectbox("ダウンロードする文書を選択してください:", 
                                       options=list(doc_options.keys()), 
                                       format_func=lambda x: doc_options[x],
                                       key=f"download_select_{datetime.now().timestamp()}") # Ensure unique key for selectbox

        selected_doc_to_download = next((doc for doc in display_docs if doc['id'] == selected_doc_id), None)

        if selected_doc_to_download:
            # ダウンロードボタンのコールバックでログを記録
            def record_download_log():
                # このコールバックが呼ばれた時点でダウンロードが開始される（または直後）
                # ただし、ユーザーが実際にファイルを保存したかは保証できない
                add_log(st.session_state.username, "文書ダウンロード", selected_doc_to_download['name'])
                st.toast(f"「{selected_doc_to_download['name']}」のダウンロードログを記録しました。")


            st.download_button(
                label=f"「{selected_doc_to_download['name']}」をダウンロード",
                data=selected_doc_to_download['data'],
                file_name=selected_doc_to_download['filename'],
                mime="application/pdf",
                on_click=record_download_log, # on_clickでログ記録関数を呼び出し
                key=f"download_btn_{selected_doc_id}_{datetime.now().timestamp()}" # Ensure unique key for button
            )
        else:
            st.write("選択された文書が見つかりません。")
    else:
        st.info("表示できる文書がありません。")


def display_logs():
    """閲覧ログを表示する関数"""
    st.subheader("閲覧ログ")
    if not st.session_state.logs:
        st.info("ログはありません。")
        return

    log_df = pd.DataFrame(st.session_state.logs)
    if not log_df.empty:
        log_df['timestamp'] = pd.to_datetime(log_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        log_df = log_df[['timestamp', 'user', 'action', 'document_name']]
        log_df = log_df.sort_values(by='timestamp', ascending=False)
        st.dataframe(log_df.reset_index(drop=True), use_container_width=True)
    else:
        st.info("ログデータが空です。")


# --- アプリケーションの実行フロー ---
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
