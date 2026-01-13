import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import japanize_matplotlib
from matplotlib.colors import ListedColormap
from supabase import create_client, Client
import random, math

# --- A. 初期設定 ---
st.set_page_config(layout="wide", page_title="WT Online Ultimate Pro")
supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

GRID_SIZE = 15
df_master = pd.read_csv("units.csv")

# --- B. 描画エンジン (レーダー・メインマップ統合) ---

def draw_tactical_map(grid, units, my_team):
    """メインマップ：視界制限・HP/AP/高度表示"""
    fig, ax = plt.subplots(figsize=(10, 10), facecolor='#1e212b')
    ax.set_facecolor('#1e212b')
    
    # 0:地面, 1-5:ビル, 6:味方(ミントグリーン), 7:敵(赤)
    cmap = ListedColormap(['#3d2b1f', '#d3d3d3', '#bdbdbd', '#9e9e9e', '#757575', '#424242', '#2ecc71', '#e74c3c'])
    
    display_map = grid.copy().astype(float)
    my_active_units = [u for u in units if u['team'] == my_team and u.get('is_active')]

    for u in units:
        if not u.get('is_active'): continue
        
        # 視界判定 (味方から5マス以内)
        is_visible = (u['team'] == my_team)
        if not is_visible:
            for my_u in my_active_units:
                if math.sqrt((u['pos_x']-my_u['pos_x'])**2 + (u['pos_y']-my_u['pos_y'])**2) <= 5:
                    is_visible = True; break

        if is_visible:
            val = 6 if u['team'] == my_team else 7
            display_map[int(u['pos_x']), int(u['pos_y'])] = val
            
            # 詳細ラベル
            hp_now = int(u.get('hp', 0))
            ap_now = int(u.get('ap', 0))
            z_now = int(u.get('pos_z', 0))
            label = f"{u['unit_name']}\nHP:{hp_now} Z:{z_now} AP:{ap_now}"
            
            label_bg = '#2ecc71' if u['team'] == my_team else '#e74c3c'
            ax.text(u['pos_y'], u['pos_x'] - 0.8, label, color='white', fontsize=8, 
                    fontweight='bold', ha='center', va='bottom',
                    bbox=dict(facecolor=label_bg, alpha=0.9, boxstyle='round,pad=0.3'))

    ax.imshow(display_map, cmap=cmap, vmin=0, vmax=7, interpolation='nearest')
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            if grid[i, j] > 0:
                ax.text(j, i, str(int(grid[i, j])), ha='center', va='center', color='white', alpha=0.3, fontweight='bold')
    return fig

def draw_radar(units, my_team):
    """レーダー機能：バッグワーム隠密対応"""
    fig, ax = plt.subplots(figsize=(4, 4), facecolor='#0d1117')
    ax.set_facecolor('#0d1117')
    for r in [3, 7, 11]:
        circle = plt.Circle((7, 7), r, color='#1b5e20', fill=False, linestyle=':', alpha=0.5)
        ax.add_artist(circle)

    for u in units:
        if u.get('is_active'):
            if u['team'] == my_team or u.get('selected_sub') != 'バッグワーム':
                color = '#2ecc71' if u['team'] == my_team else '#e74c3c'
                ax.scatter(u['pos_y'], u['pos_x'], c=color, s=100, edgecolors='white', alpha=0.8, marker='H')
    ax.set_xlim(-0.5, 14.5); ax.set_ylim(14.5, -0.5); ax.axis('off')
    return fig

# --- C. 戦闘解決エンジン (TypeError対策版) ---

def is_los_clear(u, e, grid):
    steps = max(abs(int(u['pos_x'])-int(e['pos_x'])), abs(int(u['pos_y'])-int(e['pos_y'])))
    if steps == 0: return True
    for i in range(1, steps):
        tx = int(u['pos_x'] + (e['pos_x'] - u['pos_x']) * i / steps)
        ty = int(u['pos_y'] + (e['pos_y'] - u['pos_y']) * i / steps)
        if grid[tx, ty] > max(int(u.get('pos_z', 0)), int(e.get('pos_z', 0))): return False
    return True

def resolve_turn(my_team, enemy_team, mode, grid):
    st.info("戦況を解決中...")
    units = supabase.table("unit_states").select("*").execute().data
    session = supabase.table("game_session").select("*").eq("id", 1).single().execute().data
    
    logs = []
    my_pts = int(session.get('my_points', 0))
    en_pts = int(session.get('enemy_points', 0))

    # 1. 行動解決
    for u in units:
        if not u.get('is_active'): continue
        master = df_master[df_master['name'] == u['unit_name']].iloc[0]
        u['ap'] = int(min(25, u.get('ap', 0) + int(master['mob']) + 5))

        move = u.get('submitted_move')
        if move:
            u['pos_x'], u['pos_y'], u['pos_z'] = int(move['x']), int(move['y']), int(move['z'])
        elif mode == "コンピューター（CPU）" and u['team'] == enemy_team:
            targets = [t for t in units if t['team'] == my_team and t['is_active']]
            if targets:
                target = random.choice(targets)
                u['pos_x'] = int(u['pos_x'] + (1 if target['pos_x'] > u['pos_x'] else -1 if target['pos_x'] < u['pos_x'] else 0))
                u['pos_y'] = int(u['pos_y'] + (1 if target['pos_y'] > u['pos_y'] else -1 if target['pos_y'] < u['pos_y'] else 0))
                u['pos_z'] = int(grid[u['pos_x'], u['pos_y']])

        if u['unit_name'] == 'ハイレイン' and u.get('selected_main') == 'アレクトール':
            if grid[u['pos_x'], u['pos_y']] > 0:
                grid[u['pos_x'], u['pos_y']] -= 1
                u['trn'] = float(u.get('trn', 40) + 10)
                logs.append(f"🦋 ハイレインが建物の一部を吸収！")

    # 2. 攻撃計算
    for u in [u for u in units if u.get('is_active')]:
        master = df_master[df_master['name'] == u['unit_name']].iloc[0]
        cur_trn = float(u.get('trn', master['trn']))
        enemies = [e for e in units if e['team'] != u['team'] and e.get('is_active')]
        main_w = u.get('selected_main', '-')

        for e in enemies:
            dist = math.sqrt((u['pos_x']-e['pos_x'])**2 + (u['pos_y']-e['pos_y'])**2 + (u.get('pos_z',0)-e.get('pos_z',0))**2)
            if dist <= master['rng'] and main_w != '-':
                # ダメージ乱数とクリティカル
                atk = (master['atk'] * 1.5) * (1 + cur_trn/10) * random.uniform(0.85, 1.15)
                if main_w == 'オルガノン': atk *= 2.0; grid[int(e['pos_x']), int(e['pos_y'])] = max(0, grid[int(e['pos_x']), int(e['pos_y'])] - 1)
                elif main_w == 'アイビス' and u['unit_name'] == '雨取 千佳': atk *= 3.0; grid[int(e['pos_x']), int(e['pos_y'])] = max(0, grid[int(e['pos_x']), int(e['pos_y'])] - 2)

                if is_los_clear(u, e, grid) or main_w in ['オルガノン', 'バイパー']:
                    dmg = int(atk)
                    e['hp'] -= dmg
                    logs.append(f"💥 {u['unit_name']} -> {e['unit_name']} ({dmg}ダメ)")
                    if e['hp'] <= 0:
                        e['hp'] = 0; e['is_active'] = False
                        if u['team'] == my_team: my_pts += 1
                        else: en_pts += 1

    # 3. DB一括更新 (キャスト徹底)
    for u in units:
        supabase.table("unit_states").update({
            "hp": float(u['hp']), "pos_x": int(u['pos_x']), "pos_y": int(u['pos_y']), "pos_z": int(u['pos_z']),
            "ap": int(u['ap']), "trn": float(u.get('trn', 10)), "is_active": bool(u['is_active']), "submitted_move": None
        }).eq("unit_name", u['unit_name']).execute()
    
    supabase.table("game_session").update({
        "current_turn": int(session['current_turn']+1), "my_points": int(my_pts), "enemy_points": int(en_pts)
    }).eq("id", 1).execute()
    for l in logs: supabase.table("battle_logs").insert({"turn": int(session['current_turn']), "message": l}).execute()

# --- D. メイン UI ---

st.title("🛰️ WT Online: Ultimate v8")

session = supabase.table("game_session").select("*").eq("id", 1).single().execute().data
live_units = supabase.table("unit_states").select("*").execute().data

with st.sidebar:
    st.header(f"Turn {session['current_turn']} / 10")
    c1, c2 = st.columns(2); c1.metric("味方点", session['my_points']); c2.metric("敵点", session['enemy_points'])
    st.markdown("---")
    st.subheader("📡 レーダー")
    st.pyplot(draw_radar(live_units, "操作チーム"))
    st.markdown("---")
    entry_mode = st.radio("チーム編成", ["部隊プリセット", "カスタム編成"])
    if entry_mode == "部隊プリセット":
        my_t_sel = st.selectbox("自分の部隊", df_master['team'].unique(), index=1)
        en_t_sel = st.selectbox("敵部隊", [t for t in df_master['team'].unique() if t != my_t_sel])
    else:
        my_t_sel = "カスタム"; en_t_sel = "敵チーム"
        customs = st.multiselect("メンバー選択", df_master['name'].unique())

    mode = st.radio("対戦形式", ["友人", "CPU"])
    if st.button("試合開始（初期化）"):
        supabase.table("unit_states").delete().neq("id", 0).execute()
        supabase.table("battle_logs").delete().neq("id", 0).execute()
        selected = df_master[df_master['team'].isin([my_t_sel, en_t_sel])] if entry_mode=="部隊プリセット" else df_master[df_master['name'].isin(customs)]
        for _, row in selected.iterrows():
            supabase.table("unit_states").insert({
                "unit_name": row['name'], "team": row['team'] if entry_mode=="部隊プリセット" else "カスタム",
                "hp": 100, "ap": 20, "trn": float(row['trn']), "pos_x": random.randint(0, 14), "pos_y": random.randint(0, 14), "pos_z": 0, "is_active": True
            }).execute()
        supabase.table("game_session").update({"current_turn": 1, "my_points":0, "enemy_points":0}).eq("id", 1).execute()
        st.rerun()

col_map, col_cmd = st.columns([2, 1])
with col_map:
    if 'grid' not in st.session_state: st.session_state.grid = np.random.randint(0, 4, (GRID_SIZE, GRID_SIZE))
    st.pyplot(draw_tactical_map(st.session_state.grid, live_units, "操作チーム" if entry_mode=="カスタム" else my_t_sel))
    logs = supabase.table("battle_logs").select("*").order("id", desc=True).limit(5).execute().data
    for l in logs: st.caption(f"Turn {l['turn']}: {l['message']}")

with col_cmd:
    st.subheader("🎮 コマンド")
    my_active = [u for u in live_units if (u['team'] == my_t_sel or u['team'] == "カスタム") and u.get('is_active')]
    for u in my_active:
        with st.expander(f"{u['unit_name']} (HP:{int(u['hp'])} AP:{u.get('ap')})"):
            m = df_master[df_master['name'] == u['unit_name']].iloc[0]
            cx1, cx2, cx3 = st.columns(3)
            nx = int(cx1.number_input("X", 0, 14, u['pos_x'], key=f"x{u['unit_name']}"))
            ny = int(cx2.number_input("Y", 0, 14, u['pos_y'], key=f"y{u['unit_name']}"))
            nz = int(cx3.number_input("Z", 0, int(st.session_state.grid[nx, ny]), u['pos_z'], key=f"z{u['unit_name']}"))
            mt = st.selectbox("メイン", [m[f'main{i}'] for i in range(1, 5) if m[f'main{i}'] != '-'], key=f"m{u['unit_name']}")
            st = st.selectbox("サブ", [m[f'sub{i}'] for i in range(1, 5) if m[f'sub{i}'] != '-'], key=f"s{u['unit_name']}")
            cost = (abs(u['pos_x']-nx) + abs(u['pos_y']-ny)) + (abs(u['pos_z']-nz) * 2) + (5 if mt != '-' else 0)
            st.caption(f"消費AP: {cost}")
            if st.button("確定", key=f"b{u['unit_name']}"):
                supabase.table("unit_states").update({"submitted_move": {"x": nx, "y": ny, "z": nz}, "selected_main": mt, "selected_sub": st}).eq("unit_name", u['unit_name']).execute()
                st.success("予約済")
    if st.button("🚨 全行動解決"):
        resolve_turn(my_t_sel, en_t_sel, mode, st.session_state.grid)
        st.rerun()
