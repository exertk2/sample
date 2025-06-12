import streamlit as st
import pandas as pd
from datetime import datetime, date

# -------------------------------------------------------------------
# アプリの基本設定
# -------------------------------------------------------------------
st.set_page_config(
    page_title="通勤車両管理アプリ",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 通勤車両管理アプリ")
st.write("従業員のマイカー通勤に関する車両情報を登録・管理します。")

# -------------------------------------------------------------------
# データ保存領域の初期化 (st.session_stateを使用)
# -------------------------------------------------------------------
if 'vehicle_df' not in st.session_state:
    # 空のデータフレームを作成
    st.session_state.vehicle_df = pd.DataFrame(columns=[
        '登録日', '氏名', '所属部署', '車種', 'ナンバープレート',
        '保険会社', '証券番号', '対人賠償', '対物賠償',
        '使用目的', '保険開始日', '保険終了日'
    ])

# -------------------------------------------------------------------
# 入力フォーム
# -------------------------------------------------------------------
st.header("📝 新規車両登録フォーム")

# st.formを使うことで、中の要素をまとめて送信できる
with st.form(key='vehicle_form', clear_on_submit=True):
    # 2列レイアウト
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("氏名", placeholder="山田 太郎")
        department = st.text_input("所属部署", placeholder="営業部")
        car_model = st.text_input("車種", placeholder="トヨタ・アクア")
        license_plate = st.text_input("ナンバープレート", placeholder="品川 300 あ 12-34")

    with col2:
        insurance_company = st.text_input("保険会社", placeholder="〇〇損保")
        policy_number = st.text_input("証券番号", placeholder="1234567890")
        # 必須条件の選択肢
        personal_liability = st.selectbox(
            "対人賠償",
            ("無制限", "その他"),
            help="対人賠償が無制限の保険を選択してください。"
        )
        property_damage_liability = st.selectbox(
            "対物賠償",
            ("無制限", "その他"),
            help="対物賠償が無制限の保険を選択してください。"
        )
        usage_purpose = st.selectbox(
            "主な使用目的",
            ("日常・レジャー・通勤", "通勤・業務", "日常・レジャー"),
            help="「通勤」が含まれる目的を選択してください。"
        )
        
    # 3列レイアウト
    col3, col4, col5 = st.columns(3)
    with col3:
        start_date = st.date_input("保険期間（開始日）", value=date.today())
    with col4:
        end_date = st.date_input("保険期間（終了日）", value=date(date.today().year + 1, date.today().month, date.today().day))
    with col5:
         # 保険証券のアップロード（ファイル自体は保存しないサンプル）
        uploaded_file = st.file_uploader(
            "保険証券の画像をアップロード", 
            type=['png', 'jpg', 'jpeg', 'pdf']
        )

    # フォームの送信ボタン
    submit_button = st.form_submit_button(label='登録申請する')


# -------------------------------------------------------------------
# フォーム送信後の処理
# -------------------------------------------------------------------
if submit_button:
    # 入力チェック
    error_messages = []
    if not all([name, department, car_model, license_plate, insurance_company, policy_number]):
        error_messages.append("すべての必須項目を入力してください。")
    if personal_liability != "無制限":
        error_messages.append("対人賠償は「無制限」である必要があります。")
    if property_damage_liability != "無制限":
        error_messages.append("対物賠償は「無制限」である必要があります。")
    if "通勤" not in usage_purpose:
        error_messages.append("使用目的は「通勤」を含むものを選択してください。")
    if uploaded_file is None:
        error_messages.append("保険証券の画像をアップロードしてください。")

    # エラーがなければデータを追加
    if not error_messages:
        # 新しいデータを辞書として作成
        new_data = {
            '登録日': datetime.now().strftime('%Y-%m-%d %H:%M'),
            '氏名': name,
            '所属部署': department,
            '車種': car_model,
            'ナンバープレート': license_plate,
            '保険会社': insurance_company,
            '証券番号': policy_number,
            '対人賠償': personal_liability,
            '対物賠償': property_damage_liability,
            '使用目的': usage_purpose,
            '保険開始日': start_date,
            '保険終了日': end_date,
        }
        # データフレームに追加
        new_df = pd.DataFrame([new_data])
        st.session_state.vehicle_df = pd.concat([st.session_state.vehicle_df, new_df], ignore_index=True)
        st.success("車両情報を正常に登録しました。")
    else:
        # エラーメッセージを表示
        for msg in error_messages:
            st.error(msg)


# --------------------------------
