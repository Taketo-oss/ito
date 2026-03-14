import streamlit as st
from supabase import create_client, Client
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. CSSによるモバイルUI・色調整 ---
st.set_page_config(page_title="ito Mobile", layout="centered")
st.markdown("""
    <style>
    .stButton button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; color: #000000 !important; }
    .card-box { border: 3px solid #333333; padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 5px; color: #000000 !important; font-size: 1.1em; background-color: #ffffff; }
    .my-card { background-color: #bbdefb !important; border-color: #0d47a1 !important; }
    .stCaption { color: #333333 !important; font-weight: bold; text-align: center; margin-bottom: 15px; }
    .player-tag { background-color: #f0f2f6; padding: 5px 10px; border-radius: 15px; display: inline-block; margin: 2px; border: 1px solid #ccc; color: #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初期設定 & Supabase ---
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = st.session_state.supabase
ROOM_ID = 1
st_autorefresh(interval=3000, key="datarefresh") # 3秒に短縮してリアルタイム性アップ

def get_data():
    res = supabase.table("ito_rooms").select("*").eq("id", ROOM_ID).execute()
    return res.data[0]
def set_data(updates):
    supabase.table("ito_rooms").update(updates).eq("id", ROOM_ID).execute()

data = get_data()

# --- 3. ログイン・参加処理 ---
if "my_name" not in st.session_state:
    st.session_state.my_name = ""

if not st.session_state.my_name:
    st.title("🎨 ito Mobile")
    name = st.text_input("表示名を入力してください")
    if st.button("参加する") and name:
        # DBの参加者リストに自分を追加
        current_players = data.get('player_list', [])
        if name not in current_players:
            current_players.append(name)
            set_data({"player_list": current_players})
        st.session_state.my_name = name
        st.rerun()
    st.stop()

# --- 4. 画面表示 (SETUP) ---
if data['status'] == "SETUP":
    st.title("⚙️ ルーム待機中")
    
    # 参加者の表示
    st.subheader("👥 現在の参加者")
    players = data.get('player_list', [])
    if players:
        html_players = "".join([f"<span class='player-tag'>{p}</span>" for p in players])
        st.markdown(html_players, unsafe_allow_html=True)
    else:
        st.write("待機中...")

    st.divider()
    st.subheader("ホスト設定")
    topic = st.text_input("お題", value=data.get('topic', ''), placeholder="例：怖いもの")
    h_count = st.number_input("手札枚数", 1, 5, value=int(data.get('hand_count', 1)))
    
    if st.button("この設定でゲーム開始！", type="primary"):
        set_data({
            "topic": topic, 
            "status": "PLAYING", 
            "table_data": [], 
            "hand_count": h_count
        })
        st.session_state.pop("my_hand", None) # 自分の手札をリセット
        st.rerun()

# --- 5. 画面表示 (PLAYING) ---
elif data['status'] == "PLAYING":
    st.title(f"🃏 {data['topic']}")
    table = data['table_data']
    # 重要：各自が選んだ数ではなく、DBに保存された「公式の枚数」を使う
    sync_hand_count = data.get('hand_count', 1)

    # 手札の生成（DBの枚数に従う）
    if "my_hand" not in st.session_state:
        # 全員が同じDBのhand_countを参照して手札を作成
        st.session_state.my_hand = sorted([random.randint(1, 100) for _ in range(sync_hand_count)])
    
    my_cards_on_table = [c for c in table if c['player'] == st.session_state.my_name]
    
    # 手札エリア
    st.subheader(f"📋 あなたの手札 ({len(st.session_state.my_hand)}枚)")
    if st.session_state.my_hand:
        cols = st.columns(len(st.session_state.my_hand))
        for i, num in enumerate(st.session_state.my_hand):
            if cols[i].button(f"{num}", key=f"hand_{i}"):
                st.session_state.selected_num = num
                st.session_state.selected_idx = i

        if "selected_num" in st.session_state:
            st.markdown(f"選択中: **{st.session_state.selected_num}**")
            c_name = st.text_input("名前をつけて場に出す")
            if st.button("確定") and c_name:
                if len(my_cards_on_table) < sync_hand_count:
                    table.append({
                        "name": c_name, 
                        "num": st.session_state.selected_num, 
                        "player": st.session_state.my_name
                    })
                    st.session_state.my_hand.pop(st.session_state.selected_idx)
                    del st.session_state.selected_num
                    set_data({"table_data": table})
                    st.rerun()
                else:
                    st.error(f"出せるのは{sync_hand_count}枚までです。")
    
    # 場のエリア（縦並び）
    st.divider()
    st.subheader("🖼️ 場の状況 (上:小 ↓ 下:大)")
    for i, card in enumerate(table):
        is_mine = card['player'] == st.session_state.my_name
        label = f"【{card['num']}】 {card['name']}" if is_mine else f"【？】 {card['name']}"
        st.markdown(f"<div class='card-box {'my-card' if is_mine else ''}'><b>{label}</b></div>", unsafe_allow_html=True)
        st.caption(f"👤 {card['player']}")
        
        if is_mine:
            c1, c2, c3 = st.columns(3)
            if c1.button("⬆️", key=f"U_{i}") and i > 0:
                table[i], table[i-1] = table[i-1], table[i]
                set_data({"table_data": table}); st.rerun()
            if c2.button("↩️ 回収", key=f"Ret_{i}"):
                st.session_state.my_hand.append(card['num'])
                table.pop(i)
                set_data({"table_data": table}); st.rerun()
            if c3.button("⬇️", key=f"D_{i}") and i < len(table)-1:
                table[i], table[i+1] = table[i+1], table[i]
                set_data({"table_data": table}); st.rerun()

    if st.button("全員完了！結果を見る", type="primary"):
        set_data({"status": "OPEN"})
        st.rerun()

# --- 6. 画面表示 (OPEN) ---
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
    
    if st.button("もう一度遊ぶ（リセット）"):
        # 次のゲームのために参加者リスト以外をリセット
        set_data({"status": "SETUP", "table_data": [], "topic": "", "hand_count": 1})
        st.session_state.pop("my_hand", None)
        st.rerun()
