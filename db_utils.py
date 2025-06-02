# db_utils.py
# データベース操作関連の関数をまとめたファイル

import sqlite3
from datetime import date, datetime

DATABASE_NAME = 'visit_management.db'

def get_db_connection():
    """データベース接続を取得する"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # カラム名でアクセスできるようにする
    return conn

def init_db():
    """データベースの初期化（テーブル作成と初期事業所登録）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 事業所テーブル
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS offices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    ''')

    # 担当者テーブル
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        is_active BOOLEAN DEFAULT TRUE -- 論理削除用フラグ
    )
    ''')

    # 事業所担当割り当てテーブル
    # 1つの事業所に同時にアクティブな担当者は最大4人までという制約はアプリケーション側で制御
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        office_id INTEGER NOT NULL,
        staff_id INTEGER NOT NULL,
        start_date TEXT NOT NULL, -- YYYY-MM-DD
        end_date TEXT,            -- YYYY-MM-DD, NULLの場合は現在も担当
        FOREIGN KEY (office_id) REFERENCES offices(id),
        FOREIGN KEY (staff_id) REFERENCES staff(id)
    )
    ''')

    # 訪問記録テーブル
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL, -- どの割り当てに対する訪問か
        visit_date TEXT NOT NULL,       -- YYYY-MM-DD
        type TEXT NOT NULL,             -- '予定' or '実績'
        notes TEXT,
        FOREIGN KEY (assignment_id) REFERENCES assignments(id)
    )
    ''')

    # 初期事業所データ（AからZ）を登録 (存在しない場合のみ)
    for i in range(26):
        office_name = chr(ord('A') + i)
        cursor.execute("SELECT id FROM offices WHERE name = ?", (office_name,))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO offices (name) VALUES (?)", (office_name,))

    conn.commit()
    conn.close()

# --- 担当者 (Staff) CRUD ---
def add_staff(name):
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO staff (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError: # UNIQUE制約違反など
        return False
    finally:
        conn.close()

def get_all_staff(active_only=True):
    conn = get_db_connection()
    query = "SELECT id, name, is_active FROM staff"
    if active_only:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name"
    staff_list = conn.execute(query).fetchall()
    conn.close()
    return staff_list

def get_staff_by_id(staff_id):
    conn = get_db_connection()
    staff = conn.execute("SELECT id, name, is_active FROM staff WHERE id = ?", (staff_id,)).fetchone()
    conn.close()
    return staff

def update_staff_name(staff_id, new_name):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE staff SET name = ? WHERE id = ?", (new_name, staff_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def set_staff_active_status(staff_id, is_active):
    conn = get_db_connection()
    conn.execute("UPDATE staff SET is_active = ? WHERE id = ?", (is_active, staff_id))
    conn.commit()
    conn.close()

# --- 事業所 (Office) ---
def get_all_offices():
    conn = get_db_connection()
    offices = conn.execute("SELECT id, name FROM offices ORDER BY name").fetchall()
    conn.close()
    return offices

def get_office_by_id(office_id):
    conn = get_db_connection()
    office = conn.execute("SELECT id, name FROM offices WHERE id = ?", (office_id,)).fetchone()
    conn.close()
    return office

# --- 割り当て (Assignments) CRUD ---
def add_assignment(office_id, staff_id, start_date):
    conn = get_db_connection()
    # 同じ担当者が同じ事業所に重複してアクティブに割り当てられないようにする (簡易チェック)
    # より厳密には、既存の割り当て期間と重複しないかをチェックする必要がある
    current_assignments = get_current_assignments_for_office(office_id)
    if len(current_assignments) >= 4:
        conn.close()
        return False, "この事業所には既に4人の担当者が割り当てられています。"

    # 同じ担当者が既にアクティブな割り当てを持っていないか確認
    for assign in current_assignments:
        if assign['staff_id'] == staff_id:
            conn.close()
            return False, "この担当者は既にこの事業所にアクティブに割り当てられています。"

    try:
        conn.execute("INSERT INTO assignments (office_id, staff_id, start_date) VALUES (?, ?, ?)",
                     (office_id, staff_id, start_date))
        conn.commit()
        return True, "割り当てが追加されました。"
    except Exception as e:
        return False, f"割り当て追加エラー: {e}"
    finally:
        conn.close()

def end_assignment(assignment_id, end_date):
    conn = get_db_connection()
    conn.execute("UPDATE assignments SET end_date = ? WHERE id = ?", (end_date, assignment_id))
    conn.commit()
    conn.close()

def get_assignments_for_office(office_id):
    """特定の事業所の全ての割り当て履歴を取得"""
    conn = get_db_connection()
    assignments = conn.execute('''
        SELECT a.id, a.office_id, o.name as office_name, a.staff_id, s.name as staff_name, a.start_date, a.end_date
        FROM assignments a
        JOIN offices o ON a.office_id = o.id
        JOIN staff s ON a.staff_id = s.id
        WHERE a.office_id = ? AND s.is_active = TRUE
        ORDER BY a.start_date DESC, s.name
    ''', (office_id,)).fetchall()
    conn.close()
    return assignments

def get_current_assignments_for_office(office_id):
    """特定の事業所の現在の割り当てを取得 (end_date is NULL)"""
    conn = get_db_connection()
    today = date.today().strftime('%Y-%m-%d')
    assignments = conn.execute('''
        SELECT a.id, a.office_id, o.name as office_name, a.staff_id, s.name as staff_name, a.start_date, a.end_date
        FROM assignments a
        JOIN offices o ON a.office_id = o.id
        JOIN staff s ON a.staff_id = s.id
        WHERE a.office_id = ? AND s.is_active = TRUE AND a.start_date <= ? AND (a.end_date IS NULL OR a.end_date >= ?)
        ORDER BY s.name
    ''', (office_id, today, today)).fetchall()
    conn.close()
    return assignments

def get_assignment_by_id(assignment_id):
    conn = get_db_connection()
    assignment = conn.execute('''
        SELECT a.id, a.office_id, o.name as office_name, a.staff_id, s.name as staff_name, a.start_date, a.end_date
        FROM assignments a
        JOIN offices o ON a.office_id = o.id
        JOIN staff s ON a.staff_id = s.id
        WHERE a.id = ?
    ''', (assignment_id,)).fetchone()
    conn.close()
    return assignment

# --- 訪問記録 (Visits) CRUD ---
def add_visit(assignment_id, visit_date, visit_type, notes):
    conn = get_db_connection()
    conn.execute("INSERT INTO visits (assignment_id, visit_date, type, notes) VALUES (?, ?, ?, ?)",
                 (assignment_id, visit_date, visit_type, notes))
    conn.commit()
    conn.close()

def get_visits_for_assignment(assignment_id):
    conn = get_db_connection()
    visits = conn.execute('''
        SELECT v.id, v.visit_date, v.type, v.notes,
               a.staff_id, s.name as staff_name,
               a.office_id, o.name as office_name
        FROM visits v
        JOIN assignments a ON v.assignment_id = a.id
        JOIN staff s ON a.staff_id = s.id
        JOIN offices o ON a.office_id = o.id
        WHERE v.assignment_id = ?
        ORDER BY v.visit_date DESC
    ''', (assignment_id,)).fetchall()
    conn.close()
    return visits

def get_visits_for_office(office_id):
    conn = get_db_connection()
    # 特定の事業所に関連する全てのアクティブな担当者の訪問記録を取得
    visits = conn.execute('''
        SELECT v.id, v.visit_date, v.type, v.notes,
               a.staff_id, s.name as staff_name, s.is_active as staff_is_active,
               a.office_id, o.name as office_name,
               a.id as assignment_id
        FROM visits v
        JOIN assignments a ON v.assignment_id = a.id
        JOIN staff s ON a.staff_id = s.id
        JOIN offices o ON a.office_id = o.id
        WHERE a.office_id = ? AND s.is_active = TRUE
        ORDER BY s.name, v.visit_date DESC
    ''', (office_id,)).fetchall()
    conn.close()
    return visits

def get_all_visits_summary():
    """全事業所の最新の訪問状況などを取得するためのサマリーデータ"""
    conn = get_db_connection()
    # このクエリは複雑になるため、ここでは基本的な情報を取得する例とします
    # 各事業所の最新の訪問日や担当者などを集約する必要がある
    # 簡単のため、ここでは全訪問記録を返す (アプリ側で加工)
    # より実践的には、事業所ごとに最新の訪問実績などを集約するクエリを書く
    summary = conn.execute('''
        SELECT
            o.name as office_name,
            s.name as staff_name,
            v.visit_date,
            v.type,
            v.notes,
            a.start_date as assignment_start_date,
            a.end_date as assignment_end_date
        FROM visits v
        JOIN assignments a ON v.assignment_id = a.id
        JOIN staff s ON a.staff_id = s.id
        JOIN offices o ON a.office_id = o.id
        WHERE s.is_active = TRUE AND (a.end_date IS NULL OR a.end_date >= date('now'))
        ORDER BY o.name, v.visit_date DESC
    ''').fetchall()
    conn.close()
    return summary


if __name__ == '__main__':
    # db_utils.py を直接実行した場合にDBを初期化
    print("データベースを初期化中...")
    init_db()
    print("データベースの初期化完了。")
    # テスト用担当者追加
    # if not get_staff_by_id(1): # 存在しない場合のみ
    #     add_staff("山田 太郎")
    #     add_staff("佐藤 花子")
    #     add_staff("鈴木 一郎")
    #     add_staff("高橋 次郎")
    #     add_staff("田中 三郎")
    # print("テスト担当者を追加しました（初回のみ）。")
