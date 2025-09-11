import streamlit as st
import sqlite3
import pandas as pd
import os

# ★ アプリケーション起動時のパスワード認証
PASSWORD = "1" # ★ ここを実際のパスワードに変更してください

# --------------------
# データベースの初期化
# --------------------
def init_db():
    """
    SQLiteデータベースを初期化し、documentsテーブルを作成します。
    """
    conn = sqlite3.connect('employee_docs.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            employee_id TEXT NOT NULL UNIQUE,
            handler_name TEXT,
            submission_date TEXT,
            check_date TEXT,
            rejection_reason TEXT,
            resubmission_date TEXT,
            recheck_date TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

# アプリケーション起動時にデータベースを初期化
if not os.path.exists('employee_docs.db'):
    init_db()

# --------------------
# データベース接続関数
# --------------------
def get_db_connection():
    """
    SQLiteデータベースへの接続を返します。
    """
    conn = sqlite3.connect('employee_docs.db')
    conn.row_factory = sqlite3.Row
    return conn

# --------------------
# データの取得関数
# --------------------
def get_all_records():
    """
    データベースから全ての書類記録を取得し、Pandas DataFrameとして返します。
    """
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM documents", conn)
    conn.close()
    return df

# --------------------
# Streamlit アプリケーションのUIとロジック
# --------------------

# セッション状態の初期化
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# パスワード認証
if not st.session_state['authenticated']:
    st.title("書類管理システム ログイン")
    password_input = st.text_input("パスワードを入力してください", type="password")
    
    if st.button("ログイン"):
        if password_input == PASSWORD:
            st.session_state['authenticated'] = True
            st.success("ログインに成功しました！")
            st.experimental_rerun()
        else:
            st.error("パスワードが間違っています。")

# 認証済みの場合のメインアプリケーション
else:
    st.title("雇用書類提出状況 管理アプリ")

    # サイドバーメニュー
    st.sidebar.title("操作メニュー")
    menu = st.sidebar.selectbox("機能を選択", ["新規登録", "データ閲覧・編集"])

    # --------------------
    # 新規登録機能
    # --------------------
    if menu == "新規登録":
        st.subheader("新規書類提出の登録")
        with st.form("new_entry_form"):
            employee_name = st.text_input("氏名", key="new_name")
            employee_id = st.text_input("職員番号", key="new_id")
            handler_name = st.text_input("担当職員名", key="new_handler")
            submission_date = st.date_input("書類提出日")
            
            submit_button = st.form_submit_button("登録")

            if submit_button:
                if employee_name and employee_id:
                    conn = get_db_connection()
                    try:
                        conn.execute("""
                            INSERT INTO documents (employee_name, employee_id, handler_name, submission_date) 
                            VALUES (?, ?, ?, ?)
                        """, (employee_name, employee_id, handler_name, submission_date.strftime('%Y-%m-%d')))
                        conn.commit()
                        st.success("新しい登録が完了しました！")
                    except sqlite3.IntegrityError:
                        st.error("エラー: その職員番号は既に登録されています。")
                    finally:
                        conn.close()
                else:
                    st.error("氏名と職員番号は必須です。")

    # --------------------
    # データ閲覧・編集機能
    # --------------------
    elif menu == "データ閲覧・編集":
        st.subheader("登録済みデータの閲覧と編集")
        
        df = get_all_records()

        if not df.empty:
            # データを表示
            st.dataframe(df)
            
            # 個別データの編集
            st.subheader("個別データの編集")
            record_id_to_edit = st.selectbox("編集するデータのIDを選択", df['id'].tolist())
            
            if record_id_to_edit:
                selected_record = df[df['id'] == record_id_to_edit].iloc[0]
                
                with st.form("edit_form"):
                    st.text_input("氏名", value=selected_record['employee_name'], disabled=True)
                    st.text_input("職員番号", value=selected_record['employee_id'], disabled=True)
                    
                    handler_name = st.text_input("担当職員名", value=selected_record['handler_name'], key="edit_handler")
                    submission_date = st.text_input("書類提出日", value=selected_record['submission_date'], key="edit_sub_date")
                    
                    # 日付の形式を調整してDate Inputに渡す
                    check_date_val = selected_record['check_date']
                    resubmission_date_val = selected_record['resubmission_date']
                    recheck_date_val = selected_record['recheck_date']

                    if check_date_val: check_date_val = pd.to_datetime(check_date_val).date()
                    if resubmission_date_val: resubmission_date_val = pd.to_datetime(resubmission_date_val).date()
                    if recheck_date_val: recheck_date_val = pd.to_datetime(recheck_date_val).date()

                    check_date = st.date_input("書類内容確認日", value=check_date_val)
                    rejection_reason = st.text_area("不受理理由", value=selected_record['rejection_reason'], key="edit_reject")
                    resubmission_date = st.date_input("再提出日", value=resubmission_date_val)
                    recheck_date = st.date_input("書類内容再確認日", value=recheck_date_val)
                    notes = st.text_area("備考", value=selected_record['notes'], key="edit_notes")

                    update_button = st.form_submit_button("更新")

                    if update_button:
                        conn = get_db_connection()
                        conn.execute("""
                            UPDATE documents
                            SET handler_name=?, submission_date=?, check_date=?, rejection_reason=?, resubmission_date=?, recheck_date=?, notes=?
                            WHERE id=?
                        """, (handler_name, submission_date, check_date.strftime('%Y-%m-%d') if check_date else None, rejection_reason, resubmission_date.strftime('%Y-%m-%d') if resubmission_date else None, recheck_date.strftime('%Y-%m-%d') if recheck_date else None, notes, record_id_to_edit))
                        conn.commit()
                        conn.close()
                        st.success("データが更新されました！")
                        st.experimental_rerun()
        else:
            st.info("登録されているデータはありません。")
