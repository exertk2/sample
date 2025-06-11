import streamlit as st
import sqlite3
import pandas as pd
import datetime

# --- データベース設定 ---
DB_NAME = "trip_management.db"

def get_db_connection():
    """データベース接続を取得します。"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """データベースとテーブルを初期化します。"""
    conn = get_db_connection()
    c = conn.cursor()
    # テーブル作成 (ご提示のスキーマを修正)
    c.execute('''
        CREATE TABLE IF NOT EXISTS trip (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            employee TEXT NOT NULL,
            seq TEXT,
            sex_code INTEGER,
            sex_name TEXT,
            department_code INTEGER,
            department_name TEXT,
            ward_code INTEGER,
            ward_name TEXT,
            timestamp TEXT DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
            history_number INTEGER DEFAULT 1,
            "1st_choice" TEXT,
            "2nd_choice" TEXT,
            bus TEXT,
            allergy TEXT,
            allergy_details TEXT
        )
    ''')
    
    # --- サンプルデータの投入 (初回実行時のみ) ---
    c.execute("SELECT COUNT(*) FROM trip")
    if c.fetchone()[0] == 0:
        sample_employees = [
            (101, '鈴木 一郎', 'A-1', 1, '男性', 10, '総務部', 101, '第一病棟'),
            (102, '佐藤 花子', 'A-2', 2, '女性', 10, '総務部', 102, '第二病棟'),
            (201, '高橋 健太', 'B-1', 1, '男性', 20, '経理部', 201, '第三病棟'),
            (202, '田中 美咲', 'B-2', 2, '女性', 20, '経理部', 101, '第一病棟'),
            (301, '渡辺 雄大', 'C-1', 1, '男性', 30, '人事部', 102, '第二病棟'),
        ]
        for emp in sample_employees:
            c.execute('''
                INSERT INTO trip (employee_id, employee, seq, sex_code, sex_name, department_code, department_name, ward_code, ward_name, "1st_choice", "2nd_choice", bus, allergy, allergy_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (*emp, '未選択', '未選択', '未選択', 'なし', ''))
    
    conn.commit()
    conn.close()

def get_all_trips():
    """全ての旅行データを取得します。"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM trip ORDER BY employee_id, history_number DESC", conn)
    conn.close()
    return df

def get_latest_trips():
    """各職員の最新の旅行データを取得します。"""
    df = get_all_trips()
    if not df.empty:
        # employee_idでグループ化し、history_numberが最大の行のインデックスを取得
        latest_idx = df.groupby('employee_id')['history_number'].idxmax()
        return df.loc[latest_idx]
    return pd.DataFrame()

def get_employee_master():
    """職員マスタ（重複除外）を取得します。"""
    df = get_latest_trips()
    if not df.empty:
        return df[['employee_id', 'employee', 'seq', 'sex_code', 'sex_name', 'department_code', 'department_name', 'ward_code', 'ward_name']].drop_duplicates().sort_values('employee_id')
    return pd.DataFrame()


def add_trip_record(employee_id, choice1, choice2, bus, allergy, allergy_details):
    """新しい旅行記録を追加（更新）します。"""
    conn = get_db_connection()
    c = conn.cursor()

    # 既存の職員情報を取得
    c.execute("SELECT * FROM trip WHERE employee_id = ? ORDER BY history_number DESC LIMIT 1", (employee_id,))
    latest_record = c.fetchone()
    
    if not latest_record:
        st.error("指定された職員IDが見つかりません。")
        conn.close()
        return

    # 新しい履歴番号を計算
    new_history_number = latest_record['history_number'] + 1
    
    # 新しいレコードを挿入
    c.execute('''
        INSERT INTO trip (
            employee_id, employee, seq, sex_code, sex_name, 
            department_code, department_name, ward_code, ward_name, 
            history_number, "1st_choice", "2nd_choice", bus, allergy, allergy_details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        latest_record['employee_id'], latest_record['employee'], latest_record['seq'],
        latest_record['sex_code'], latest_record['sex_name'], latest_record['department_code'],
        latest_record['department_name'], latest_record['ward_code'], latest_record['ward_name'],
        new_history_number, choice1, choice2, bus, allergy, allergy_details
    ))
    
    conn.commit()
    conn.close()


# --- Streamlit UI ---

st.set_page_config(page_title="職員研修旅行管理アプリ", layout="wide")
st.title("職員研修旅行管理アプリ")

# --- サイドバー (ナビゲーション) ---
menu = ["入力", "一覧（最新）", "一覧（全履歴）", "印刷用リスト（基本）", "印刷用リスト（アレルギー情報付き）"]
choice = st.sidebar.selectbox("メニューを選択", menu)
st.sidebar.markdown("---")
st.sidebar.info("このアプリは職員の研修旅行の希望を管理します。")

# --- ページごとの表示 ---

if choice == "入力":
    st.header("希望の入力・更新")
    
    employee_master = get_employee_master()
    if not employee_master.empty:
        employee_dict = dict(zip(employee_master['employee_id'], employee_master['employee']))
        
        selected_employee_id = st.selectbox(
            "職員を選択してください",
            options=list(employee_dict.keys()),
            format_func=lambda x: f"{x}: {employee_dict[x]}"
        )

        # 最新の登録情報を取得してフォームのデフォルト値に設定
        latest_trips = get_latest_trips()
        current_data = latest_trips[latest_trips['employee_id'] == selected_employee_id].iloc[0]

        with st.form("trip_form"):
            st.markdown(f"**選択中の職員:** {current_data['employee']} (ID: {current_data['employee_id']})")
            
            # 選択肢の定義
            course_options = ["未選択", "Aコース：温泉とグルメの旅", "Bコース：歴史と文化探訪", "Cコース：アクティビティ体験"]
            bus_options = ["未選択", "1号車", "2号車", "3号車", "不要"]
            
            choice1 = st.selectbox("第1希望", course_options, index=course_options.index(current_data['1st_choice']) if current_data['1st_choice'] in course_options else 0)
            choice2 = st.selectbox("第2希望", course_options, index=course_options.index(current_data['2nd_choice']) if current_data['2nd_choice'] in course_options else 0)
            bus = st.selectbox("バスの希望", bus_options, index=bus_options.index(current_data['bus']) if current_data['bus'] in bus_options else 0)
            
            allergy = st.radio("アレルギーの有無", ["なし", "あり"], index=["なし", "あり"].index(current_data['allergy']))
            
            allergy_details = st.text_area("アレルギーの詳細（ありの場合）", value=current_data['allergy_details'])
            
            submitted = st.form_submit_button("登録する")
            
            if submitted:
                if choice1 == "未選択" or bus == "未選択":
                    st.warning("第1希望とバスの希望は「未選択」以外を選んでください。")
                elif choice1 == choice2 and choice1 != "未選択":
                     st.warning("第1希望と第2希望は異なるコースを選択してください。")
                else:
                    add_trip_record(selected_employee_id, choice1, choice2, bus, allergy, allergy_details)
                    st.success(f"{current_data['employee']}さんの希望を登録しました。")
                    st.balloons()

elif choice == "一覧（最新）":
    st.header("職員別・最新の希望一覧")
    st.info("各職員の最新の登録情報のみ表示しています。")
    latest_trips = get_latest_trips()
    
    display_cols = [
        'employee_id', 'employee', 'department_name', '1st_choice', 
        '2nd_choice', 'bus', 'allergy', 'allergy_details', 'timestamp'
    ]
    # 存在しない列を除外
    display_cols = [col for col in display_cols if col in latest_trips.columns]

    if not latest_trips.empty:
        st.dataframe(latest_trips[display_cols], use_container_width=True)
    else:
        st.info("データがありません。")

elif choice == "一覧（全履歴）":
    st.header("全登録履歴一覧")
    st.info("過去の変更履歴を含む全てのデータを表示しています。")
    all_trips = get_all_trips()

    display_cols = [
        'employee_id', 'employee', 'history_number', '1st_choice', 
        'bus', 'allergy', 'timestamp'
    ]
    display_cols = [col for col in display_cols if col in all_trips.columns]
    
    if not all_trips.empty:
        st.dataframe(all_trips[display_cols], use_container_width=True)
    else:
        st.info("データがありません。")

elif choice == "印刷用リスト（基本）":
    st.header("印刷用リスト（基本） - コース別・バス乗車リスト")
    
    latest_trips = get_latest_trips()
    valid_trips = latest_trips[latest_trips['1st_choice'] != '未選択']
    
    if not valid_trips.empty:
        grouped = valid_trips.groupby('1st_choice')
        for name, group in grouped:
            st.subheader(f"コース: {name} (計: {len(group)}名)")
            display_data = group[['employee', 'department_name', 'bus']].rename(columns={
                'employee': '氏名', 'department_name': '所属', 'bus': 'バス'
            })
            st.table(display_data.sort_values('bus').reset_index(drop=True))
    else:
        st.info("有効なデータがありません。")

elif choice == "印刷用リスト（アレルギー情報付き）":
    st.header("印刷用リスト（アレルギー情報付き）")
    
    latest_trips = get_latest_trips()
    valid_trips = latest_trips[latest_trips['1st_choice'] != '未選択']

    if not valid_trips.empty:
        grouped = valid_trips.groupby('1st_choice')
        for name, group in grouped:
            st.subheader(f"コース: {name} (計: {len(group)}名)")
            display_data = group[['employee', 'department_name', 'bus', 'allergy', 'allergy_details']].rename(columns={
                'employee': '氏名', 'department_name': '所属', 'bus': 'バス', 'allergy': 'アレルギー', 'allergy_details': '詳細'
            })
            st.table(display_data.sort_values('bus').reset_index(drop=True))
    else:
        st.info("有効なデータがありません。")

# --- アプリケーションの初期化 ---
if __name__ == "__main__":
    init_db()
    # メインの処理はStreamlitが自動的に行う
