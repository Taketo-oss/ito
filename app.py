import streamlit as st
from supabase import create_client, Client
import random
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. UIカスタムCSS (家計簿アプリ風配色 + 高コントラスト) ---
st.set_page_config(page_title="ito Mobile", layout="centered")

PRIMARY = "#4DA6FF"   # スカイブルー
BG_DARK = "#0D1B2A"   # 深い紺色
CARD_BG = "#1B263B"   # 少し明るい紺色
TEXT_COLOR = "#E0E1DD" # 青みのある白

st.markdown(f"""
    <style>
    .stApp {{ background-color: {BG_DARK}; color: {TEXT_COLOR}; }}
    html, body, [data-testid="stWidgetLabel"], .stMarkdown p, h1, h2, h3 {{
        color: {TEXT_COLOR} !important;
    }}
    /* 立体的なボタン */
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
    div[data-testid="stBaseButton-primary"] button {{
        background-color: {PRIMARY} !important;
        color: {BG_DARK} !important;
        box-shadow: 0 4px 0 #2B86E0;
    }}
    /* カードデザイン */
    .game-card {{
        background-color: {CARD_BG};
        border: 2px solid #2B3A55;
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 8px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }}
    .my-card-panel {{
        background-color: rgba(77, 166, 255, 0.15) !important;
        border: 2px solid {PRIMARY} !important;
    }}
    .covered-card {{
        border: 2px dashed {PRIMARY} !important;
        opacity: 0.8;
    }}
    .card-text {{ font-size: 1.25em; font-weight: 900; color: #FFFFFF; }}
    .player-sub {{ font-size: 0.8rem; color: #8E9AAF; font-weight: 700; }}
    .player-tag {{
        display: inline-block; padding: 6px 14px; border-radius: 8px;
        font-size: 0.85rem; font-weight: bold; background-color: rgba(77, 166, 255, 0.1);
        color: {PRIMARY}; border: 1px solid rgba(77, 166, 255, 0.3); margin: 4px;
    }}
    hr {{ opacity: 0.2; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 接続・同期ロジック ---
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = st.session_state.supabase
ROOM_ID = 1

# 状態に応じて自動更新を管理
auto_on = st.session_state.get('auto_refresh', True)
st_autorefresh(interval=3500 if auto_on else 0, key="datarefresh")

def get_data():
    res = supabase.table("ito_rooms").select("*").eq("id", ROOM_ID).execute()
    return res.data[0]
def set_data(updates):
    supabase.table("ito_rooms").update(updates).eq("id", ROOM_ID).execute()

data = get_data()

if "my_name" not in st.session_state:
    st.session_state.my_name = ""

# --- 3. 参加フェーズ ---
if not st.session_state.my_name:
    st.title("😸 ito Online")
    name = st.text_input("ニックネームを入力")
    if st.button("参加する", type="primary") and name:
        p_list = data.get('player_list', [])
        if name not in p_list:
            p_list.append(name)
            set_data({"player_list": p_list})
        st.session_state.my_name = name
        st.rerun()
    st.stop()

# --- 4. 待機画面 (SETUP) ---
if data['status'] == "SETUP":
    st.session_state.auto_refresh = True
    st.session_state.reveal_index = -1
    
    st.subheader("👥 現在の参加者")
    players = data.get('player_list', [])
    tags_html = "".join([f"<span class='player-tag'>👤 {p}</span>" for p in players])
    st.markdown(tags_html, unsafe_allow_html=True)

    st.divider()
    st.subheader("🛠️ ルーム設定")
    topic = st.text_input("お題", value=data.get('topic', ''))
    h_count = st.number_input("手札の枚数", 1, 5, value=int(data.get('hand_count', 1)))
    
    if st.button("ゲームを開始する", type="primary"):
        # ホストが「開始」を押した瞬間にDBの枚数を確定させる
        set_data({"topic": topic, "status": "PLAYING", "table_data": [], "hand_count": h_count})
        st.session_state.pop("my_hand", None) # 自分の分は即リセット
        st.rerun()

# --- 5. ゲーム画面 (PLAYING) ---
elif data['status'] == "PLAYING":
    st.markdown(f"<h2 style='text-align: center; color: {PRIMARY} !important;'>🃏 {data['topic']}</h2>", unsafe_allow_html=True)
    table = data['table_data']
    official_hand_count = int(data.get('hand_count', 1))

    # 【重要】手札生成・同期ロジック
    # 手札がない、またはDBの枚数とズレている場合は生成し直す
    if "my_hand" not in st.session_state or len(st.session_state.my_hand) + len([c for c in table if c['player'] == st.session_state.my_name]) != official_hand_count:
        # すでに場に出している分も考慮して補填する
        my_on_table = [c for c in table if c['player'] == st.session_state.my_name]
        needed = official_hand_count - len(my_on_table)
        st.session_state.my_hand = sorted([random.randint(1, 100) for _ in range(max(0, needed))])

    # 手札エリア
    st.markdown(f"### 📋 あなたの手札 ({len(st.session_state.my_hand)}枚)")
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
        st.markdown(f"<div class='game-card {'my-card-panel' if is_mine else ''}'><div class='card-text'>{label}</div><div class='player-sub'>👤 {card['player']}</div></div>", unsafe_allow_html=True)
        
        if is_mine:
            c1, c2, c3 = st.columns([1,2,1])
            if i > 0:
                if c1.button("⬆️", key=f"u_{i}"):
                    table[i], table[i-1] = table[i-1], table[i]
                    set_data({"table_data": table}); st.rerun()
            if c2.button("↩️ 回収", key=f"r_{i}"):
                st.session_state.my_hand.append(card['num'])
                table.pop(i); set_data({"table_data": table}); st.rerun()
            if i < len(table)-1:
                if c3.button("⬇️", key=f"d_{i}"):
                    table[i], table[i+1] = table[i+1], table[i]
                    set_data({"table_data": table}); st.rerun()

    if st.button("全員完了！OPEN！", type="primary"):
        set_data({"status": "OPEN"})
        st.session_state.auto_refresh = False
        st.rerun()

# --- 6. オープン画面 (ドキドキ順次オープン) ---
elif data['status'] == "OPEN":
    st.session_state.auto_refresh = False
    st.markdown("<h1 style='text-align: center;'>🎊 答え合わせ</h1>", unsafe_allow_html=True)
    table = data['table_data']
    
    if "reveal_index" not in st.session_state: st.session_state.reveal_index = -1

    for i in range(len(table)):
        card = table[i]
        if i <= st.session_state.reveal_index:
            st.markdown(f"<div class='game-card'><div class='card-text'>【{card['num']}】 {card['name']}</div><div class='player-sub'>👤 {card['player']}</div></div>", unsafe_allow_html=True)
        else:
            if i == st.session_state.reveal_index + 1:
                c1, c2 = st.columns([1, 4])
                with c1:
                    if st.button("めくる", key=f"rev_{i}", type="primary"):
                        st.session_state.reveal_index += 1; st.rerun()
                with c2: st.markdown(f"<div class='game-card covered-card'><div class='card-text'>ドキドキ...</div><div class='player-sub'>👤 {card['player']} ( {card['name']} )</div></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='game-card covered-card'><div class='card-text'>？？？</div><div class='player-sub'>👤 {card['player']}</div></div>", unsafe_allow_html=True)

    if st.session_state.reveal_index == len(table) - 1:
        st.divider()
        prev_num, success = 0, True
        for card in table:
            if card['num'] < prev_num: success = False; break
            prev_num = card['num']
        if success: st.balloons(); st.success("🎉 大成功！")
        else: st.error("😢 失敗...")
        if st.button("もう一度遊ぶ", type="primary"):
            set_data({"status": "SETUP", "table_data": [], "topic": "", "hand_count": 1})
            st.session_state.pop("my_hand", None); st.session_state.reveal_index = -1; st.rerun()
