import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

st.set_page_config(layout="wide", page_title="緯度経度取得")

# Nominatim Geocodingサービスの初期化
# user_agent は任意のユニークな文字列を設定してください。
# セッションごとに新しいgeolocatorインスタンスを作成することで、独立性を確保
def get_geolocator():
    return Nominatim(user_agent="my-school-locator-app-{}".format(time.time()))

@st.cache_data
def get_coordinates(school_name, unique_id):
    """
    地名から緯度と経度を取得する関数。
    Nominatimを使用し、取得できない場合はNoneを返す。
    レート制限に配慮するため、取得後には短い間隔で待機する。
    unique_idはキャッシュのキーとして使用され、各リクエストが独立していることを保証します。
    """
    geolocator = get_geolocator() # 各呼び出しで新しいgeolocatorインスタンスを取得
    try:
        location = geolocator.geocode(school_name, timeout=10)
        if location:
            return {"name": school_name, "lat": location.latitude, "lon": location.longitude}
        else:
            return None
    except GeocoderTimedOut:
        st.error(f"'{school_name}' の座標取得中にタイムアウトしました。再試行してください。")
        return None
    except GeocoderServiceError as e:
        st.error(f"座標取得サービスエラー: {e}。後でもう一度お試しください。")
        return None
    finally:
        # Nominatimの利用規約に準拠するため、リクエスト間に短時間の遅延を入れる
        # 通常、1秒に1回以上のリクエストは推奨されません。
        time.sleep(2) # 2秒に延長して、より確実にレート制限を遵守

def display_schools_on_map(school_data):
    """
    地名、緯度、経度のリストを受け取り、Streamlitで表示する。
    """
    if not school_data:
        st.warning("表示する地名データがありません。")
        return

    # データフレームを作成
    df = pd.DataFrame(school_data)

    st.write("### 結果")

    st.dataframe(df)

if __name__ == "__main__":
    st.title("地名の緯度経度取得")

    # ユーザーが学校名を入力できるテキストエリア
    school_names_input = st.text_area(
        "地名を1行に1つ入力してください。取得できないときは市区町村名、都道府県名、日本 などを付け足しましょう。",
        "岸良学園 肝付町"
    )

    # 入力された学校名をリストに変換
    input_school_names = [name.strip() for name in school_names_input.split('\n') if name.strip()]

    processed_schools = []
    if st.button("座標を取得して表示"):
        if input_school_names:
            progress_bar = st.progress(0)
            total_schools = len(input_school_names)
            for i, name in enumerate(input_school_names):
                # unique_idを渡すことで、st.cache_dataが各呼び出しを別々にキャッシュするようにする
                coords = get_coordinates(name, i) # i を unique_id として渡す
                if coords:
                    processed_schools.append(coords)
                progress_bar.progress((i + 1) / total_schools)

            if processed_schools:
                display_schools_on_map(processed_schools)
            else:
                st.info("指定された地名の座標を一つも取得できませんでした。")
        else:
            st.warning("地名を入力してください。")

    st.write("---")
    st.write("**注意:**")
    st.write("Nominatimは無料のサービスですが、過度なリクエストは制限されることがあります。")
    st.write("利用規約（[https://nominatim.org/release-docs/latest/api/Overview/#api-usage-policy](https://nominatim.org/release-docs/latest/api/Overview/#api-usage-policy)）を確認し、遵守してください。")
    st.info("特に、1秒に1回以上のリクエストは避けるべきです。本コードでは2秒に1回のリクエストで制限しています。")
