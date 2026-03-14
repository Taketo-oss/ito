import streamlit as st
from supabase import create_client, Client
import random
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. UIカスタムCSS (家計簿アプリ風) ---
st.set_page_config(page_title="ito Mobile", layout="centered")

PRIMARY = "#4DA6FF"
BG_DARK = "#0D1B2A"
CARD_BG = "#1B263B"
TEXT_COLOR = "#E0E1DD"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {BG_DARK}; color: {TEXT_COLOR}; }}
    .stButton button {{
        width: 100%; border-radius: 12px; height: 3.8em; font-weight: 800;
        border: 2px solid {PRIMARY} !important; background-color: {CARD_BG};
        color: {PRIMARY} !important; box-shadow: 0 4px 0 {PRIMARY};
    }}
    .game-card {{
        background-color: {CARD_BG}; border: 2px solid #2B3A55;
        border-radius: 18px; padding: 16px; margin-bottom: 8px; text-align: center;
    }}
    .my-card-panel {{ border: 2px solid {PRIMARY} !important; background-color: rgba(77, 166, 255, 0.1); }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 接続設定 ---
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = st.session_state.supabase
ROOM_ID = 1

# 自動更新（RuntimeError対策のため、間隔を少し広めの4秒に設定）
st_autorefresh(interval=4000, key="ito_refresh")

def get_data():
    try:
        res = supabase.table("ito_rooms").select("*").eq("id", ROOM_ID).execute()
        return res.data[0]
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return None

def set_data(updates):
    try:
        supabase.table("ito_rooms").update(updates).eq("id", ROOM_ID).execute()
    except Exception as e:
        st.error(f"送信エラー: {e}")

data = get_data()
if not data: st.stop()

# --- 3. セッション管理 (RuntimeError対策) ---
# セッションの初期化を安全に行う
if "my_name" not in st.session_state: st.session_state.my_name = ""
if "reveal_index" not in st.session_state: st.session_state.reveal_index = -1

# ログイン
if not st.session_state.my_name:
    st.title("😸 ito Online")
    name = st.text_input("ニックネーム")
    if st.button("参加する", type="primary") and name:
        p_list = list(data.get('player_list', []))
        if name not in p_list:
            p_list.append(name)
            set_data({"player_list": p_list})
        st.session_state.my_name = name
        st.rerun()
    st.stop()

# --- 4. メインロジック ---
if data['status'] == "SETUP":
    st.session_state.reveal_index = -1
    st.subheader("👥 待機中")
    st.write(", ".join(data.get('player_list', [])))
    st.divider()
    topic = st.text_input("お題", value=data.get('topic', ''))
    h_count = st.number_input("手札枚数", 1, 5, value=int(data.get('hand_count', 1)))
    if st.button("開始！", type="primary"):
        set_data({"topic": topic, "status": "PLAYING", "table_data": [], "hand_count": h_count})
        if "my_hand" in st.session_state: del st.session_state.my_hand
        st.rerun()

elif data['status'] == "PLAYING":
    st.title(f"🃏 {data['topic']}")
    table = data['table_data']
    official_count = int(data.get('hand_count', 1))
    
    # 手札同期
    my_cards = [c for c in table if c['player'] == st.session_state.my_name]
    if "my_hand" not in st.session_state or (len(st.session_state.my_hand) + len(my_cards) != official_count):
        st.session_state.my_hand = sorted([random.randint(1, 100) for _ in range(official_count - len(my_cards))])

    # 手札表示
    cols = st.columns(len(st.session_state.my_hand)) if st.session_state.my_hand else []
    for i, num in enumerate(st.session_state.my_hand):
        if cols[i].button(str(num), key=f"h_{num}_{i}"):
            st.session_state.sel_num = num
            st.session_state.sel_idx = i

    if "sel_num" in st.session_state:
        name = st.text_input(f"{st.session_state.sel_num} を言葉にすると？")
        if st.button("場に出す", type="primary") and name:
            table.append({"name": name, "num": st.session_state.sel_num, "player": st.session_state.my_name})
            st.session_state.my_hand.pop(st.session_state.sel_idx)
            del st.session_state.sel_num
            set_data({"table_data": table})
            st.rerun()

    # 場の表示 (縦)
    st.divider()
    for i, card in enumerate(table):
        mine = card['player'] == st.session_state.my_name
        txt = f"【{card['num']}】 {card['name']}" if mine else f"【？】 {card['name']}"
        st.markdown(f"<div class='game-card {'my-card-panel' if mine else ''}'>{txt}<br><small>{card['player']}</small></div>", unsafe_allow_html=True)
        if mine:
            c1, c2, c3 = st.columns([1,2,1])
            if i > 0 and c1.button("⬆️", key=f"u_{i}"):
                table[i], table[i-1] = table[i-1], table[i]; set_data({"table_data": table}); st.rerun()
            if c2.button("↩️", key=f"r_{i}"):
                st.session_state.my_hand.append(card['num']); table.pop(i); set_data({"table_data": table}); st.rerun()
            if i < len(table)-1 and c3.button("⬇️", key=f"d_{i}"):
                table[i], table[i+1] = table[i+1], table[i]; set_data({"table_data": table}); st.rerun()

    if st.button("全員完了！OPEN"):
        set_data({"status": "OPEN"}); st.rerun()

elif data['status'] == "OPEN":
    st.title("🎊 オープン")
    table = data['table_data']
    for i, card in enumerate(table):
        if i <= st.session_state.reveal_index:
            st.markdown(f"<div class='game-card'>【{card['num']}】 {card['name']}<br><small>{card['player']}</small></div>", unsafe_allow_html=True)
        elif i == st.session_state.reveal_index + 1:
            if st.button(f"めくる ({card['name']})", type="primary"):
                st.session_state.reveal_index += 1; st.rerun()
    if st.session_state.reveal_index == len(table)-1:
        if st.button("リセット"):
            set_data({"status": "SETUP", "table_data": [], "topic": "", "hand_count": 1})
            st.session_state.reveal_index = -1; st.rerun()
