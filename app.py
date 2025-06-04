import streamlit as st
from datetime import datetime
import pandas as pd

# --- 初期設定 ---
# 事前に定義されたユーザー (本番環境ではもっと安全な方法で管理してください)
VALID_USERS = {
    "admin": "password123",
    "user1": "testuser1",
    "user2": "testuser2"
}

# アプリのセッション状態の初期化
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
if 'documents' not in st.session_state:
    st.session_state.documents = [] # {'id': int, 'name': str, 'description': str, 'uploader': str, 'filename': str, 'data': bytes, 'uploaded_at': datetime, 'access': str ('public' or 'private')}
if 'logs' not in st.session_state:
    st.session_state.logs = [] # {'timestamp': datetime, 'user': str, 'action': str, 'document_name': str}
if 'doc_id_counter' not in st.session_state:
    st.session_state.doc_id_counter = 0

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
        if username in VALID_USERS and VALID_USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"{username}としてログインしました。")
            add_log(username, "ログイン", "-")
            st.rerun() # ページを再読み込みしてメインアプリを表示
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
        # セッション内のドキュメントやログもクリアする場合はここに追加
        # st.session_state.documents = []
        # st.session_state.logs = []
        # st.session_state.doc_id_counter = 0
        st.rerun()

    menu = ["文書一覧・閲覧", "文書登録", "閲覧ログ確認"]
    choice = st.sidebar.selectbox("メニュー", menu)

    if choice == "文書一覧・閲覧":
        display_documents()
    elif choice == "文書登録":
        upload_document_page()
    elif choice == "閲覧ログ確認":
        display_logs()

def upload_document_page():
    """文書登録ページを表示する関数"""
    st.subheader("文書登録")
    doc_name = st.text_input("文書名*", help="必須項目です。")
    doc_description = st.text_area("説明")
    uploaded_file = st.file_uploader("PDFファイルをアップロード", type="pdf")
    
    # 閲覧権限の設定 (簡易版)
    # 'public': 全員が閲覧可能
    # 'private': アップロード者のみ閲覧可能 (今回はログインユーザーで判定)
    access_level = st.radio("公開範囲:", ('公開 (全員に表示)', '非公開 (自分のみ)'), index=0)
    access_setting = 'public' if access_level == '公開 (全員に表示)' else 'private'

    if st.button("登録"):
        if not doc_name:
            st.warning("文書名を入力してください。")
        elif uploaded_file is not None:
            file_data = uploaded_file.read()
            doc_id = get_next_doc_id()
            new_document = {
                'id': doc_id,
                'name': doc_name,
                'description': doc_description,
                'uploader': st.session_state.username,
                'filename': uploaded_file.name,
                'data': file_data,
                'uploaded_at': datetime.now(),
                'access': access_setting
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

    # フィルター機能（簡易版）
    search_term = st.text_input("文書名で検索")

    display_docs = []
    for doc in st.session_state.documents:
        # 閲覧権限のチェック
        can_view = False
        if doc['access'] == 'public':
            can_view = True
        elif doc['access'] == 'private' and doc['uploader'] == st.session_state.username:
            can_view = True
        
        # 管理者は全ての非公開文書も閲覧可能 (今回はadminユーザーのみ)
        if st.session_state.username == 'admin' and doc['access'] == 'private':
             can_view = True


        if can_view:
            if search_term.lower() in doc['name'].lower():
                display_docs.append(doc)
    
    if not display_docs:
        st.info("条件に合う文書はありません。")
        return

    # DataFrameで見やすく表示
    docs_for_df = []
    for doc in display_docs:
        docs_for_df.append({
            "ID": doc['id'],
            "文書名": doc['name'],
            "説明": doc['description'],
            "アップロード者": doc['uploader'],
            "ファイル名": doc['filename'],
            "登録日時": doc['uploaded_at'].strftime("%Y-%m-%d %H:%M"),
            "公開範囲": "公開" if doc['access'] == 'public' else "非公開"
        })
    
    df = pd.DataFrame(docs_for_df)
    
    if not df.empty:
        st.dataframe(df.set_index("ID"), use_container_width=True)

        st.markdown("---")
        st.subheader("文書ダウンロード")
        
        # ダウンロードする文書を選択
        # display_docsの中からIDと名前のリストを作成
        doc_options = {doc['id']: f"{doc['name']} (ID: {doc['id']})" for doc in display_docs}
        
        if not doc_options:
            st.write("ダウンロード可能な文書がありません。")
            return

        selected_doc_id = st.selectbox("ダウンロードする文書を選択してください:", 
                                       options=list(doc_options.keys()), 
                                       format_func=lambda x: doc_options[x])

        selected_doc_to_download = next((doc for doc in display_docs if doc['id'] == selected_doc_id), None)

        if selected_doc_to_download:
            st.download_button(
                label=f"「{selected_doc_to_download['name']}」をダウンロード",
                data=selected_doc_to_download['data'],
                file_name=selected_doc_to_download['filename'],
                mime="application/pdf"
            )
            # ダウンロードボタンが押されたことを検知するのはStreamlitでは直接的でないため、
            # ここではボタンが表示されたらログを記録する（厳密なダウンロード検知ではない）
            if st.session_state.get(f"download_log_recorded_{selected_doc_id}", False) is False:
                 # ログがまだ記録されていない場合のみ記録
                 # このロジックはボタンが押された瞬間ではなく、再レンダリング時に評価されるため、
                 # 完璧なダウンロード検知にはなりません。
                 # より正確な検知にはコールバックや複雑な状態管理が必要です。
                 # 今回は簡易的に、ボタンが表示されたらログを追加します。
                 pass # 実際のダウンロード検知は難しいため、ここではログ追加を保留

            # よりシンプルなアプローチ：ダウンロードボタンが押されたことを明示的にユーザーにアクションさせる
            # 例えば、ダウンロード後に「ダウンロードしました」ボタンを押させるなど。
            # 今回は、ダウンロードボタンの表示をもって「閲覧試行」とみなすこともできます。
            # ログのタイミングについては検討が必要です。
            # 一旦、ダウンロードボタンが押されたことを検知できないので、
            # 「閲覧」操作としてログを残すのは、文書詳細ページなどに遷移した場合が適切かもしれません。
            # ここでは、ダウンロードボタンが押されたことを直接検知できないため、
            # ログは「文書一覧表示」などの粒度にするか、別途工夫が必要です。
            # 今回は、ダウンロードボタンが押されたらログを追加する、という挙動は実装が難しいため、
            # ログは「文書登録」「ログイン」「ログアウト」に限定します。
            # もしダウンロードのログが必要な場合は、ダウンロード後に確認ボタンを設けるなどの工夫が必要です。
            # ここでは、ダウンロードボタンが押されたことを検知してログを追加する機能は省略します。
            # 代わりに、閲覧ログ確認画面で手動でログを追加するような機能も考えられます。

            # ログ追加のタイミングについて：
            # st.download_button は押されたイベントを直接返さないため、
            # ダウンロード操作のログを正確に取るのは難しいです。
            # 一つの回避策として、ダウンロードボタンがクリックされたら特定のセッション状態を更新し、
            # 次の再描画でそれを検知してログを記録する方法がありますが、やや複雑になります。
            # 今回は、ダウンロード操作のログは省略し、他の操作ログに注力します。
            # もし必要であれば、ダウンロード後に「ログを記録」ボタンを別途設けるなどのUI変更を検討します。
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
    log_df['timestamp'] = pd.to_datetime(log_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    log_df = log_df[['timestamp', 'user', 'action', 'document_name']]
    log_df = log_df.sort_values(by='timestamp', ascending=False)
    st.dataframe(log_df, use_container_width=True)

# --- アプリケーションの実行フロー ---
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
