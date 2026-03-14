import streamlit as st
from supabase import create_client, Client
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. モダンWebゲーム風 CSS ---
st.set_page_config(page_title="ito Mobile", layout="centered")
st.markdown("""
    <style>
    /* 全体の背景色を少しグレーにしてカードを引き立てる */
    .stApp { background-color: #f7f9fc; }
    
    /* ボタンの共通スタイル：立体感と丸み */
    .stButton button {
        width: 100%;
        border-radius: 14px;
        height: 3.8em;
        font-weight: 800;
        font-size: 1.1em;
        border: none;
        box-shadow: 0 4px 0 #cccccc; /* 下に立体的な影 */
        transition: all 0.1s;
        color: #1a1a1a !important;
        background-color: #ffffff;
    }
    .stButton button:active {
        transform: translateY(3px); /* 押した時に沈む演出 */
        box-shadow: 0 1px 0 #cccccc;
    }
    /* 決定ボタン（Primary）の色 */
    div[data-testid="stBaseButton-primary"] button {
        background-color: #ffd600 !important; /* 黄色で目立たせる */
        box-shadow: 0 4px 0 #b29600;
    }

    /* カード風パネルのデザイン */
    .card-container {
        background-color: #ffffff;
        border: 2px solid #e0e0e0;
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        text-align: center;
    }
    .my-card-panel {
        background-color: #e3f2fd !important; /* 爽やかな水色 */
        border: 2px solid #2196f3 !important;
    }
    .card-title {
        color: #1a1a1a;
        font-size: 1.3em;
        font-weight: 900;
        margin-bottom: 5px;
    }
    .player-name {
        font-size: 0.9em;
        color: #666666;
        font-weight: 600;
    }
    /* 参加者タグ */
    .player-tag {
        background-color: #ffffff;
        padding: 8px 16px;
        border-radius: 50px;
        display: inline-block;
        margin: 4px;
        border: 2px solid #e0e0e0;
        font-weight: bold;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 接続設定 (前回と同様) ---
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = st.session_state.supabase
ROOM_ID = 1
st_autorefresh(interval=3500, key="datarefresh")

def get_data():
    res = supabase.table("ito_rooms").select("*").eq("id", ROOM_ID).execute()
    return res.data[0]
def set_data(updates):
    supabase.table("ito_rooms").update(updates).eq("id", ROOM_ID).execute()

data = get_data()

# --- 3. 参加フェーズ ---
if "my_name" not in st.session_state:
    st.session_state.my_name = ""

if not st.session_state.my_name:
    st.title("🎨 ito Online")
    name = st.text_input("名前を入力", placeholder="ニックネーム")
    if st.button("ゲームに参加する", type="primary") and name:
        p_list = data.get('player_list', [])
        if name not in p_list:
            p_list.append(name)
            set_data({"player_list": p_list})
        st.session_state.my_name = name
        st.rerun()
    st.stop()

# --- 4. 待機画面 (SETUP) ---
if data['status'] == "SETUP":
    st.title("🎮 ルーム待機中")
    
    st.markdown("### 👥 参加しているメンバー")
    players = data.get('player_list', [])
    tags_html = "".join([f"<span class='player-tag'>{p}</span>" for p in players])
    st.markdown(tags_html, unsafe_allow_html=True)

    st.divider()
    with st.container():
        st.markdown("### 🛠️ ホスト設定")
        topic = st.text_input("今日のお題は？", value=data.get('topic', ''))
        h_count = st.number_input("配るカードの枚数", 1, 5, value=int(data.get('hand_count', 1)))
        if st.button("この設定で開始！", type="primary"):
            set_data({"topic": topic, "status": "PLAYING", "table_data": [], "hand_count": h_count})
            st.session_state.pop("my_hand", None)
            st.rerun()

# --- 5. ゲーム画面 (PLAYING) ---
elif data['status'] == "PLAYING":
    st.markdown(f"<h1 style='text-align: center;'>🃏 {data['topic']}</h1>", unsafe_allow_html=True)
    table = data['table_data']
    h_count = data.get('hand_count', 1)

    if "my_hand" not in st.session_state:
        st.session_state.my_hand = sorted([random.randint(1, 100) for _ in range(h_count)])
    
    # 手札エリア
    st.markdown("### 📋 あなたの手札")
    cols = st.columns(len(st.session_state.my_hand)) if st.session_state.my_hand else [st.empty()]
    for i, num in enumerate(st.session_state.my_hand):
        if cols[i].button(f"{num}", key=f"h_{i}"):
            st.session_state.selected_num = num
            st.session_state.selected_idx = i

    if "selected_num" in st.session_state:
        st.markdown(f"**選択中: {st.session_state.selected_num}**")
        c_name = st.text_input("この数字を言葉にすると？")
        if st.button("場に出す", type="primary") and c_name:
            table.append({"name": c_name, "num": st.session_state.selected_num, "player": st.session_state.my_name})
            st.session_state.my_hand.pop(st.session_state.selected_idx)
            del st.session_state.selected_num
            set_data({"table_data": table}); st.rerun()

    # 場のエリア
    st.divider()
    st.markdown("### 🖼️ 場の状況 (上が小さい)")
    for i, card in enumerate(table):
        is_mine = card['player'] == st.session_state.my_name
        label = f"【{card['num']}】 {card['name']}" if is_mine else f"【？】 {card['name']}"
        
        # カスタムHTMLカード
        st.markdown(f"""
            <div class='card-container {'my-card-panel' if is_mine else ''}'>
                <div class='card-title'>{label}</div>
                <div class='player-name'>👤 {card['player']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if is_mine:
            c1, c2, c3 = st.columns([1,2,1])
            c1.button("⬆️", key=f"u_{i}") if i > 0 else c1.empty()
            if c2.button("↩️ 回収", key=f"r_{i}"):
                st.session_state.my_hand.append(card['num'])
                table.pop(i); set_data({"table_data": table}); st.rerun()
            c3.button("⬇️", key=f"d_{i}") if i < len(table)-1 else c3.empty()

    if st.button("全員並べたので結果を見る！", type="primary"):
        set_data({"status": "OPEN"}); st.rerun()

# --- 6. 結果発表 (OPEN) ---
elif data['status'] == "OPEN":
    st.title("🎊 答え合わせ")
    table = data['table_data']
    for i, card in enumerate(table):
        st.markdown(f"<div class='card-container'><h3>{card['name']} : {card['num']}</h3><small>{card['player']}</small></div>", unsafe_allow_html=True)
    
    if st.button("もう一度遊ぶ", type="primary"):
        set_data({"status": "SETUP", "table_data": [], "topic": "", "hand_count": 1})
        st.session_state.my_hand = []
        st.rerun()
