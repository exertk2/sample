import streamlit as st
import pandas as pd
from datetime import datetime
import uuid # To generate unique IDs for requests
import sqlite3 # For database interaction

# --- Database Configuration ---
DB_NAME = "purchase_requests.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Access columns by name
    return conn

def init_db():
    """Initializes the database and creates the 'requests' table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            申請ID TEXT PRIMARY KEY,
            申請日 TEXT,
            申請者 TEXT,
            部署 TEXT,
            件名 TEXT,
            品名 TEXT,
            数量 INTEGER,
            単価 REAL,
            合計金額 REAL,
            購入理由 TEXT,
            希望納期 TEXT,
            ステータス TEXT,
            承認者コメント TEXT,
            承認日 TEXT,
            ファイル名 TEXT
        )
    """)
    conn.commit()
    conn.close()

# Call init_db at the start of the script to ensure the table exists
init_db()

# --- Helper Functions for Database Operations ---
def add_request_to_db(request_data):
    """Adds a new purchase request to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO requests (申請ID, 申請日, 申請者, 部署, 件名, 品名, 数量, 単価, 合計金額, 購入理由, 希望納期, ステータス, 承認者コメント, 承認日, ファイル名)
            VALUES (:申請ID, :申請日, :申請者, :部署, :件名, :品名, :数量, :単価, :合計金額, :購入理由, :希望納期, :ステータス, :承認者コメント, :承認日, :ファイル名)
        """, {
            "申請ID": request_data["申請ID"],
            "申請日": request_data["申請日"].isoformat() if isinstance(request_data["申請日"], datetime) else request_data["申請日"],
            "申請者": request_data["申請者"],
            "部署": request_data["部署"],
            "件名": request_data["件名"],
            "品名": request_data["品名"],
            "数量": request_data["数量"],
            "単価": request_data["単価"],
            "合計金額": request_data["合計金額"],
            "購入理由": request_data["購入理由"],
            "希望納期": request_data["希望納期"].isoformat() if isinstance(request_data["希望納期"], datetime) else request_data["希望納期"],
            "ステータス": request_data["ステータス"],
            "承認者コメント": request_data["承認者コメント"],
            "承認日": request_data["承認日"].isoformat() if pd.notna(request_data["承認日"]) and isinstance(request_data["承認日"], datetime) else None,
            "ファイル名": request_data["ファイル名"]
        })
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"データベースエラー (登録時): {e}")
    finally:
        conn.close()

def update_request_in_db(request_id, status, comment, approval_date):
    """Updates the status, comment, and approval date of a request in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE requests
            SET ステータス = ?, 承認者コメント = ?, 承認日 = ?
            WHERE 申請ID = ?
        """, (status, comment, approval_date.isoformat() if pd.notna(approval_date) and isinstance(approval_date, datetime) else None, request_id))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"データベースエラー (更新時): {e}")
    finally:
        conn.close()

def get_all_requests_from_db():
    """Retrieves all purchase requests from the database and returns them as a DataFrame."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM requests", conn)
        # Convert date strings back to datetime objects
        if not df.empty:
            for col in ["申請日", "希望納期", "承認日"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce') # errors='coerce' will turn unparseable to NaT
        return df
    except sqlite3.Error as e:
        st.error(f"データベースエラー (読み込み時): {e}")
        return pd.DataFrame(columns=[ # Return empty df on error to prevent crashes
            "申請ID", "申請日", "申請者", "部署", "件名", "品名", "数量", "単価", "合計金額",
            "購入理由", "希望納期", "ステータス", "承認者コメント", "承認日", "ファイル名"
        ])
    finally:
        conn.close()

def delete_all_requests_from_db():
    """Deletes all requests from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM requests")
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"データベースエラー (全削除時): {e}")
    finally:
        conn.close()

# Set page configuration
st.set_page_config(layout="wide", page_title="購入伺いシステム", page_icon="📝")

# --- Initialize session state for UI elements (user_role) ---
if 'user_role' not in st.session_state:
    st.session_state.user_role = "申請者" # Default role

# --- Helper Functions (UI) ---
def generate_request_id():
    """Generates a unique request ID."""
    return str(uuid.uuid4())

def format_display_df(df):
    """Formats the DataFrame for better display."""
    if df.empty:
        return df

    display_df = df.copy()
    # Format date columns if they exist
    if "申請日" in display_df.columns:
        display_df["申請日"] = pd.to_datetime(display_df["申請日"], errors='coerce').dt.strftime('%Y-%m-%d')
    if "希望納期" in display_df.columns:
        display_df["希望納期"] = pd.to_datetime(display_df["希望納期"], errors='coerce').dt.strftime('%Y-%m-%d')
    if "承認日" in display_df.columns:
        # Handle NaT for '承認日' before formatting
        display_df["承認日"] = display_df["承認日"].apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d %H:%M') if pd.notna(x) else '')

    # Reorder columns for display
    column_order = [
        "申請ID", "ステータス", "申請日", "申請者", "部署", "件名", "合計金額",
        "品名", "数量", "単価", "購入理由", "希望納期", "承認者コメント", "承認日", "ファイル名"
    ]
    existing_columns = [col for col in column_order if col in display_df.columns]
    return display_df[existing_columns]

# --- Sidebar for Role Selection ---
st.sidebar.title("ユーザーロール選択")
roles = ["申請者", "承認者", "システム管理者"]
st.session_state.user_role = st.sidebar.radio("役割を選択してください:", roles, index=roles.index(st.session_state.user_role))

st.sidebar.markdown("---")
st.sidebar.info(f"現在のロール: **{st.session_state.user_role}**")

# --- Main Application Logic ---
st.title("📝 購入伺いシステム (SQLite版)")

if st.session_state.user_role == "申請者":
    st.header("購入申請フォーム")
    with st.form("purchase_request_form", clear_on_submit=True):
        st.subheader("申請者情報")
        applicant_name = st.text_input("申請者名", placeholder="例: 山田 太郎")
        department = st.text_input("部署名", placeholder="例: 営業部")
        request_subject = st.text_input("件名", placeholder="例: PC購入の件")

        st.subheader("購入品詳細")
        item_name = st.text_input("品名", placeholder="例: ノートパソコン XYZモデル")
        quantity = st.number_input("数量", min_value=1, value=1, step=1)
        unit_price = st.number_input("単価（円）", min_value=0.0, value=100000.0, step=1000.0, format="%.2f")
        total_price = quantity * unit_price
        st.text_input("合計金額（円）", value=f"{total_price:,.2f}", disabled=True)

        reason = st.text_area("購入理由・目的", placeholder="例: 新規プロジェクトのため、高性能なPCが必要")
        due_date = st.date_input("希望納期", value=datetime.now().date() + pd.Timedelta(days=7))

        uploaded_file = st.file_uploader("添付ファイル (見積書など)", type=['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx'])
        file_name_to_store = uploaded_file.name if uploaded_file else None

        submit_button = st.form_submit_button("申請する")

        if submit_button:
            if not all([applicant_name, department, request_subject, item_name]):
                st.error("必須項目（申請者名, 部署名, 件名, 品名）を入力してください。")
            else:
                new_request_id = generate_request_id()
                new_request_data = {
                    "申請ID": new_request_id,
                    "申請日": datetime.now(),
                    "申請者": applicant_name,
                    "部署": department,
                    "件名": request_subject,
                    "品名": item_name,
                    "数量": quantity,
                    "単価": unit_price,
                    "合計金額": total_price,
                    "購入理由": reason,
                    "希望納期": pd.to_datetime(due_date),
                    "ステータス": "申請中",
                    "承認者コメント": "",
                    "承認日": pd.NaT,
                    "ファイル名": file_name_to_store,
                }
                add_request_to_db(new_request_data)
                st.success(f"購入申請 (ID: {new_request_id}) をデータベースに登録しました。")
                if uploaded_file:
                    st.info(f"ファイル '{uploaded_file.name}' がアップロードされました（デモ：ファイル自体はDBに保存されません）。")

    st.header("自分の申請一覧")
    requests_df = get_all_requests_from_db()
    # For this demo, "自分の申請一覧" shows all requests for simplicity.
    # In a real app, you'd filter by the logged-in user.
    if not requests_df.empty:
        my_requests_df = requests_df.copy() # Show all for demo simplicity
        st.dataframe(format_display_df(my_requests_df), use_container_width=True, hide_index=True)
    else:
        st.info("まだ申請はありません。")

elif st.session_state.user_role == "承認者":
    st.header("承認待ち申請一覧")
    requests_df = get_all_requests_from_db()
    pending_requests_df = requests_df[requests_df["ステータス"] == "申請中"]

    if not pending_requests_df.empty:
        for index, request_row in pending_requests_df.iterrows():
            request = request_row.to_dict() # Work with dict for easier access
            st.subheader(f"申請ID: {request['申請ID']} - {request['件名']}")
            with st.expander("詳細を表示/承認処理", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**申請者:** {request['申請者']}")
                    st.markdown(f"**部署:** {request['部署']}")
                    st.markdown(f"**申請日:** {pd.to_datetime(request['申請日']).strftime('%Y-%m-%d') if pd.notna(request['申請日']) else 'N/A'}")
                    st.markdown(f"**希望納期:** {pd.to_datetime(request['希望納期']).strftime('%Y-%m-%d') if pd.notna(request['希望納期']) else 'N/A'}")
                with col2:
                    st.markdown(f"**品名:** {request['品名']}")
                    st.markdown(f"**数量:** {request['数量']}")
                    st.markdown(f"**単価:** {request['単価']:,.2f} 円")
                    st.markdown(f"**合計金額:** {request['合計金額']:,.2f} 円")

                st.markdown(f"**購入理由:**")
                st.info(request['購入理由'])

                if request['ファイル名']:
                     st.markdown(f"**添付ファイル:** {request['ファイル名']} (表示/ダウンロード機能は未実装)")
                else:
                    st.markdown("**添付ファイル:** なし")

                approver_comment = st.text_area("承認者コメント", key=f"comment_{request['申請ID']}")

                action_col1, action_col2 = st.columns(2) # Removed third column for now
                with action_col1:
                    if st.button("承認", key=f"approve_{request['申請ID']}", type="primary"):
                        update_request_in_db(request["申請ID"], "承認済", approver_comment, datetime.now())
                        st.success(f"申請ID: {request['申請ID']} を承認しました。")
                        st.rerun()

                with action_col2:
                    if st.button("却下", key=f"reject_{request['申請ID']}"):
                        if not approver_comment:
                            st.warning("却下理由をコメントに入力してください。")
                        else:
                            update_request_in_db(request["申請ID"], "却下済", approver_comment, datetime.now())
                            st.error(f"申請ID: {request['申請ID']} を却下しました。")
                            st.rerun()
            st.markdown("---")
    else:
        st.info("承認待ちの申請はありません。")

elif st.session_state.user_role == "システム管理者":
    st.header("全申請一覧")
    all_requests_df = get_all_requests_from_db()
    if not all_requests_df.empty:
        all_requests_sorted = all_requests_df.sort_values(by="申請日", ascending=False, na_position='first')
        st.dataframe(format_display_df(all_requests_sorted), use_container_width=True, hide_index=True)

        if st.button("全申請データをクリア（DBから削除）", type="secondary"):
            # Confirmation dialog
            confirm_col1, confirm_col2 = st.columns([3,1])
            with confirm_col1:
                st.warning("本当にデータベースから全ての申請データをクリアしますか？この操作は元に戻せません。")
            with confirm_col2:
                if st.button("はい、クリアします", key="confirm_clear_db_button", type="primary"):
                    delete_all_requests_from_db()
                    st.success("データベースから全申請データをクリアしました。")
                    st.rerun()
    else:
        st.info("申請データはまだありません。")

# --- Footer or Common Information ---
st.markdown("---")
st.caption("© 2024 購入伺いシステム (Streamlit SQLite Demo)")


