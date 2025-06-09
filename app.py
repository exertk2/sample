import streamlit as st
import pandas as pd

# --- 1. データ準備 (本来はデータベースで管理) ---
def setup_initial_data():
    """デモ用のユーザー、考課設定、評価データを準備します。"""
    # ユーザー情報: {ユーザーID: {name: 名前, password: パスワード}}
    users = {
        "manager01": {"name": "鈴木 一郎 (部長)", "password": "a"},
        "leader01": {"name": "佐藤 次郎 (課長)", "password": "b"},
        "member01": {"name": "田中 三郎 (メンバー)", "password": "c"},
        "member02": {"name": "高橋 四郎 (メンバー)", "password": "d"}
    }

    # 考課者設定: {被評価者ID: [考課者ID1, 考課者ID2, ...]}
    # 田中さんは鈴木部長と佐藤課長から評価される
    # 高橋さんも鈴木部長と佐藤課長から評価される
    # 佐藤課長は鈴木部長から評価される
    evaluators_map = {
        "member01": ["manager01", "leader01"],
        "member02": ["manager01", "leader01"],
        "leader01": ["manager01"]
    }

    # 評価項目
    evaluation_items = {
        "人間力": ["協調性", "責任感", "積極性"],
        "仕事力": ["業務遂行力", "課題解決力", "企画・提案力"]
    }

    # 評価データ (ここに評価結果が蓄積される)
    # 構造: {被評価者ID: {考課者ID: {項目: {score: 5, comment: "..."}}}}
    evaluations = {}

    return users, evaluators_map, evaluation_items, evaluations

# --- 2. Streamlitのセッション初期化 ---
def initialize_session_state():
    """アプリケーションの初回起動時にセッションを初期化します。"""
    if 'initialized' not in st.session_state:
        users, evaluators_map, items, evaluations = setup_initial_data()
        st.session_state.users = users
        st.session_state.evaluators_map = evaluators_map
        st.session_state.evaluation_items = items
        st.session_state.evaluations = evaluations
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.session_state.initialized = True
        
        # デモ用に田中さんへの鈴木部長からの評価を事前に入れておく
        st.session_state.evaluations.setdefault("member01", {})["manager01"] = {
            "協調性": {"score": 5, "comment": "チームの中心として素晴らしい活躍を見せた。"},
            "責任感": {"score": 4, "comment": "担当案件を最後までやり遂げる力がある。"},
            "積極性": {"score": 4, "comment": "定例会での改善提案も的確だった。"},
            "業務遂行力": {"score": 5, "comment": "常に期待以上の成果を出しており、安心して任せられる。"},
            "課題解決力": {"score": 4, "comment": "発生した問題にも冷静に対処し、解決に導いた。"},
            "企画・提案力": {"score": 3, "comment": "もう少し広い視野での提案ができるとさらに良い。"}
        }

# --- 3. ログイン画面 ---
def login_screen():
    """ログイン画面を表示し、認証処理を行います。"""
    st.title("人事考課アプリ")
    
    user_id = st.text_input("ユーザーID")
    password = st.text_input("パスワード", type="password")

    if st.button("ログイン"):
        users = st.session_state.users
        if user_id in users and users[user_id]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.session_state.user_name = users[user_id]["name"]
            st.rerun()  # ログイン成功したら再実行してメイン画面へ
        else:
            st.error("ユーザーIDまたはパスワードが正しくありません。")

# --- 4. 評価入力ページ ---
def show_evaluation_input_page():
    """考課者が被評価者の評価を入力するページです。"""
    st.header(f"評価入力")
    
    current_user_id = st.session_state.user_id
    
    # 自分が考課者になっている被評価者をリストアップ
    targets_to_evaluate = [
        target_id for target_id, evaluators in st.session_state.evaluators_map.items()
        if current_user_id in evaluators
    ]

    if not targets_to_evaluate:
        st.info("あなたが評価する対象者はいません。")
        return

    # プルダウンで評価対象を選択
    target_names = {uid: st.session_state.users[uid]['name'] for uid in targets_to_evaluate}
    selected_target_name = st.selectbox(
        "評価する社員を選択してください",
        options=list(target_names.values())
    )
    
    # 選択された名前からIDを逆引き
    selected_target_id = [uid for uid, name in target_names.items() if name == selected_target_name][0]

    st.subheader(f"【{selected_target_name}】さんの評価")
    
    # 既に入力済みかチェックし、メッセージを表示
    if st.session_state.evaluations.get(selected_target_id, {}).get(current_user_id):
        st.warning("この社員の評価は既に入力済みです。修正する場合は、再度入力して提出してください。")

    # 評価入力フォーム
    with st.form(key=f"eval_form_{selected_target_id}"):
        scores = {}
        comments = {}
        items = st.session_state.evaluation_items
        
        for category, item_list in items.items():
            st.markdown(f"#### {category}")
            for item in item_list:
                cols = st.columns([2, 3, 4])
                with cols[0]:
                    st.write(item)
                with cols[1]:
                    scores[item] = st.radio(
                        "点数", options=[1, 2, 3, 4, 5], horizontal=True,
                        label_visibility="collapsed", key=f"score_{selected_target_id}_{item}"
                    )
                with cols[2]:
                    comments[item] = st.text_input(
                        "コメント", placeholder="具体的な行動やエピソードを記入",
                        label_visibility="collapsed", key=f"comment_{selected_target_id}_{item}"
                    )
        
        submitted = st.form_submit_button("この内容で評価を提出する")

        if submitted:
            evaluation_data = {item: {"score": scores[item], "comment": comments[item]} for item in scores}
            st.session_state.evaluations.setdefault(selected_target_id, {})[current_user_id] = evaluation_data
            st.success(f"{selected_target_name}さんの評価を保存しました。")

# --- 5. 自分の評価閲覧ページ ---
def show_my_evaluation_page():
    """ログインユーザー自身の評価結果を表示するページです。"""
    st.header("あなたの評価")
    
    my_id = st.session_state.user_id
    my_evaluations = st.session_state.evaluations.get(my_id)
    
    if not my_evaluations:
        st.info("あなたの評価はまだ入力されていません。")
        return
        
    all_evaluators_for_me = st.session_state.evaluators_map.get(my_id, [])
    
    # 全員の評価が完了しているかチェック
    if len(my_evaluations) < len(all_evaluators_for_me):
        st.warning(f"全考課者({len(all_evaluators_for_me)}名)の評価が完了していません。現在{len(my_evaluations)}名が入力済みです。")

    # --- データフレームを作成して評価を一覧表示 ---
    items_flat = [item for sublist in st.session_state.evaluation_items.values() for item in sublist]
    
    # 考課者ごとのスコアとコメントを収集
    scores_by_item = {item: [] for item in items_flat}
    comments_by_evaluator = {}
    evaluator_names = {eid: st.session_state.users[eid]['name'] for eid in my_evaluations.keys()}

    for evaluator_id, eval_data in my_evaluations.items():
        evaluator_name = evaluator_names[evaluator_id]
        comments_by_evaluator[evaluator_name] = {}
        for item, data in eval_data.items():
            if item in scores_by_item:
                scores_by_item[item].append(data['score'])
                comments_by_evaluator[evaluator_name][item] = data['comment']

    # 表データを作成
    results_list = []
    total_avg_score = 0
    for category, item_list in st.session_state.evaluation_items.items():
        for item in item_list:
            scores = scores_by_item.get(item, [])
            avg_score = sum(scores) / len(scores) if scores else 0
            total_avg_score += avg_score
            
            row = {"カテゴリ": category, "評価項目": item}
            for i, evaluator_id in enumerate(my_evaluations.keys()):
                evaluator_name = evaluator_names[evaluator_id]
                score = my_evaluations[evaluator_id].get(item, {}).get('score', '未')
                row[f"考課者{i+1} ({evaluator_name.split(' ')[0]})"] = score
            row["平均点"] = f"{avg_score:.2f}"
            results_list.append(row)

    df_results = pd.DataFrame(results_list)

    # --- 画面表示 ---
    st.subheader(f"総合評価")
    max_score = len(items_flat) * 5
    st.metric(label="合計平均点", value=f"{total_avg_score:.2f} / {max_score:.0f}")

    st.subheader("評価詳細")
    st.dataframe(df_results, hide_index=True)

    st.subheader("考課者からのコメント")
    for evaluator_name, comments in comments_by_evaluator.items():
        with st.expander(f"考課者: {evaluator_name} からのコメント"):
            for item, comment in comments.items():
                if comment:
                    st.markdown(f"**{item}**: {comment}")

# --- 6. メインロジック ---
def main():
    """アプリケーションのメインコントローラー"""
    initialize_session_state()

    if not st.session_state.get("logged_in"):
        login_screen()
    else:
        st.sidebar.title("メニュー")
        st.sidebar.write(f"ようこそ、{st.session_state.user_name}さん")

        # 考課者権限があるかチェック
        is_evaluator = any(st.session_state.user_id in v for v in st.session_state.evaluators_map.values())
        
        menu_options = ["あなたの評価"]
        if is_evaluator:
            menu_options.append("評価入力")

        page = st.sidebar.radio("ページを選択", menu_options)
        
        if page == "あなたの評価":
            show_my_evaluation_page()
        elif page == "評価入力":
            show_evaluation_input_page()
        
        if st.sidebar.button("ログアウト"):
            # セッションをクリアしてログアウト
            for key in list(st.session_state.keys()):
                if key != 'initialized': # 初期化フラグ以外を消す
                    del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
