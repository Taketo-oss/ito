import streamlit as st
from supabase import create_client, Client
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 初期設定 & Supabase接続 ---
# Streamlit Cloudの「Settings > Secrets」に以下の情報を登録してください
if "supabase" not in st.session_state:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    st.session_state.supabase = create_client(url, key)

supabase = st.session_state.supabase
ROOM_ID = 1

# 5秒ごとに自動更新
st_autorefresh(interval=5000, key="datarefresh")

# --- 2. プレイヤー情報の管理 ---
if "my_name" not in st.session_state:
    st.session_state.my_name = ""

if not st.session_state.my_name:
    st.title("ito")
    name = st.text_input("あなたの表示名を入力してください")
    if st.button("参加する"):
        if name:
            st.session_state.my_name = name
            st.rerun()
        else:
            st.warning("名前を入力してください")
    st.stop()

# --- 3. データ同期関数 ---
def get_game_data():
    res = supabase.table("ito_rooms").select("*").eq("id", ROOM_ID).execute()
    return res.data[0] if res.data else None

def update_game_data(updates):
    supabase.table("ito_rooms").update(updates).eq("id", ROOM_ID).execute()

data = get_game_data()

# --- 4. 画面表示 (SETUPフェーズ) ---
if data['status'] == "SETUP":
    st.title("⚙️ ゲーム設定 (待機中)")
    st.write(f"参加者: **{st.session_state.my_name}**")
    
    with st.expander("ホスト設定（誰か一人が操作してください）"):
        topic = st.text_input("お題を入力", placeholder="例：持っていたらモテそうなもの")
        hand_count = st.number_input("各自の手札枚数", min_value=1, value=1)
        if st.button("このお題でゲーム開始！"):
            update_game_data({
                "topic": topic,
                "table_data": [],
                "status": "PLAYING"
            })
            st.rerun()

# --- 5. 画面表示 (PLAYINGフェーズ) ---
elif data['status'] == "PLAYING":
    st.title(f"🃏 お題：{data['topic']}")
    table = data['table_data']
    
    # 手札の配布（まだ持っていない場合のみ）
    if "my_hand" not in st.session_state or not st.session_state.my_hand:
        # 本来は重複を避けるべきだが、簡易版として1-100からランダム
        st.session_state.my_hand = [random.randint(1, 100) for _ in range(1)] # 枚数固定(簡易)

    st.sidebar.markdown(f"👤 プレイヤー: **{st.session_state.my_name}**")
    
    # カード提出フォーム
    if st.session_state.my_hand:
        current_num = st.session_state.my_hand[0]
        st.info(f"あなたの数字は **{current_num}** です")
        card_name = st.text_input("言葉で表現してください", placeholder="例：オムライス")
        
        if card_name:
            st.write("どこに置きますか？")
            cols = st.columns(len(table) + 1)
            for i in range(len(table) + 1):
                label = "ここ"
                if len(table) == 0: label = "真ん中に置く"
                elif i == 0: label = "一番左"
                elif i == len(table): label = "一番右"
                
                if cols[i].button(label, key=f"pos_{i}"):
                    table.insert(i, {
                        "name": card_name, 
                        "player": st.session_state.my_name, 
                        "num": current_num
                    })
                    st.session_state.my_hand.pop(0)
                    update_game_data({"table_data": table})
                    st.rerun()
    else:
        st.success("提出済みです。他の人を待ちましょう。")

    # 場の表示
    st.divider()
    st.subheader("現在の場")
    if table:
        display_cols = st.columns(len(table))
        for idx, card in enumerate(table):
            with display_cols[idx]:
                st.button(f"？\n{card['name']}", key=f"field_{idx}", disabled=True, use_container_width=True)
                st.caption(f"👤 {card['player']}")

    if st.button("全員並べたのでOPEN！", type="primary"):
        update_game_data({"status": "OPEN"})
        st.rerun()

# --- 6. 画面表示 (OPENフェーズ) ---
elif data['status'] == "OPEN":
    st.title("🎊 結果発表")
    table = data['table_data']
    
    success = True
    prev_num = 0
    
    for i in range(len(table)):
        card = table[i]
        is_error = card['num'] < prev_num
        
        color = "green" if not is_error else "red"
        st.markdown(f"### {i+1}. {card['name']} : **{card['num']}** (by {card['player']})")
        
        if is_error:
            success = False
        prev_num = card['num']

    if success:
        st.balloons()
        st.success("大成功！価値観がピッタリです！")
    else:
        st.error("失敗... 価値観がズレていたようです😭")
        st.write("😢" * 10)

    if st.button("新しいゲームを始める"):
        update_game_data({"status": "SETUP", "table_data": [], "topic": ""})
        st.session_state.my_hand = []
        st.rerun()
