# app.py
# Streamlitアプリケーション本体

import streamlit as st
import db_utils as db
from datetime import datetime, date, timedelta

# --- データベース初期化 ---
db.init_db()

# --- 定数 ---
VISIT_TYPES = ["予定", "実績"]
MAX_STAFF_PER_OFFICE = 4

# --- ヘルパー関数 ---
def format_date(date_str):
    if date_str:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y年%m月%d日')
        except ValueError:
            return date_str # パースできない場合はそのまま返す
    return "未設定"

# --- UIセクション ---

def staff_management_section():
    st.subheader("担当者マスタ管理")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("##### 新規担当者登録")
        with st.form("new_staff_form", clear_on_submit=True):
            new_staff_name = st.text_input("担当者名", key="new_staff_name_input")
            submitted = st.form_submit_button("登録")
            if submitted and new_staff_name:
                if db.add_staff(new_staff_name):
                    st.success(f"担当者「{new_staff_name}」を登録しました。")
                else:
                    st.error(f"担当者「{new_staff_name}」の登録に失敗しました。既に存在する可能性があります。")
            elif submitted:
                st.warning("担当者名を入力してください。")

    with col2:
        st.markdown("##### 担当者一覧")
        staff_list = db.get_all_staff(active_only=False) # 非アクティブも表示
        if staff_list:
            for staff_member in staff_list:
                staff_id = staff_member['id']
                staff_name = staff_member['name']
                is_active = staff_member['is_active']

                item_col1, item_col2, item_col3 = st.columns([2,2,1])
                with item_col1:
                    st.write(f"{staff_name} ({'有効' if is_active else '無効'})")
                with item_col2:
                    new_name = st.text_input("新しい名前", value=staff_name, key=f"edit_name_{staff_id}")
                    if st.button("名前変更", key=f"update_name_btn_{staff_id}"):
                        if new_name and new_name != staff_name:
                            if db.update_staff_name(staff_id, new_name):
                                st.success(f"担当者名を「{new_name}」に変更しました。")
                                st.rerun()
                            else:
                                st.error("名前の変更に失敗しました。")
                        elif not new_name:
                            st.warning("新しい名前を入力してください。")

                with item_col3:
                    if is_active:
                        if st.button("無効化", key=f"deactivate_btn_{staff_id}"):
                            db.set_staff_active_status(staff_id, False)
                            st.success(f"担当者「{staff_name}」を無効化しました。")
                            st.rerun()
                    else:
                        if st.button("有効化", key=f"activate_btn_{staff_id}"):
                            db.set_staff_active_status(staff_id, True)
                            st.success(f"担当者「{staff_name}」を有効化しました。")
                            st.rerun()
                st.divider()
        else:
            st.info("登録されている担当者はいません。")

def office_assignment_section():
    st.subheader("事業所担当割り当て")

    offices = db.get_all_offices()
    office_names = [office['name'] for office in offices]
    selected_office_name = st.selectbox("事業所を選択", office_names, key="assign_office_select")

    if selected_office_name:
        selected_office = next((office for office in offices if office['name'] == selected_office_name), None)
        if not selected_office:
            st.error("選択された事業所が見つかりません。")
            return

        office_id = selected_office['id']
        st.markdown(f"#### {selected_office_name}事業所の担当者")

        # --- 現在の担当者 ---
        st.markdown("##### 現在の担当者")
        current_assignments = db.get_current_assignments_for_office(office_id)
        active_staff_ids_in_office = [assign['staff_id'] for assign in current_assignments]

        if current_assignments:
            for assignment in current_assignments:
                assign_col1, assign_col2, assign_col3 = st.columns([2,2,1])
                with assign_col1:
                    st.write(f"**{assignment['staff_name']}**")
                with assign_col2:
                    st.write(f"担当開始日: {format_date(assignment['start_date'])}")
                with assign_col3:
                    if st.button("担当終了", key=f"end_assign_{assignment['id']}"):
                        end_date_val = date.today().strftime('%Y-%m-%d')
                        db.end_assignment(assignment['id'], end_date_val)
                        st.success(f"{assignment['staff_name']}さんの{selected_office_name}事業所の担当を終了しました。")
                        st.rerun()
            st.caption(f"現在 {len(current_assignments)}名 / 最大 {MAX_STAFF_PER_OFFICE}名")
        else:
            st.info("現在、この事業所に割り当てられている担当者はいません。")

        # --- 新規担当者割り当て ---
        if len(current_assignments) < MAX_STAFF_PER_OFFICE:
            st.markdown("##### 新規担当者割り当て")
            all_staff = db.get_all_staff(active_only=True)
            # 現在この事業所に割り当てられていないアクティブな担当者のみを候補とする
            available_staff = [s for s in all_staff if s['id'] not in active_staff_ids_in_office]

            if available_staff:
                staff_options = {s['name']: s['id'] for s in available_staff}
                selected_staff_name_to_assign = st.selectbox("担当者を選択して割り当て", list(staff_options.keys()),
                                                             index=None, placeholder="担当者を選択...",
                                                             key=f"assign_staff_select_{office_id}")

                assign_start_date = st.date_input("担当開始日", value=date.today(), key=f"assign_start_date_{office_id}")

                if st.button("割り当て実行", key=f"exec_assign_btn_{office_id}"):
                    if selected_staff_name_to_assign and assign_start_date:
                        staff_id_to_assign = staff_options[selected_staff_name_to_assign]
                        success, message = db.add_assignment(office_id, staff_id_to_assign, assign_start_date.strftime('%Y-%m-%d'))
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("担当者と開始日を選択してください。")
            else:
                st.info("割り当て可能な（現在この事業所を担当していない）アクティブな担当者がいません。先に担当者マスタで担当者を登録・有効化してください。")
        else:
            st.warning(f"この事業所には既に{MAX_STAFF_PER_OFFICE}人の担当者が割り当てられています。新しい担当者を割り当てるには、既存の担当者の割り当てを終了してください。")


        # --- 担当履歴 ---
        st.markdown("##### 担当履歴")
        all_assignments_for_office = db.get_assignments_for_office(office_id)
        if all_assignments_for_office:
            for assignment in all_assignments_for_office:
                end_date_display = format_date(assignment['end_date']) if assignment['end_date'] else "現在担当中"
                st.write(f"{assignment['staff_name']}: {format_date(assignment['start_date'])} 〜 {end_date_display}")
            st.divider()
        else:
            st.info("この事業所の担当履歴はありません。")


def visit_record_section():
    st.subheader("訪問記録入力・確認")

    offices = db.get_all_offices()
    if not offices:
        st.warning("事業所が登録されていません。")
        return

    office_names = [office['name'] for office in offices]
    selected_office_name_visit = st.selectbox("事業所を選択", office_names, key="visit_office_select")

    if selected_office_name_visit:
        selected_office_visit = next((office for office in offices if office['name'] == selected_office_name_visit), None)
        if not selected_office_visit:
            st.error("選択された事業所が見つかりません。")
            return
        office_id_visit = selected_office_visit['id']

        current_assignments_for_visit = db.get_current_assignments_for_office(office_id_visit)
        if not current_assignments_for_visit:
            st.info(f"{selected_office_name_visit}事業所には現在割り当てられている担当者がいません。先に担当者を割り当ててください。")
            return

        assignment_options = {
            f"{assign['staff_name']} (担当期間: {format_date(assign['start_date'])}〜)": assign['id']
            for assign in current_assignments_for_visit
        }
        selected_assignment_display = st.selectbox("担当者（と担当期間）を選択", list(assignment_options.keys()),
                                                   index=None, placeholder="担当者を選択...",
                                                   key=f"visit_assignment_select_{office_id_visit}")

        if selected_assignment_display:
            selected_assignment_id = assignment_options[selected_assignment_display]

            st.markdown("##### 新規訪問記録入力")
            with st.form(f"new_visit_form_{selected_assignment_id}", clear_on_submit=True):
                visit_date_input = st.date_input("訪問日", value=date.today(), key=f"visit_date_{selected_assignment_id}")
                visit_type_input = st.selectbox("種別", VISIT_TYPES, key=f"visit_type_{selected_assignment_id}")
                visit_notes_input = st.text_area("備考・内容", key=f"visit_notes_{selected_assignment_id}")
                submit_visit = st.form_submit_button("記録登録")

                if submit_visit:
                    if visit_date_input and visit_type_input:
                        # 割り当て期間内の日付か簡単なチェック (より厳密には開始日以降、終了日以前か)
                        assignment_details = db.get_assignment_by_id(selected_assignment_id)
                        if assignment_details:
                            start_dt = datetime.strptime(assignment_details['start_date'], '%Y-%m-%d').date()
                            end_dt_str = assignment_details['end_date']
                            end_dt = datetime.strptime(end_dt_str, '%Y-%m-%d').date() if end_dt_str else date.max

                            if not (start_dt <= visit_date_input <= end_dt):
                                st.error(f"訪問日は担当期間内 ({format_date(assignment_details['start_date'])} 〜 {format_date(end_dt_str) if end_dt_str else '現在'}) にしてください。")
                            else:
                                db.add_visit(selected_assignment_id, visit_date_input.strftime('%Y-%m-%d'), visit_type_input, visit_notes_input)
                                st.success("訪問記録を登録しました。")
                                # st.rerun() # フォームクリアのため不要な場合もある
                        else:
                            st.error("割り当て情報が見つかりません。")
                    else:
                        st.warning("訪問日と種別を入力してください。")

            st.markdown("##### 訪問記録一覧")
            visits = db.get_visits_for_assignment(selected_assignment_id)
            if visits:
                for visit in visits:
                    st.markdown(f"""
                    - **{format_date(visit['visit_date'])}** - {visit['type']}
                        - 担当: {visit['staff_name']} ({visit['office_name']})
                        - 内容: {visit['notes'] if visit['notes'] else '(記載なし)'}
                    """)
                    st.divider()
            else:
                st.info("この担当者のこの事業所での訪問記録はありません。")

        # 事業所全体の訪問記録も表示（オプション）
        st.markdown(f"---")
        st.markdown(f"##### {selected_office_name_visit}事業所 全体の訪問記録 (直近)")
        all_office_visits = db.get_visits_for_office(office_id_visit)
        if all_office_visits:
            for visit in all_office_visits:
                 st.markdown(f"""
                    - **{format_date(visit['visit_date'])}** - {visit['type']} by **{visit['staff_name']}**
                        - 内容: {visit['notes'] if visit['notes'] else '(記載なし)'}
                    """)
            st.caption("上記は事業所全体の記録です。担当者ごとの詳細は担当者を選択して確認してください。")
        else:
            st.info(f"{selected_office_name_visit}事業所にはまだ訪問記録がありません。")


def main_dashboard_section():
    st.subheader("メインダッシュボード")
    st.info("ここに各事業所のサマリー情報（現在の担当者、最新の訪問実績など）を表示します。\n（この機能は現在開発中です）")

    offices = db.get_all_offices()
    if not offices:
        st.warning("事業所データがありません。")
        return

    for office in offices:
        office_id = office['id']
        office_name = office['name']
        st.markdown(f"#### {office_name}事業所")

        current_assignments = db.get_current_assignments_for_office(office_id)
        if current_assignments:
            staff_names = ", ".join([assign['staff_name'] for assign in current_assignments])
            st.write(f"現在の担当者: {staff_names}")
        else:
            st.write("現在の担当者: なし")

        # 最新の訪問実績を取得（簡易版）
        office_visits = db.get_visits_for_office(office_id)
        latest_実績_visit = None
        for v in office_visits:
            if v['type'] == '実績':
                if latest_実績_visit is None or datetime.strptime(v['visit_date'], '%Y-%m-%d') > datetime.strptime(latest_実績_visit['visit_date'], '%Y-%m-%d'):
                    latest_実績_visit = v

        if latest_実績_visit:
            st.write(f"最新訪問実績: {format_date(latest_実績_visit['visit_date'])} by {latest_実績_visit['staff_name']} ({latest_実績_visit['notes'] or '詳細なし'})")
        else:
            st.write("最新訪問実績: なし")
        st.divider()


# --- メインアプリケーション ---
def main():
    st.set_page_config(page_title="訪問管理アプリ", layout="wide")
    st.title("事業所訪問 予定・実績管理アプリ")

    menu = ["メインダッシュボード", "担当者マスタ管理", "事業所担当割り当て", "訪問記録"]
    choice = st.sidebar.selectbox("メニュー", menu)

    if choice == "メインダッシュボード":
        main_dashboard_section()
    elif choice == "担当者マスタ管理":
        staff_management_section()
    elif choice == "事業所担当割り当て":
        office_assignment_section()
    elif choice == "訪問記録":
        visit_record_section()

if __name__ == '__main__':
    main()


