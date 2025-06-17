import sqlite3
import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import configparser

# --- 設定ファイル (INI) の管理 ---
CONFIG_FILE = 'config.ini'
SECTION_NAME = 'DatabasePaths'
CSV_FILE_PATH = 'data.csv' # デフォルトのCSVファイルパス

def load_config():
    """設定ファイルからデータベースパスを読み込む"""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    if SECTION_NAME in config:
        return config[SECTION_NAME].get('files', '').split(';')
    return []

def save_config(db_paths):
    """データベースパスを設定ファイルに保存する"""
    config = configparser.ConfigParser()
    config[SECTION_NAME] = {'files': ';'.join(db_paths)}
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        print(f"設定を '{CONFIG_FILE}' に保存しました。")
    except IOError as e:
        messagebox.showerror("エラー", f"設定ファイルの書き込みに失敗しました: {e}")

# --- SQLite デリートインサート処理 ---
def delete_insert_from_csv_to_sqlite(db_files, table_name, csv_file_path, log_widget):
    """
    複数のSQLiteデータベース内の同一テーブルに対して、CSVファイルの内容で
    データをデリートインサートします。
    ログメッセージをlog_widgetに出力します。
    """
    log_widget.insert(tk.END, f"CSVファイル '{csv_file_path}' を読み込み中...\n")
    log_widget.see(tk.END)

    if not os.path.exists(csv_file_path):
        log_widget.insert(tk.END, f"エラー: CSVファイル '{csv_file_path}' が見つかりません。\n")
        log_widget.see(tk.END)
        return False

    # CSVファイルからデータを読み込む
    rows_to_insert = []
    header = []
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                # CSVから読み込んだ行の要素数がヘッダーの数と一致するか確認
                if len(row) == len(header):
                    rows_to_insert.append(row)
                else:
                    log_widget.insert(tk.END, f"警告: CSVの行 '{row}' のカラム数がヘッダーと一致しません。スキップします。\n")
        log_widget.insert(tk.END, f"CSVファイルから {len(rows_to_insert)} 行のデータを読み込みました。\n")
        log_widget.see(tk.END)
    except Exception as e:
        log_widget.insert(tk.END, f"エラー: CSVファイルの読み込み中にエラーが発生しました: {e}\n")
        log_widget.see(tk.END)
        return False

    # 各データベースに対してデリートインサート処理を実行
    success = True
    for db_file in db_files:
        conn = None
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            log_widget.insert(tk.END, f"\n--- データベース '{db_file}' を処理中 ---\n")
            log_widget.see(tk.END)

            # 既存データを全て削除 (DELETE)
            log_widget.insert(tk.END, f"  テーブル '{table_name}' から既存データを削除しています...\n")
            log_widget.see(tk.END)
            cursor.execute(f"DELETE FROM {table_name}")
            log_widget.insert(tk.END, f"  削除完了。影響を受けた行数: {cursor.rowcount}\n")
            log_widget.see(tk.END)

            # 新しいデータを挿入 (INSERT)
            if rows_to_insert:
                if not header: # ヘッダーが空の場合は処理しない
                    log_widget.insert(tk.END, "エラー: CSVヘッダーが読み込めませんでした。挿入をスキップします。\n")
                    success = False
                    continue

                placeholders = ', '.join(['?'] * len(header))
                insert_sql = f"INSERT INTO {table_name} ({','.join(header)}) VALUES ({placeholders})"

                log_widget.insert(tk.END, f"  テーブル '{table_name}' に新しいデータを挿入しています...\n")
                log_widget.see(tk.END)
                cursor.executemany(insert_sql, rows_to_insert)
                log_widget.insert(tk.END, f"  挿入完了。挿入された行数: {cursor.rowcount}\n")
                log_widget.see(tk.END)
            else:
                log_widget.insert(tk.END, f"  CSVファイルに挿入するデータがありませんでした。\n")

            conn.commit()
            log_widget.insert(tk.END, f"  データベース '{db_file}' の更新が完了しました。\n")
            log_widget.see(tk.END)

        except sqlite3.Error as e:
            log_widget.insert(tk.END, f"エラー: データベース '{db_file}' の処理中にエラーが発生しました: {e}\n")
            log_widget.see(tk.END)
            success = False
        except Exception as e:
            log_widget.insert(tk.END, f"予期せぬエラーが発生しました: {e}\n")
            log_widget.see(tk.END)
            success = False
        finally:
            if conn:
                conn.close()
    return success

# --- Tkinter GUI ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite デリートインサートツール")

        self.db_files = [] # 選択されたDBファイルのリスト
        self.target_table = tk.StringVar(value="my_table") # デフォルトのテーブル名

        self.create_widgets()
        self.load_previous_files()

    def create_widgets(self):
        # フレームの作成
        frame_top = tk.Frame(self.root, padx=10, pady=10)
        frame_top.pack(fill=tk.X)

        frame_middle = tk.Frame(self.root, padx=10, pady=10)
        frame_middle.pack(fill=tk.BOTH, expand=True)

        frame_bottom = tk.Frame(self.root, padx=10, pady=10)
        frame_bottom.pack(fill=tk.X)

        # データベースファイル選択
        tk.Label(frame_top, text="SQLiteデータベースファイル:").pack(anchor=tk.W)
        self.file_list_text = scrolledtext.ScrolledText(frame_top, height=5, wrap=tk.WORD, state='disabled')
        self.file_list_text.pack(fill=tk.X, pady=5)
        self.select_button = tk.Button(frame_top, text="ファイルを選択", command=self.select_db_files)
        self.select_button.pack(pady=5)

        # テーブル名入力
        tk.Label(frame_top, text="対象テーブル名:").pack(anchor=tk.W, pady=(10, 0))
        self.table_entry = tk.Entry(frame_top, textvariable=self.target_table, width=50)
        self.table_entry.pack(pady=5)

        # デリートインサート実行ボタン
        self.run_button = tk.Button(frame_middle, text="デリートインサートを実行", command=self.run_delete_insert, height=2, bg='lightblue')
        self.run_button.pack(pady=20)

        # ログ出力エリア
        tk.Label(frame_bottom, text="ログ:").pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(frame_bottom, height=10, wrap=tk.WORD, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)

    def select_db_files(self):
        """ファイル選択ダイアログを表示し、選択されたファイルをリストに格納、GUIに表示"""
        filetypes = [("SQLite files", "*.sqlite *.db *.sqlite3"), ("All files", "*.*")]
        selected_files = filedialog.askopenfilenames(
            title="SQLiteデータベースファイルを選択",
            filetypes=filetypes
        )
        if selected_files:
            self.db_files = list(selected_files)
            self.update_file_list_display()
            save_config(self.db_files) # 選択後、すぐに設定に保存

    def update_file_list_display(self):
        """選択されたファイルリストをGUIのScrolledTextに表示する"""
        self.file_list_text.config(state='normal')
        self.file_list_text.delete(1.0, tk.END)
        if self.db_files:
            for f in self.db_files:
                self.file_list_text.insert(tk.END, f + "\n")
        else:
            self.file_list_text.insert(tk.END, "ファイルが選択されていません。\n")
        self.file_list_text.config(state='disabled')
        self.file_list_text.see(tk.END) # 最下部を表示

    def load_previous_files(self):
        """INIファイルから前回のファイルパスを読み込み、GUIに表示する"""
        loaded_files = load_config()
        if loaded_files:
            # 存在しないファイルパスを除外
            self.db_files = [f for f in loaded_files if os.path.exists(f)]
            if len(loaded_files) != len(self.db_files):
                self.log_text.config(state='normal')
                self.log_text.insert(tk.END, "警告: 前回の設定ファイルから一部のファイルが見つかりませんでした。リストを更新しました。\n")
                self.log_text.config(state='disabled')
                save_config(self.db_files) # 存在しないファイルを除外して保存し直す
            self.update_file_list_display()
        else:
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, "設定ファイルから前回のデータベースパスが見つかりませんでした。\n")
            self.log_text.config(state='disabled')


    def run_delete_insert(self):
        """デリートインサート処理を実行する"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END) # ログをクリア
        self.log_text.insert(tk.END, "--- デリートインサート処理を開始します ---\n")
        self.log_text.config(state='disabled')

        if not self.db_files:
            messagebox.showwarning("警告", "SQLiteデータベースファイルが選択されていません。")
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, "エラー: データベースファイルが選択されていません。\n")
            self.log_text.config(state='disabled')
            return

        table = self.target_table.get().strip()
        if not table:
            messagebox.showwarning("警告", "対象テーブル名が入力されていません。")
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, "エラー: 対象テーブル名が入力されていません。\n")
            self.log_text.config(state='disabled')
            return

        if not os.path.exists(CSV_FILE_PATH):
            messagebox.showerror("エラー", f"CSVファイル '{CSV_FILE_PATH}' が見つかりません。")
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, f"エラー: CSVファイル '{CSV_FILE_PATH}' が見つかりません。\n")
            self.log_text.config(state='disabled')
            return

        # 実行中にボタンを無効化
        self.run_button.config(state='disabled')
        self.select_button.config(state='disabled')

        # デリートインサート処理を実行
        success = delete_insert_from_csv_to_sqlite(self.db_files, table, CSV_FILE_PATH, self.log_text)

        # 実行後にボタンを有効化
        self.run_button.config(state='normal')
        self.select_button.config(state='normal')

        self.log_text.config(state='normal')
        if success:
            self.log_text.insert(tk.END, "\n--- デリートインサート処理が完了しました ---\n")
            messagebox.showinfo("完了", "デリートインサート処理が正常に完了しました。")
        else:
            self.log_text.insert(tk.END, "\n--- デリートインサート処理中にエラーが発生しました ---\n")
            messagebox.showerror("エラー", "デリートインサート処理中にエラーが発生しました。ログを確認してください。")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END) # 最下部を表示

# --- メイン処理 ---
if __name__ == '__main__':
    # テスト用のDBファイル作成（初回起動時のみ必要、または手動で作成）
    # この部分でGUIで選択する前にダミーのSQLiteファイルを作成しておくとテストしやすいです。
    sample_db_names = ['sample_db1.sqlite', 'sample_db2.sqlite']
    for db_name in sample_db_names:
        if not os.path.exists(db_name):
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS my_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    value TEXT
                )
            ''')
            cursor.execute("INSERT INTO my_table (name, value) VALUES ('InitialA', 'OldVal1')")
            cursor.execute("INSERT INTO my_table (name, value) VALUES ('InitialB', 'OldVal2')")
            conn.commit()
            conn.close()
            print(f"テスト用データベース '{db_name}' を作成しました。")

    root = tk.Tk()
    app = App(root)
    root.mainloop()

