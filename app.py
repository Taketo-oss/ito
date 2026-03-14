import streamlit as st
from supabase import create_client, Client
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. UI設定 (家計簿アプリ風ダークモード) ---
st.set_page_config(page_title="ito Mobile", layout="centered")

# カラー定義 (家計簿アプリの配色)
PRIMARY = "#4DA6FF"   # スカイブルー
BG_DARK = "#0D1B2A"   # 深い紺色
CARD_BG = "#1B263B"   # 少し明るい紺色
TEXT_COLOR = "#E0E1DD" # 青みのある白

st.markdown(f"""
    <style>
    /* 全体の背景と文字色 */
    .stApp {{ background-color: {BG_DARK}; color: {TEXT_COLOR}; }}
    html, body, [data-testid="stWidgetLabel"], .stMarkdown p, h1, h2, h3 {{
        color: {TEXT_COLOR} !important;
    }}

    /* ボタン：立体感のあるスカイブルー */
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
        color: {BG_DARK} !important;
        box-shadow: 0 4px 0 #2B86E0;
    }}

    /* ゲームカード：家計簿パネル風 */
    .game-card {{
        background-color: {CARD_BG};
        border: 2px solid #2B3A55;
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 8px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }}
    /* 自分のカード */
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

    /* 参加者タグ */
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
    hr {{ opacity: 0.2; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 接続・同期ロジック ---
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = st.session_state.supabase
ROOM_ID = 1

# 自動更新 (安定のため4秒)
st_autorefresh(interval=4000, key="ito_refresh_stable")

def get_data():
    try:
        res = supabase.table("ito_rooms").select("*").eq("id", ROOM_ID).execute()
        return res.data[0]
    except:
        return None

def set_data(updates):
    try:
        supabase.table("ito_rooms").update(updates).eq("id", ROOM_ID).execute()
    except:
        st.error("データの送信に失敗しました。")

data = get_data()
if not data:
    st.warning("Supabaseとの接続を確認中...")
    st.stop()

# セッション変数の安全な初期化
if "my_name" not in st.session_state: st.session_state.my_name = ""

# --- 3. 退出処理 ---
def logout():
    if st.session_state.my_name:
        p_list = list(data.get('player_list', []))
        if st.session_state.my_name in p_list:
            p_list.remove(st.session_state.my_name)
            set_data({"player_list": p_list})
        st.session_state.my_name = ""
        if "my_hand" in st.session_state: del st.session_state.my_hand
        st.rerun()

# サイドバーに退出ボタンを表示
with st.sidebar:
    if st.session_state.my_name:
        st.write(f"👤 **{st.session_state.my_name}**")
        if st.button("ゲームから退出"):
            logout()

# --- 4. 参加フェーズ ---
if not st.session_state.my_name:
    st.title("😸 ito Online")
    name = st.text_input("名前を入力してください")
    if st.button("参加する", type="primary") and name:
        p_list = list(data.get('player_list', []))
        if name not in p_list:
            p_list.append(name)
            set_data({"player_list": p_list})
        st.session_state.my_name = name
        st.rerun()
    st.stop()

# --- 5. SETUP 画面 ---
if data['status'] == "SETUP":
    st.subheader("👥 待機中のメンバー")
    players = data.get('player_list', [])
    tags_html = "".join([f"<span class='player-tag'>👤 {p}</span>" for p in players])
    st.markdown(tags_html, unsafe_allow_html=True)

    st.divider()
    st.subheader("🛠️ ルーム設定")
    topic = st.text_input("お題", value=data.get('topic', ''), placeholder="例：人気の食べ物")
    h_count = st.number_input("手札の枚数", 1, 5, value=int(data.get('hand_count', 1)))
    
    if st.button("ゲームを開始する", type="primary"):
        set_data({"topic": topic, "status": "PLAYING", "table_data": [], "hand_count": h_count})
        if "my_hand" in st.session_state: del st.session_state.my_hand
        st.rerun()

# --- 6. PLAYING 画面 ---
elif data['status'] == "PLAYING":
    st.markdown(f"<h2 style='text-align: center; color: {PRIMARY};'>🃏 {data['topic']}</h2>", unsafe_allow_html=True)
    table = data['table_data']
    official_count = int(data.get('hand_count', 1))

    # 手札の厳密同期
    my_on_table = [c for c in table if c['player'] == st.session_state.my_name]
    if "my_hand" not in st.session_state or (len(st.session_state.my_hand) + len(my_on_table) != official_count):
        st.session_state.my_hand = sorted([random.randint(1, 100) for _ in range(max(0, official_count - len(my_on_table)))])

    st.markdown(f"### 📋 あなたの手札 ({len(st.session_state.my_hand)}枚)")
    cols = st.columns(len(st.session_state.my_hand)) if st.session_state.my_hand else []
    for i, num in enumerate(st.session_state.my_hand):
        if cols[i].button(str(num), key=f"h_{num}_{i}"):
            st.session_state.sel_num, st.session_state.sel_idx = num, i

    if "sel_num" in st.session_state:
        st.markdown(f"選択中: **{st.session_state.sel_num}**")
        val_name = st.text_input("言葉で表現すると？", placeholder="例：オムライス")
        if st.button("確定して場に出す", type="primary") and val_name:
            table.append({"name": val_name, "num": st.session_state.sel_num, "player": st.session_state.my_name})
            st.session_state.my_hand.pop(st.session_state.sel_idx)
            del st.session_state.sel_num
            set_data({"table_data": table}); st.rerun()

    st.divider()
    st.caption("🖼️ 場の状況 (上が小さい数字)")
    for i, card in enumerate(table):
        mine = card['player'] == st.session_state.my_name
        label = f"【{card['num']}】 {card['name']}" if mine else f"【？】 {card['name']}"
        st.markdown(f"<div class='game-card {'my-card-panel' if mine else ''}'><div class='card-text'>{label}</div><div class='player-sub'>👤 {card['player']}</div></div>", unsafe_allow_html=True)
        
        if mine:
            c1, c2, c3 = st.columns([1,2,1])
            if i > 0 and c1.button("⬆️", key=f"u_{i}"):
                table[i], table[i-1] = table[i-1], table[i]; set_data({"table_data": table}); st.rerun()
            if c2.button("↩️ 回収", key=f"r_{i}"):
                st.session_state.my_hand.append(card['num']); table.pop(i); set_data({"table_data": table}); st.rerun()
            if i < len(table)-1 and c3.button("⬇️", key=f"d_{i}"):
                table[i], table[i+1] = table[i+1], table[i]; set_data({"table_data": table}); st.rerun()

    if st.button("全員完了！答え合わせへ", type="primary"):
        set_data({"status": "OPEN"}); st.rerun()

# --- 7. OPEN 画面 (シンプル全公開版) ---
elif data['status'] == "OPEN":
    st.markdown("<h1 style='text-align: center;'>🎊 答え合わせ</h1>", unsafe_allow_html=True)
    table = data['table_data']
    
    # 成功判定
    prev_num, success = 0, True
    for card in table:
        if card['num'] < prev_num: success = False; break
        prev_num = card['num']
    
    if success: st.balloons(); st.success("🎉 大成功！価値観がピッタリです！")
    else: st.error("😢 失敗... 価値観がズレていたようです。")

    # 全カードを一気に表示
    for card in table:
        st.markdown(f"""
            <div class='game-card'>
                <div class='card-text'>【{card['num']}】 {card['name']}</div>
                <div class='player-sub'>👤 {card['player']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    if st.button("リセットして戻る", type="primary"):
        set_data({"status": "SETUP", "table_data": [], "topic": "", "hand_count": 1})
        if "my_hand" in st.session_state: del st.session_state.my_hand
        st.rerun()
