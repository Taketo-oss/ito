import streamlit as st
from supabase import create_client, Client
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. CSSによるモバイルUI調整 ---
st.set_page_config(page_title="ito Mobile", layout="centered")
st.markdown("""
    <style>
    .stButton button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .card-box { border: 2px solid #f0f2f6; padding: 10px; border-radius: 15px; text-align: center; margin-bottom: 10px; }
    .my-card { background-color: #e1f5fe; border-color: #01579b; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初期設定 & Supabase ---
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = st.session_state.supabase
ROOM_ID = 1
st_autorefresh(interval=4000, key="datarefresh") # 4秒更新

if "my_name" not in st.session_state:
    st.session_state.my_name = ""

# ログイン画面
if not st.session_state.my_name:
    st.title("🎨 ito Mobile")
    name = st.text_input("表示名を入力")
    if st.button("参加する") and name:
        st.session_state.my_name = name
        st.rerun()
    st.stop()

# データ操作
def get_data():
    res = supabase.table("ito_rooms").select("*").eq("id", ROOM_ID).execute()
    return res.data[0]
def set_data(updates):
    supabase.table("ito_rooms").update(updates).eq("id", ROOM_ID).execute()

data = get_data()

# --- 3. セットアップ ---
if data['status'] == "SETUP":
    st.title("⚙️ ルーム設定")
    with st.container():
        topic = st.text_input("お題", placeholder="例：怖いもの")
        h_count = st.number_input("手札枚数", 1, 5, 1)
        if st.button("ゲーム開始"):
            set_data({"topic": topic, "status": "PLAYING", "table_data": [], "hand_count": h_count})
            st.session_state.pop("my_hand", None) # 手札リセット
            st.rerun()

# --- 4. プレイ画面 ---
elif data['status'] == "PLAYING":
    st.title(f"🃏 {data['topic']}")
    table = data['table_data']
    hand_limit = data.get('hand_count', 1)

    # 手札生成（1回だけ実行）
    if "my_hand" not in st.session_state:
        st.session_state.my_hand = sorted([random.randint(1, 100) for _ in range(hand_limit)])
    
    # 自分の現在の場に出している枚数
    my_cards_on_table = [c for c in table if c['player'] == st.session_state.my_name]
    
    # --- 手札エリア ---
    st.subheader("📋 あなたの手札")
    if st.session_state.my_hand:
        cols = st.columns(len(st.session_state.my_hand))
        for i, num in enumerate(st.session_state.my_hand):
            if cols[i].button(f"{num}", key=f"hand_{i}"):
                st.session_state.selected_num = num
                st.session_state.selected_idx = i

        if "selected_num" in st.session_state:
            st.write(f"選択中: **{st.session_state.selected_num}**")
            c_name = st.text_input("名前をつけて場に出す", key="input_name")
            if st.button("場に出す") and c_name:
                if len(my_cards_on_table) < hand_limit:
                    table.append({"name": c_name, "num": st.session_state.selected_num, "player": st.session_state.my_name})
                    st.session_state.my_hand.pop(st.session_state.selected_idx)
                    del st.session_state.selected_num
                    set_data({"table_data": table})
                    st.rerun()
                else:
                    st.error(f"出せるのは{hand_limit}枚までです！")
    else:
        st.write("手札はありません（すべて提出済み）")

    # --- 場（テーブル）エリア ---
    st.divider()
    st.subheader("🖼️ 場の状況 (左:小 → 右:大)")
    
    for i, card in enumerate(table):
        is_mine = card['player'] == st.session_state.my_name
        with st.container():
            # 自分には数字が見える、他人には見えない
            label = f"【{card['num']}】 {card['name']}" if is_mine else f"【？】 {card['name']}"
            st.markdown(f"<div class='card-box {'my-card' if is_mine else ''}'><b>{label}</b><br><small>👤 {card['player']}</small></div>", unsafe_allow_html=True)
            
            # 自分のカードなら操作ボタンを表示
            if is_mine:
                c1, c2, c3 = st.columns(3)
                if c1.button("⬅️", key=f"L_{i}") and i > 0:
                    table[i], table[i-1] = table[i-1], table[i]
                    set_data({"table_data": table}); st.rerun()
                if c2.button("↩️", key=f"R_{i}"):
                    st.session_state.my_hand.append(card['num'])
                    table.pop(i)
                    set_data({"table_data": table}); st.rerun()
                if c3.button("➡️", key=f"RR_{i}") and i < len(table)-1:
                    table[i], table[i+1] = table[i+1], table[i]
                    set_data({"table_data": table}); st.rerun()

    if st.button("全員完了！OPEN！", type="primary"):
        set_data({"status": "OPEN"})
        st.rerun()

# --- 5. OPEN画面 ---
elif data['status'] == "OPEN":
    st.title("🎊 結果発表")
    table = data['table_data']
    success = True
    for i in range(len(table)):
        st.subheader(f"{i+1}. {table[i]['name']} : {table[i]['num']}")
        st.caption(f"by {table[i]['player']}")
        if i > 0 and table[i]['num'] < table[i-1]['num']: success = False
    
    if success: st.balloons(); st.success("大成功！")
    else: st.error("失敗...")
    
    if st.button("次へ"):
        set_data({"status": "SETUP", "table_data": []})
        st.rerun()
