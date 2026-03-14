import streamlit as st
from supabase import create_client, Client
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 家計簿アプリ風 UIカスタムCSS ---
st.set_page_config(page_title="ito Mobile", layout="centered")

# 家計簿アプリのカラーパレットを定義
PRIMARY = "#4DA6FF"   # スカイブルー
BG_DARK = "#0D1B2A"   # 深い紺色
CARD_BG = "#1B263B"   # 少し明るい紺色
TEXT_COLOR = "#E0E1DD" # 青みのある白

st.markdown(f"""
    <style>
    /* 全体の背景と文字色 */
    .stApp {{ background-color: {BG_DARK}; color: {TEXT_COLOR}; }}
    
    /* 標準テキストの色の強制 */
    html, body, [data-testid="stWidgetLabel"], .stMarkdown p, h1, h2, h3 {{
        color: {TEXT_COLOR} !important;
    }}

    /* ボタン：家計簿アプリ風のスカイブルー基調 */
    .stButton button {{
        width: 100%;
        border-radius: 12px;
        height: 3.8em;
        font-weight: 800;
        border: 2px solid {PRIMARY} !important;
        background-color: {CARD_BG};
        color: {PRIMARY} !important;
        box-shadow: 0 4px 0 {PRIMARY};
        transition: all 0.1s;
    }}
    .stButton button:active {{
        transform: translateY(2px);
        box-shadow: 0 2px 0 {PRIMARY};
    }}
    
    /* 決定ボタン（Primary） */
    div[data-testid="stBaseButton-primary"] button {{
        background-color: {PRIMARY} !important;
        color: {BG_DARK} !important; /* 背景が青なので文字は紺で抜く */
        box-shadow: 0 4px 0 #2B86E0;
    }}

    /* ゲームカード：家計簿のログのようなパネル */
    .game-card {{
        background-color: {CARD_BG};
        border: 2px solid #2B3A55;
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 8px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }}
    /* 自分のカード：家計簿のタグのような強調色 */
    .my-card-panel {{
        background-color: rgba(77, 166, 255, 0.15) !important;
        border: 2px solid {PRIMARY} !important;
    }}
    .card-text {{
        font-size: 1.25em;
        font-weight: 900;
        color: #FFFFFF;
        margin-bottom: 4px;
    }}
    .player-sub {{
        font-size: 0.8rem;
        color: #8E9AAF;
        font-weight: 700;
    }}

    /* 参加者タグ：家計簿のcat-tag風 */
    .player-tag {{
        display: inline-block;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: bold;
        background-color: rgba(77, 166, 255, 0.1);
        color: {PRIMARY};
        border: 1px solid rgba(77, 166, 255, 0.3);
        margin: 4px;
    }}
    
    /* 水平線の透過度調整 */
    hr {{ opacity: 0.2; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 接続設定 ---
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
    st.title("🐱 ito Online")
    name = st.text_input("ニックネームを入力")
    if st.button("ゲームに参加", type="primary") and name:
        p_list = data.get('player_list', [])
        if name not in p_list:
            p_list.append(name)
            set_data({"player_list": p_list})
        st.session_state.my_name = name
        st.rerun()
    st.stop()

# --- 4. 待機画面 (SETUP) ---
if data['status'] == "SETUP":
    st.subheader("👥 待機中のメンバー")
    players = data.get('player_list', [])
    tags_html = "".join([f"<span class='player-tag'>👤 {p}</span>" for p in players])
    st.markdown(tags_html, unsafe_allow_html=True)

    st.divider()
    st.subheader("🛠️ ルーム設定")
    topic = st.text_input("お題", value=data.get('topic', ''))
    h_count = st.number_input("手札の枚数", 1, 5, value=int(data.get('hand_count', 1)))
    if st.button("ゲームを開始する", type="primary"):
        set_data({"topic": topic, "status": "PLAYING", "table_data": [], "hand_count": h_count})
        st.session_state.pop("my_hand", None)
        st.rerun()

# --- 5. ゲーム画面 (PLAYING) ---
elif data['status'] == "PLAYING":
    st.markdown(f"<h2 style='text-align: center; color: {PRIMARY} !important;'>🃏 {data['topic']}</h2>", unsafe_allow_html=True)
    table = data['table_data']
    h_count = data.get('hand_count', 1)

    if "my_hand" not in st.session_state:
        st.session_state.my_hand = sorted([random.randint(1, 100) for _ in range(h_count)])
    
    # あなたの手札
    st.markdown("### 📋 あなたの手札")
    cols = st.columns(len(st.session_state.my_hand)) if st.session_state.my_hand else [st.empty()]
    for i, num in enumerate(st.session_state.my_hand):
        if cols[i].button(f"{num}", key=f"h_{i}"):
            st.session_state.selected_num = num
            st.session_state.selected_idx = i

    if "selected_num" in st.session_state:
        st.markdown(f"**選択中: {st.session_state.selected_num}**")
        c_name = st.text_input("言葉で表現すると？", placeholder="例：ラーメン")
        if st.button("場に出す", type="primary") and c_name:
            table.append({"name": c_name, "num": st.session_state.selected_num, "player": st.session_state.my_name})
            st.session_state.my_hand.pop(st.session_state.selected_idx)
            del st.session_state.selected_num
            set_data({"table_data": table}); st.rerun()

    # 場のエリア
    st.divider()
    st.caption("🖼️ 場の状況 (上が小さい)")
    for i, card in enumerate(table):
        is_mine = card['player'] == st.session_state.my_name
        label = f"【{card['num']}】 {card['name']}" if is_mine else f"【？】 {card['name']}"
        
        st.markdown(f"""
            <div class='game-card {'my-card-panel' if is_mine else ''}'>
                <div class='card-text'>{label}</div>
                <div class='player-sub'>👤 {card['player']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if is_mine:
            c1, c2, c3 = st.columns([1,2,1])
            c1.button("⬆️", key=f"u_{i}") if i > 0 else c1.empty()
            if c2.button("↩️ 回収", key=f"r_{i}"):
                st.session_state.my_hand.append(card['num'])
                table.pop(i); set_data({"table_data": table}); st.rerun()
            c3.button("⬇️", key=f"d_{i}") if i < len(table)-1 else c3.empty()

    if st.button("全員並べた！OPEN！", type="primary"):
        set_data({"status": "OPEN"}); st.rerun()

# --- 6. 結果発表 (OPEN) ---
elif data['status'] == "OPEN":
    st.title("🎊 答え合わせ")
    table = data['table_data']
    for i, card in enumerate(table):
        st.markdown(f"<div class='game-card'><h3>{card['name']} : {card['num']}</h3><small>{card['player']}</small></div>", unsafe_allow_html=True)
    
    if st.button("もう一度遊ぶ", type="primary"):
        set_data({"status": "SETUP", "table_data": [], "topic": "", "hand_count": 1})
        st.session_state.my_hand = []
        st.rerun()
