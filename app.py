import streamlit as st
import pandas as pd
from datetime import datetime
import uuid # To generate unique IDs for requests

# Set page configuration
st.set_page_config(layout="wide", page_title="購入伺いシステム", page_icon="📝")

# --- Initialize session state for storing data ---
if 'requests_df' not in st.session_state:
    # Initialize an empty DataFrame to store purchase requests
    # Status options: 申請中, 承認済, 却下済, 差し戻し (For simplicity, we'll start with fewer)
    st.session_state.requests_df = pd.DataFrame(columns=[
        "申請ID", "申請日", "申請者", "部署", "件名", "品名", "数量", "単価", "合計金額",
        "購入理由", "希望納期", "ステータス", "承認者コメント", "承認日", "ファイル名"
    ])
if 'user_role' not in st.session_state:
    st.session_state.user_role = "申請者" # Default role
if 'next_request_id_counter' not in st.session_state:
    st.session_state.next_request_id_counter = 1 # Simple counter for request IDs

# --- Helper Functions ---
def generate_request_id():
    """Generates a unique request ID."""
    # Using a simple counter for this demo. For production, consider UUIDs or database sequences.
    # req_id = f"REQ-{datetime.now().strftime('%Y%m%d')}-{st.session_state.next_request_id_counter:04d}"
    # st.session_state.next_request_id_counter += 1
    return str(uuid.uuid4()) # Using UUID for better uniqueness in a session

def format_display_df(df):
    """Formats the DataFrame for better display."""
    if df.empty:
        return df

    display_df = df.copy()
    # Format date columns if they exist
    if "申請日" in display_df.columns:
        display_df["申請日"] = pd.to_datetime(display_df["申請日"]).dt.strftime('%Y-%m-%d')
    if "希望納期" in display_df.columns:
        display_df["希望納期"] = pd.to_datetime(display_df["希望納期"]).dt.strftime('%Y-%m-%d')
    if "承認日" in display_df.columns:
        display_df["承認日"] = pd.to_datetime(display_df["承認日"], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')

    # Reorder columns for display if needed (example)
    column_order = [
        "申請ID", "ステータス", "申請日", "申請者", "部署", "件名", "合計金額",
        "品名", "数量", "単価", "購入理由", "希望納期", "承認者コメント", "承認日", "ファイル名"
    ]
    # Filter out columns not present in the current DataFrame
    existing_columns = [col for col in column_order if col in display_df.columns]
    return display_df[existing_columns]

# --- Sidebar for Role Selection ---
st.sidebar.title("ユーザーロール選択")
roles = ["申請者", "承認者", "システム管理者"] # Added System Admin for viewing all
st.session_state.user_role = st.sidebar.radio("役割を選択してください:", roles, index=roles.index(st.session_state.user_role))

st.sidebar.markdown("---")
st.sidebar.info(f"現在のロール: **{st.session_state.user_role}**")

# --- Main Application Logic ---
st.title("📝 購入伺いシステム (プロトタイプ)")

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
                    "申請日": datetime.now(), # Store as datetime object
                    "申請者": applicant_name,
                    "部署": department,
                    "件名": request_subject,
                    "品名": item_name,
                    "数量": quantity,
                    "単価": unit_price,
                    "合計金額": total_price,
                    "購入理由": reason,
                    "希望納期": pd.to_datetime(due_date), # Store as datetime object
                    "ステータス": "申請中",
                    "承認者コメント": "",
                    "承認日": pd.NaT, # Not a Time for not yet approved
                    "ファイル名": file_name_to_store,
                }
                # Convert dict to DataFrame and append
                new_request_df = pd.DataFrame([new_request_data])
                st.session_state.requests_df = pd.concat([st.session_state.requests_df, new_request_df], ignore_index=True)
                st.success(f"購入申請 (ID: {new_request_id}) を提出しました。")
                # To handle file saving (this is a placeholder, actual saving needs more robust logic)
                if uploaded_file:
                    # In a real app, you'd save this to a persistent storage and store the path/ID.
                    # For this demo, we are just storing the name.
                    st.info(f"ファイル '{uploaded_file.name}' がアップロードされました（デモ）。")


    st.header("自分の申請一覧")
    if not st.session_state.requests_df.empty:
        # Filter for applicant's requests - for simplicity, we show all for now.
        # In a real app, you'd filter by logged-in user.
        # For this demo, let's assume the current applicant_name input is the filter
        my_requests_df = st.session_state.requests_df.copy() # Show all for demo simplicity
        if not my_requests_df.empty:
            st.dataframe(format_display_df(my_requests_df), use_container_width=True, hide_index=True)
        else:
            st.info("まだ申請はありません。")
    else:
        st.info("まだ申請はありません。")

elif st.session_state.user_role == "承認者":
    st.header("承認待ち申請一覧")
    pending_requests_df = st.session_state.requests_df[st.session_state.requests_df["ステータス"] == "申請中"]

    if not pending_requests_df.empty:
        for index, request in pending_requests_df.iterrows():
            st.subheader(f"申請ID: {request['申請ID']} - {request['件名']}")
            with st.expander("詳細を表示/承認処理", expanded=False):
                # Display request details in a more readable format
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**申請者:** {request['申請者']}")
                    st.markdown(f"**部署:** {request['部署']}")
                    st.markdown(f"**申請日:** {pd.to_datetime(request['申請日']).strftime('%Y-%m-%d')}")
                    st.markdown(f"**希望納期:** {pd.to_datetime(request['希望納期']).strftime('%Y-%m-%d')}")
                with col2:
                    st.markdown(f"**品名:** {request['品名']}")
                    st.markdown(f"**数量:** {request['数量']}")
                    st.markdown(f"**単価:** {request['単価']:,.2f} 円")
                    st.markdown(f"**合計金額:** {request['合計金額']:,.2f} 円")

                st.markdown(f"**購入理由:**")
                st.info(request['購入理由'])

                if request['ファイル名']:
                     st.markdown(f"**添付ファイル:** {request['ファイル名']} (表示/ダウンロード機能は未実装)")
                     # In a real app, you'd provide a download link here if files are stored.
                else:
                    st.markdown("**添付ファイル:** なし")

                approver_comment = st.text_area("承認者コメント", key=f"comment_{request['申請ID']}")

                action_col1, action_col2, action_col3 = st.columns(3)
                with action_col1:
                    if st.button("承認", key=f"approve_{request['申請ID']}", type="primary"):
                        st.session_state.requests_df.loc[st.session_state.requests_df["申請ID"] == request["申請ID"], "ステータス"] = "承認済"
                        st.session_state.requests_df.loc[st.session_state.requests_df["申請ID"] == request["申請ID"], "承認者コメント"] = approver_comment
                        st.session_state.requests_df.loc[st.session_state.requests_df["申請ID"] == request["申請ID"], "承認日"] = datetime.now()
                        st.success(f"申請ID: {request['申請ID']} を承認しました。")
                        st.rerun() # Rerun to update the list

                with action_col2:
                    if st.button("却下", key=f"reject_{request['申請ID']}"):
                        if not approver_comment:
                            st.warning("却下理由をコメントに入力してください。")
                        else:
                            st.session_state.requests_df.loc[st.session_state.requests_df["申請ID"] == request["申請ID"], "ステータス"] = "却下済"
                            st.session_state.requests_df.loc[st.session_state.requests_df["申請ID"] == request["申請ID"], "承認者コメント"] = approver_comment
                            st.session_state.requests_df.loc[st.session_state.requests_df["申請ID"] == request["申請ID"], "承認日"] = datetime.now()
                            st.error(f"申請ID: {request['申請ID']} を却下しました。")
                            st.rerun() # Rerun to update the list
                # "差し戻し" can be added here similarly
                # with action_col3:
                #     if st.button("差し戻し", key=f"return_{request['申請ID']}"):
                #         # Logic for returning the request
                #         pass
            st.markdown("---")
    else:
        st.info("承認待ちの申請はありません。")

elif st.session_state.user_role == "システム管理者":
    st.header("全申請一覧")
    if not st.session_state.requests_df.empty:
        # Display all requests, sort by date descending
        all_requests_sorted = st.session_state.requests_df.sort_values(by="申請日", ascending=False)
        st.dataframe(format_display_df(all_requests_sorted), use_container_width=True, hide_index=True)

        if st.button("全申請データをクリア（デモ用）", type="secondary"):
            if st.checkbox("本当にクリアしますか？この操作は元に戻せません。", key="confirm_clear"):
                st.session_state.requests_df = pd.DataFrame(columns=[
                    "申請ID", "申請日", "申請者", "部署", "件名", "品名", "数量", "単価", "合計金額",
                    "購入理由", "希望納期", "ステータス", "承認者コメント", "承認日", "ファイル名"
                ])
                st.session_state.next_request_id_counter = 1
                st.success("全申請データをクリアしました。")
                st.rerun()

    else:
        st.info("申請データはまだありません。")

# --- Footer or Common Information ---
st.markdown("---")
st.caption("© 2024 購入伺いシステム (Streamlit Demo)")

