import flet as ft
import sqlite3
import hashlib
import os
from datetime import datetime

# --- (Database and Utility functions like init_db, hash_password remain similar) ---
# UPLOAD_DIR = "uploads"
# os.makedirs(UPLOAD_DIR, exist_ok=True)
# ... init_db and hash_password functions ...

class DocumentRegistrationControl(ft.UserControl):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.editing_document_id = None
        self.current_document_name = None
        self.access_list = []
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        page.overlay.append(self.file_picker) # Add file picker to page overlay

        # Form fields
        self.document_name_input = ft.TextField(label="文書名")
        self.issuer_input = ft.TextField(label="発行元")
        self.remarks_input = ft.TextField(label="備考", multiline=True)
        self.current_file_display = ft.Text("")
        self.delete_file_checkbox = ft.Checkbox(label="既存の添付ファイルを削除", on_change=self.on_delete_file_checkbox_change)
        self.uploaded_file_path = None # To store the path of the newly uploaded file

        # Access control fields
        self.access_type_radio_group = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="employee", label="職員番号別"),
                ft.Radio(value="department", label="部署別"),
                ft.Radio(value="committee", label="委員会名等別"),
            ]),
            on_change=self.on_access_type_change
        )
        self.access_value_input = ft.TextField(label="職員番号を入力")
        self.access_list_display = ft.Column() # To display registered accesses

    def on_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files:
            # Handle saving the file to UPLOAD_DIR
            picked_file = e.files[0]
            file_name = picked_file.name
            save_path = os.path.join("uploads", file_name)
            # In a real app, you'd move/copy the file from its temp location to `save_path`
            # For demonstration, we'll just store the path
            self.uploaded_file_path = save_path
            self.current_file_display.value = f"新しい添付ファイル: {file_name}"
            self.current_file_display.update()
            self.page.show_snack_bar(ft.SnackBar(ft.Text(f"ファイル '{file_name}' を選択しました。"), open=True))
        self.page.update()

    def on_delete_file_checkbox_change(self, e):
        # Logic to handle existing file deletion state
        pass # In a real app, you'd manage the file_path_to_save based on this.

    def on_access_type_change(self, e):
        # Update the label of access_value_input based on selection
        if self.access_type_radio_group.value == "employee":
            self.access_value_input.label = "職員番号を入力"
        elif self.access_type_radio_group.value == "department":
            self.access_value_input.label = "部署名を入力"
        elif self.access_type_radio_group.value == "committee":
            self.access_value_input.label = "委員会名等を入力"
        self.access_value_input.update()

    def add_access(self, e):
        access_type = self.access_type_radio_group.value
        access_value = self.access_value_input.value

        if not access_value:
            self.page.show_snack_bar(ft.SnackBar(ft.Text("値を入力してください。"), open=True))
            return

        # (Add database validation here similar to Streamlit's checks for employee_id/committee_name)
        # For simplicity, just appending
        self.access_list.append({'type': access_type, 'value': access_value})
        self.update_access_list_display()
        self.page.show_snack_bar(ft.SnackBar(ft.Text(f"{access_type}: {access_value} を追加しました。"), open=True))
        self.access_value_input.value = "" # Clear input
        self.access_value_input.update()

    def remove_access(self, index):
        self.access_list.pop(index)
        self.update_access_list_display()

    def update_access_list_display(self):
        self.access_list_display.controls.clear()
        if self.access_list:
            self.access_list_display.controls.append(ft.Text("登録済み閲覧先:"))
            for i, access in enumerate(self.access_list):
                self.access_list_display.controls.append(
                    ft.Row([
                        ft.Text(f"- {access['type']}: {access['value']}"),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_color="red",
                            on_click=lambda e, idx=i: self.remove_access(idx)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
        self.access_list_display.update()

    def load_document_for_editing(self, doc_id):
        self.editing_document_id = doc_id
        # (Database query to fetch document data and access list)
        # Populate form fields and access_list based on fetched data
        # Example:
        conn = sqlite3.connect('document_management.db')
        c = conn.cursor()
        c.execute("SELECT document_name, issuer, remarks, file_path FROM documents WHERE document_id = ?", (doc_id,))
        doc_data = c.fetchone()
        if doc_data:
            self.document_name_input.value = doc_data[0]
            self.issuer_input.value = doc_data[1]
            self.remarks_input.value = doc_data[2]
            self.uploaded_file_path = doc_data[3] # Current file path
            if self.uploaded_file_path and os.path.exists(self.uploaded_file_path):
                self.current_file_display.value = f"現在の添付ファイル: {os.path.basename(self.uploaded_file_path)}"
            else:
                self.current_file_display.value = "添付ファイルなし"
        c.execute("SELECT access_type, access_value FROM document_access WHERE document_id = ?", (doc_id,))
        existing_accesses = c.fetchall()
        self.access_list = [{'type': acc[0], 'value': acc[1]} for acc in existing_accesses]
        conn.close()

        self.current_document_name = self.document_name_input.value
        self.update_access_list_display()
        self.update() # Update the entire control after loading data

    def clear_form(self):
        self.editing_document_id = None
        self.document_name_input.value = ""
        self.issuer_input.value = ""
        self.remarks_input.value = ""
        self.current_file_display.value = ""
        self.uploaded_file_path = None
        self.delete_file_checkbox.value = False
        self.access_list = []
        self.current_document_name = None
        self.update_access_list_display()
        self.update()

    def submit_document(self, e):
        # (Database logic for INSERT/UPDATE document and access_list)
        # This will be more complex due to file handling and transaction management
        doc_name = self.document_name_input.value
        issuer = self.issuer_input.value
        remarks = self.remarks_input.value
        file_path_to_save = self.uploaded_file_path

        if self.delete_file_checkbox.value and self.uploaded_file_path and os.path.exists(self.uploaded_file_path):
            os.remove(self.uploaded_file_path)
            file_path_to_save = None

        conn = sqlite3.connect('document_management.db')
        c = conn.cursor()

        if self.editing_document_id:
            c.execute("UPDATE documents SET document_name = ?, issuer = ?, remarks = ?, file_path = ? WHERE document_id = ?",
                      (doc_name, issuer, remarks, file_path_to_save, self.editing_document_id))
            document_id = self.editing_document_id
            self.page.show_snack_bar(ft.SnackBar(ft.Text(f"文書番号 {document_id} を更新しました。"), open=True))
        else:
            c.execute("INSERT INTO documents (document_name, issuer, remarks, file_path) VALUES (?, ?, ?, ?)",
                      (doc_name, issuer, remarks, file_path_to_save))
            document_id = c.lastrowid
            self.page.show_snack_bar(ft.SnackBar(ft.Text(f"文書 '{doc_name}' を文書番号 {document_id} で登録しました。"), open=True))
            self.editing_document_id = document_id # Set for potential access registration
            self.current_document_name = doc_name

        # Delete existing accesses and re-insert
        c.execute("DELETE FROM document_access WHERE document_id = ?", (document_id,))
        for access in self.access_list:
            c.execute("INSERT INTO document_access (document_id, access_type, access_value) VALUES (?, ?, ?)",
                      (document_id, access['type'], access['value']))
        conn.commit()
        conn.close()
        self.page.show_snack_bar(ft.SnackBar(ft.Text("閲覧先を保存しました。"), open=True))

        # Clear form and access list after submission
        self.clear_form()
        # You might want to navigate to document list here or reload doc options
        self.page.update()

    def build(self):
        # Fetch existing documents for the dropdown
        conn = sqlite3.connect('document_management.db')
        c = conn.cursor()
        c.execute("SELECT document_id, document_name FROM documents")
        existing_documents = c.fetchall()
        conn.close()
        doc_options = [ft.dropdown.Option("新規文書", key="new")] + \
                      [ft.dropdown.Option(f"{doc[0]}: {doc[1]}", key=str(doc[0])) for doc in existing_documents]

        self.doc_select_dropdown = ft.Dropdown(
            options=doc_options,
            label="編集する文書を選択、または新規文書を作成",
            on_change=self.on_doc_select_change
        )
        
        return ft.Column([
            ft.Text("文書登録・編集", size=20, weight=ft.FontWeight.BOLD),
            self.doc_select_dropdown,
            ft.Divider(),
            self.document_name_input,
            self.issuer_input,
            self.remarks_input,
            self.current_file_display,
            self.delete_file_checkbox,
            ft.ElevatedButton("新しい添付ファイルを選択", on_click=lambda e: self.file_picker.pick_files()),
            ft.ElevatedButton(
                text="文書を登録" if not self.editing_document_id else "文書を更新",
                on_click=self.submit_document
            ),
            ft.Divider(),
            ft.Text(f"閲覧先登録 (文書番号: {self.editing_document_id if self.editing_document_id else '未選択'}, 文書名: {self.current_document_name if self.current_document_name else '未選択'})", size=16),
            ft.Visibility(
                visible=self.editing_document_id is not None, # Show only if a document is selected/newly created
                content=ft.Column([
                    self.access_type_radio_group,
                    self.access_value_input,
                    ft.ElevatedButton("閲覧先を追加", on_click=self.add_access),
                    self.access_list_display,
                ])
            ),
            ft.Visibility(
                visible=self.editing_document_id is None,
                content=ft.Text("文書を登録または選択すると、閲覧先を登録できます。", italic=True)
            )
        ])

    def on_doc_select_change(self, e):
        selected_key = self.doc_select_dropdown.value
        if selected_key == "new":
            self.clear_form()
            self.page.show_snack_bar(ft.SnackBar(ft.Text("新規文書を作成します。"), open=True))
        else:
            doc_id = int(selected_key.split(":")[0])
            self.load_document_for_editing(doc_id)
            self.page.show_snack_bar(ft.SnackBar(ft.Text(f"文書番号 {doc_id} を編集します。"), open=True))
        self.page.update() # Update the page to reflect changes

def main(page: ft.Page):
    page.title = "文書管理システム"
    page.vertical_alignment = ft.CrossAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START
    init_db()

    # Initial view (e.g., document registration)
    doc_reg_control = DocumentRegistrationControl(page)

    # Navigation rail or app bar for different sections
    page.add(
        ft.Row([
            ft.NavigationRail(
                selected_index=0,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=100,
                min_extended_width=200,
                extended=True,
                group_alignment=-0.9,
                destinations=[
                    ft.NavigationRailDestination(
                        icon=ft.icons.UPLOAD_FILE,
                        selected_icon=ft.icons.UPLOAD_FILE_SHARP,
                        label="文書登録"
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.icons.LIST_ALT,
                        selected_icon=ft.icons.LIST_ALT_SHARP,
                        label="文書一覧"
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.icons.PERSON_ADD,
                        selected_icon=ft.icons.PERSON_ADD_SHARP,
                        label="社員登録"
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.icons.GROUP,
                        selected_icon=ft.icons.GROUP_SHARP,
                        label="社員一覧"
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.icons.ACCOUNT_TREE,
                        selected_icon=ft.icons.ACCOUNT_TREE_SHARP,
                        label="委員会等登録"
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.icons.VIEW_LIST,
                        selected_icon=ft.icons.VIEW_LIST_SHARP,
                        label="委員会等一覧"
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.icons.HISTORY,
                        selected_icon=ft.icons.HISTORY_SHARP,
                        label="閲覧ログ一覧"
                    ),
                ],
                on_change=lambda e: change_view(e.control.selected_index)
            ),
            ft.VerticalDivider(width=1),
            ft.Container(content=doc_reg_control, expand=True) # Main content area
        ],
        expand=True)
    )

    def change_view(index):
        # Logic to swap the content in the main content area based on navigation selection
        if index == 0:
            page.controls[0].controls[2].content = doc_reg_control
        elif index == 1:
            # page.controls[0].controls[2].content = DocumentListControl(page) # You'd create a similar control for each view
            page.controls[0].controls[2].content = ft.Text("文書一覧 (実装予定)")
        elif index == 2:
            page.controls[0].controls[2].content = ft.Text("社員登録 (実装予定)")
        # ... and so on for other views
        page.update()

if __name__ == "__main__":
    ft.app(target=main)
