import streamlit as st
import re
import unicodedata
from typing import List, Tuple
import uuid # For unique ID generation

# 金額表現の文字列を数値（円単位）に変換する関数
def parse_japanese_yen(text: str) -> int:
    """
    日本語の金額表現（例：「1億2,345万6千円」）を数値に変換する。
    """
    text = text.replace(',', '')
    units = {'億': 100_000_000, '万': 10_000, '千': 1_000, '円': 1}
    total_value = 0
    temp_value = 0

    # 大きい単位から処理するための正規表現
    # 例: "1億2345万6789円" -> [('1', '億'), ('2345', '万'), ('6789', '円')]
    pattern = r'(\d+)(億|万|千|円)'
    matches = re.findall(pattern, text)

    current_base = 0
    for num_part, unit_part in matches:
        num = int(num_part)
        unit_value = units[unit_part]
        
        # 例：「10万」「5千」のように、前の単位より小さい単位が来た場合
        # temp_valueを一旦加算し、新しい単位の値をtemp_valueに設定
        if unit_value < current_base:
            total_value += temp_value 
            temp_value = num * unit_value 
        # 例：「1億」「5千万」のように、同じかより大きい単位が来た場合
        # temp_valueをリセットして新しい単位の値を設定
        else:
            total_value += temp_value 
            temp_value = num * unit_value 
        
        current_base = unit_value

    total_value += temp_value

    return total_value

# メインの処理関数
def convert_text_to_kilo_yen(text: str) -> str:
    """
    テキスト内の金額表現を抽出し、条件に応じて千円単位に変換する。
    """
    # 金額表現にマッチする正規表現パターン
    # 例: "1億5,000万円", "10000円" など
    pattern = r'((?:\d[\d,]*)?(?:億|万|千|円))+'
    
    matches = list(re.finditer(pattern, text))
    
    # テキストの末尾から置換処理を行う（インデックスのずれを防ぐため）
    for match in reversed(matches):
        original_string = match.group(0)
        
        try:
            # 金額を数値に変換
            numeric_value = parse_japanese_yen(original_string)
            
            # 千円未満の端数がなく、0円より大きい場合のみ変換
            if numeric_value > 0 and numeric_value % 1000 == 0:
                # 千円単位に変換
                kilo_yen_value = numeric_value // 1000
                # 置換後の文字列を作成（3桁区切りカンマ付き）
                replacement_string = f'{kilo_yen_value:,}千円'
                
                # 元のテキストを置換
                start, end = match.span()
                text = text[:start] + replacement_string + text[end:]

        except (ValueError, IndexError):
            # 金額への変換に失敗した場合は何もしない
            continue
            
    return text

def convert_to_half_width(text: str) -> str:
    """
    全角のアルファベット、数字、括弧を半角に変換する。
    """
    # NFKC正規化を利用して全角英数字、記号の一部を半角に変換
    converted_text = unicodedata.normalize('NFKC', text)
    
    # NFKCで変換されない可能性のある全角括弧を明示的に半角に置換
    converted_text = converted_text.replace('（', '(').replace('）', ')')

    return converted_text

def format_japanese_text(text: str) -> str:
    """
    日本語のテキストを整形する。
    - 句点「。」の後ろが改行でない場合、改行を挿入する。
    - 各行の前後にあるスペースを削除する。
    """
    # 1. 句点「。」の後ろが改行でない場合、改行を挿入する
    # 「。」に続いて改行以外の文字がある場合に、その文字の前に改行を入れる
    # ただし、すでに「。\n」となっている場合は変更しない
    text = re.sub(r'。(?![\n])', '。\n', text)

    # 2. 各行の前後にあるスペースを削除する
    # splitlines()は改行文字を削除してリスト化する
    lines = text.splitlines()
    # 各行の先頭と末尾の空白文字を削除
    stripped_lines = [line.strip() for line in lines]
    
    # 空行を保持したまま再結合
    return "\n".join(stripped_lines)


# --- Streamlit UI ---
st.set_page_config(
    page_title="理事会等議事録整形ツール",
    layout="wide"
)

st.title("仕様説明")
st.write("* 入力された文章の中から「億・万・千・円」を含む金額を抽出し、**千円未満の端数がない金額のみ**を「千円」単位の表記に変換")
st.write("* 全角のアルファベット、数字、括弧を半角に変換")
st.write("* 句点「。」の後ろが改行でない場合、改行を挿入")
st.write("* 各行の前後にあるスペースを削除")

# サンプルテキスト
sample_text = """第１四半期の売上は５０,０００,０００円で、経費は２５,０００千円でした。
（その結果、利益は２,５００万円となりました。）
来期の予算は１億２０００万円を予定していますが、予備費として別途５,１２３円を確保しています。
また、固定資産の減価償却費は１,５００千円です。
合計費用は、約３０,００１,０００円の見込みです。"""

# メインの表示エリアを2カラムに分割
col_input_button, col_output = st.columns(2)

with col_input_button:
    st.markdown("**ここに文章を入力してください**")
    # 入力エリア
    input_text = st.text_area(label="ここに文章を入力してください", value=sample_text, height=250, label_visibility="collapsed")
    
    # 変換実行ボタン
    if st.button("変換を実行する", type="primary"):
        if input_text:
            # 処理順序：
            # 1. 金額変換（元のテキストに対して実行）
            processed_text_step1 = convert_text_to_kilo_yen(input_text)
            
            # 2. 半角変換（金額変換後のテキストに対して実行）
            processed_text_step2 = convert_to_half_width(processed_text_step1)
            
            # 3. テキスト整形（半角変換後のテキストに対して実行）
            final_processed_text = format_japanese_text(processed_text_step2)
            
            # 結果をSession Stateに保存し、再描画時に利用
            st.session_state['final_processed_text'] = final_processed_text
        else:
            st.warning("テキストを入力してください。")
            st.session_state['final_processed_text'] = "" # Clear previous result


with col_output:
    st.markdown("**変換後のテキスト (整形済み)**")
    # Session Stateから結果を取得して表示
    if 'final_processed_text' in st.session_state and st.session_state['final_processed_text']:
        st.code(st.session_state['final_processed_text'], language="text", height=300)
    else:
        st.code("ここに変換結果が表示されます。", language="text", height=300)

    # 変換後テキストをクリップボードにコピーするボタン
    if 'final_processed_text' in st.session_state and st.session_state['final_processed_text']:
        st.markdown("---") # 区切り線
        st.subheader("変換後テキストをクリップボードにコピー")

        # コピー対象のテキストを格納する隠しtextareaのIDを生成
        copy_target_id = str(uuid.uuid4())

        # JavaScriptでクリップボードにコピーするボタンと隠しtextareaを配置
        st.markdown(f"""
            <textarea id="{copy_target_id}" style="position: absolute; left: -9999px;">{st.session_state['final_processed_text']}</textarea>
            <button onclick="
                var copyText = document.getElementById('{copy_target_id}');
                copyText.select();
                document.execCommand('copy');
                alert('テキストがコピーされました！');
            ">変換結果をコピー</button>
        """, unsafe_allow_html=True)
