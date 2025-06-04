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
    """閲覧ログを追加する関数 (文書ダウンロード専用に変更)"""
    if action == "文書ダウンロード": # ログ記録対象をダウンロードのみに限定
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
        if username in st.session_state.registered_users and st.session_state.registered_users[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"{username}としてログインしました。")
            # add_log(username, "ログイン", "-") # ログインログは記録しない
            st.rerun() 
        else:
            st.error("ユーザー名またはパスワードが正しくありません。")

# --- メインアプリ ---
def main_app():
    """メインアプリケーションのUIを表示する関数"""
    st.sidebar.header(f"ようこそ、{st.session_state.username}さん")
    if st.sidebar.button("ログアウト"):
        # add_log(st.session_state.username, "ログアウト", "-") # ログアウトログは記録しない
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

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
                # add_log(st.session_state.username, "ユーザー登録", new_username) # ユーザー登録ログは記録しない
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
    
    all_users = list(st.session_state.registered_users.keys())
    
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
            access_list = list(set(allowed_users)) 

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
            # add_log(st.session_state.username, "文書登録", doc_name) # 文書登録ログは記録しない
            st.success(f"文書「{doc_name}」を登録しました。")
        else:
            st.warning("PDFファイルをアップロードしてください。")

def display_documents():
    """文書一覧を表示し、ダウンロード機能を提供する関数"""
    st.subheader("文書一覧")

    if not st.session_state.documents:
        st.info("登録されている文書はありません。")
        return

    search_term = st.text_input("文書名で検索", key="doc_list_search")

    display_docs_for_list = []
    current_user = st.session_state.username
    for doc in st.session_state.documents:
        can_view = False
        if current_user == 'admin':
            can_view = True
        elif doc['uploader'] == current_user:
            can_view = True
        elif current_user in doc['access']:
            can_view = True
        
        if can_view:
            if search_term.lower() in doc['name'].lower():
                display_docs_for_list.append(doc)
    
    if not display_docs_for_list:
        st.info("条件に合う文書はありません。")
        # return # ここでreturnするとダウンロードセクションが表示されないのでコメントアウト

    docs_for_df = []
    for doc in display_docs_for_list:
        # 閲覧可能な全ユーザーをリストアップ
        viewable_by = set(doc['access']) # 明示的に許可されたユーザー
        viewable_by.add(doc['uploader'])    # アップロード者
        viewable_by.add('admin')            # 管理者
        permission_str = ", ".join(sorted(list(viewable_by)))

        docs_for_df.append({
            "ID": doc['id'],
            "文書名": doc['name'],
            "説明": doc['description'],
            "アップロード者": doc['uploader'],
            "ファイル名": doc['filename'],
            "登録日時": doc['uploaded_at'].strftime("%Y-%m-%d %H:%M"),
            "閲覧許可": permission_str
        })
    
    df = pd.DataFrame(docs_for_df)
    
    if not df.empty:
        st.dataframe(df.set_index("ID"), use_container_width=True)
    elif not search_term and not st.session_state.documents: # 初期状態で文書がない場合
         pass # 上のst.infoでメッセージ表示済み
    elif search_term: # 検索したが結果がない場合
        st.info("検索条件に合う文書は一覧にありません。")


    st.markdown("---")
    st.subheader("文書ダウンロード")

    # ダウンロードセクション用のフィルタ
    download_filter_text = st.text_input(
        "ダウンロード対象をフィルタリング (文書名, 説明, ファイル名):", 
        key="download_filter"
    )

    # ダウンロード可能な文書は、一覧に表示されている文書（display_docs_for_list）を元にする
    docs_for_download_selection = []
    if not download_filter_text:
        docs_for_download_selection = display_docs_for_list
    else:
        for doc in display_docs_for_list: # 既に閲覧権限チェック済みのリストからフィルタ
            if (download_filter_text.lower() in doc['name'].lower() or
                download_filter_text.lower() in doc['description'].lower() or
                download_filter_text.lower() in doc['filename'].lower()):
                docs_for_download_selection.append(doc)

    if not docs_for_download_selection:
        if display_docs_for_list: # フィルタによって候補がなくなった場合
             st.write("フィルタ条件に合うダウンロード可能な文書がありません。")
        elif not st.session_state.documents : #そもそも文書がない
             st.write("ダウンロード可能な文書がありません。")
        # else:  一覧に表示される文書がないが、display_docs_for_listが空ではないケースは通常ない
        return


    doc_options = {doc['id']: f"{doc['name']} (ID: {doc['id']})" for doc in docs_for_download_selection}
    
    if not doc_options: #念のため
        st.write("ダウンロード可能な文書が選択肢にありません。")
        return

    selected_doc_id = st.selectbox("ダウンロードする文書を選択してください:", 
                                   options=list(doc_options.keys()), 
                                   format_func=lambda x: doc_options.get(x, "不明な文書"), # .getで存在しないキーに対応
                                   key=f"download_select_{datetime.now().timestamp()}") 

    selected_doc_to_download = next((doc for doc in docs_for_download_selection if doc['id'] == selected_doc_id), None)

    if selected_doc_to_download:
        def record_download_log():
            add_log(st.session_state.username, "文書ダウンロード", selected_doc_to_download['name'])
            st.toast(f"「{selected_doc_to_download['name']}」のダウンロードログを記録しました。")

        st.download_button(
            label=f"「{selected_doc_to_download['name']}」をダウンロード",
            data=selected_doc_to_download['data'],
            file_name=selected_doc_to_download['filename'],
            mime="application/pdf",
            on_click=record_download_log,
            key=f"download_btn_{selected_doc_id}_{datetime.now().timestamp()}" 
        )
    elif doc_options : # doc_optionsはあるが、selected_doc_to_downloadが見つからない場合（通常発生しにくい）
        st.write("選択された文書が見つかりません。")


def display_logs():
    """閲覧ログを表示する関数"""
    st.subheader("閲覧ログ (文書ダウンロードのみ)")
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
        st.info("ログデータが空です。") # フィルタリングされた結果、ログがない場合も含む


# --- アプリケーションの実行フロー ---
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
