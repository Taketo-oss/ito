import streamlit as st
from supabase import create_client, Client
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. UI設定 (家計簿アプリ風) ---
st.set_page_config(page_title="ito Mobile", layout="centered")

PRIMARY, BG_DARK, CARD_BG, TEXT_COLOR = "#4DA6FF", "#0D1B2A", "#1B263B", "#E0E1DD"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {BG_DARK}; color: {TEXT_COLOR}; }}
    html, body, [data-testid="stWidgetLabel"], .stMarkdown p, h1, h2, h3 {{
        color: {TEXT_COLOR} !important;
    }}
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
    .card-text {{ font-size: 1.2em; font-weight: 900; color: #FFFFFF; }}
    .player-tag {{
        display: inline-block; padding: 6px 14px; border-radius: 8px;
        background-color: rgba(77, 166, 255, 0.1); color: {PRIMARY};
        border: 1px solid rgba(77, 166, 255, 0.3); margin: 4px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 接続設定 ---
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = st.session_state.supabase
ROOM_ID = 1

# 自動更新 (安定のため4秒)
st_autorefresh(interval=4000, key="ito_refresh")

def get_data():
    try:
        res = supabase.table("ito_rooms").select("*").eq("id", ROOM_ID).execute()
        return res.data[0]
    except: return None

def set_data(updates):
    try: supabase.table("ito_rooms").update(updates).eq("id", ROOM_ID).execute()
    except: st.error("送信エラー")

data = get_data()
if not data: st.stop()

if "my_name" not in st.session_state: st.session_state.my_name = ""

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

# --- 3. メインロジック ---
if data['status'] == "SETUP":
    st.subheader("👥 待機中のメンバー")
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
        st.session_state.my_hand = sorted([random.randint(1, 100) for _ in range(max(0, official_count - len(my_cards)))])

    st.markdown("### 📋 あなたの手札")
    cols = st.columns(len(st.session_state.my_hand)) if st.session_state.my_hand else []
    for i, num in enumerate(st.session_state.my_hand):
        if cols[i].button(str(num), key=f"h_{i}"):
            st.session_state.sel_num, st.session_state.sel_idx = num, i

    if "sel_num" in st.session_state:
        val_name = st.text_input(f"{st.session_state.sel_num} を言葉にすると？")
        if st.button("確定して出す", type="primary") and val_name:
            table.append({"name": val_name, "num": st.session_state.sel_num, "player": st.session_state.my_name})
            st.session_state.my_hand.pop(st.session_state.sel_idx)
            del st.session_state.sel_num
            set_data({"table_data": table}); st.rerun()

    st.divider()
    for i, card in enumerate(table):
        mine = card['player'] == st.session_state.my_name
        label = f"【{card['num']}】 {card['name']}" if mine else f"【？】 {card['name']}"
        st.markdown(f"<div class='game-card {'my-card-panel' if mine else ''}'><div class='card-text'>{label}</div><small>👤 {card['player']}</small></div>", unsafe_allow_html=True)
        if mine:
            c1, c2, c3 = st.columns([1,2,1])
            if i > 0 and c1.button("⬆️", key=f"u_{i}"):
                table[i], table[i-1] = table[i-1], table[i]; set_data({"table_data": table}); st.rerun()
            if c2.button("↩️ 回収", key=f"r_{i}"):
                st.session_state.my_hand.append(card['num']); table.pop(i); set_data({"table_data": table}); st.rerun()
            if i < len(table)-1 and c3.button("⬇️", key=f"d_{i}"):
                table[i], table[i+1] = table[i+1], table[i]; set_data({"table_data": table}); st.rerun()

    if st.button("全員完了！OPEN"):
        set_data({"status": "OPEN"}); st.rerun()

elif data['status'] == "OPEN":
    st.title("🎊 結果発表")
    table = data['table_data']
    
    # 成功判定
    prev_num, success = 0, True
    for card in table:
        if card['num'] < prev_num: success = False; break
        prev_num = card['num']
    
    if success: st.balloons(); st.success("🎉 大成功！")
    else: st.error("😢 失敗...")

    # 全カード表示
    for card in table:
        st.markdown(f"<div class='game-card'><div class='card-text'>【{card['num']}】 {card['name']}</div><small>👤 {card['player']}</small></div>", unsafe_allow_html=True)
    
    st.divider()
    if st.button("リセットして戻る", type="primary"):
        set_data({"status": "SETUP", "table_data": [], "topic": "", "hand_count": 1})
        if "my_hand" in st.session_state: del st.session_state.my_hand
        st.rerun()
