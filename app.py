import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, date, time, timedelta

# ==========================================
# 1. 頁面基本設定與自訂樣式
# ==========================================
st.set_page_config(
    page_title="Anna & Fergal 減脂生死鬥",
    page_icon="🔥",
    layout="wide"
)

st.markdown("""
<style>
    .profile-card {
        padding: 18px;
        border-radius: 14px;
        border: 2px solid #e0e0e0;
        text-align: center;
        transition: 0.3s;
    }
    .profile-active {
        border: 3px solid #ff4b4b;
        background-color: rgba(255, 75, 75, 0.08);
    }
    .coach-box-roast {
        padding: 16px 20px;
        border-radius: 12px;
        background-color: #2b1111;
        border-left: 6px solid #ff4b4b;
        color: #ffcccc;
        font-size: 1.05rem;
        margin-bottom: 18px;
    }
    .coach-box-praise {
        padding: 16px 20px;
        border-radius: 12px;
        background-color: #102a1c;
        border-left: 6px solid #00cc66;
        color: #ccffdd;
        font-size: 1.05rem;
        margin-bottom: 18px;
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "fat_loss_data.json"

# ==========================================
# 2. 資料讀寫與初始化
# ==========================================
def get_default_data():
    today = date.today()
    d1 = (today - timedelta(days=2)).isoformat()
    d2 = (today - timedelta(days=1)).isoformat()
    return {
        "users": {
            "Anna": {
                "avatar": "👩",
                "start_weight": 56.0,
                "current_weight": 55.2,
                "target_weight": 50.0,
                "start_bf": 27.0,
                "current_bf": 26.3,
                "target_bf": 22.0,
                "sleep_deadline": "02:00",
                "calorie_limit": 1500
            },
            "Fergal": {
                "avatar": "👨",
                "start_weight": 80.0,
                "current_weight": 78.8,
                "target_weight": 72.0,
                "start_bf": 23.0,
                "current_bf": 22.1,
                "target_bf": 16.0,
                "sleep_deadline": "02:00",
                "calorie_limit": 2000
            }
        },
        "records": {
            "Anna": {
                d1: {
                    "exercise": "有氧運動",
                    "water_cc": 1900,
                    "slept_on_time": True,
                    "calories": 1420,
                    "diet_note": "早餐無糖豆漿+水煮蛋、午餐雞胸沙拉、晚餐燙青菜與魚肉",
                    "poop": "順暢 (1次)",
                    "weight": 55.6,
                    "body_fat": 26.6
                },
                d2: {
                    "exercise": "體態雕塑",
                    "water_cc": 1500,
                    "slept_on_time": False,
                    "calories": 1680,
                    "diet_note": "晚上偷喝了半杯手搖飲",
                    "poop": "微卡/少許",
                    "weight": 55.2,
                    "body_fat": 26.3
                }
            },
            "Fergal": {
                d1: {
                    "exercise": "體態雕塑",
                    "water_cc": 2000,
                    "slept_on_time": True,
                    "calories": 1950,
                    "diet_note": "高蛋白便當、乳清蛋白一杯",
                    "poop": "順暢 (1次)",
                    "weight": 79.3,
                    "body_fat": 22.5
                },
                d2: {
                    "exercise": "有氧運動",
                    "water_cc": 1800,
                    "slept_on_time": True,
                    "calories": 1880,
                    "diet_note": "煎雞腿排去皮、糙米飯半碗",
                    "poop": "順暢 (2次以上)",
                    "weight": 78.8,
                    "body_fat": 22.1
                }
            }
        }
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        data = get_default_data()
        save_data(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

if "selected_user" not in st.session_state:
    st.session_state.selected_user = "Anna"

# ==========================================
# 3. 核心邏輯：目標計算、犀利語錄、週結算
# ==========================================
def calc_goal_progress(user_info):
    w_total = max(user_info["start_weight"] - user_info["target_weight"], 0.1)
    w_done = user_info["start_weight"] - user_info["current_weight"]
    w_pct = min(max(w_done / w_total, 0.0), 1.0)

    bf_total = max(user_info["start_bf"] - user_info["target_bf"], 0.1)
    bf_done = user_info["start_bf"] - user_info["current_bf"]
    bf_pct = min(max(bf_done / bf_total, 0.0), 1.0)

    overall = (w_pct + bf_pct) / 2
    is_winner = (
        user_info["current_weight"] <= user_info["target_weight"]
        and user_info["current_bf"] <= user_info["target_bf"]
    )
    return overall, w_pct, bf_pct, is_winner

def generate_coach_message(user_name, user_info, today_rec, hard_mode=True):
    roasts = []
    praises = []

    if not today_rec:
        return (
            "roast",
            f"📢 **【系統警報】{user_name} 今天完全還沒打卡！** 怎麼，是已經放棄 $1000 獎金，打算把錢雙手奉上給另一半了嗎？快點填寫今天的數據，別想裝死躲過結算！"
        )

    # 飲水檢查
    if today_rec["water_cc"] < 1800:
        short = 1800 - today_rec["water_cc"]
        if hard_mode:
            roasts.append(f"水才喝 {today_rec['water_cc']}cc（還差 {short}cc），你是仙人掌嗎？身體缺水代謝直接當機，脂肪想燒都燒不動，快去灌水！")
        else:
            roasts.append(f"今天喝水量還差 {short}cc 才到 1800cc 喔，快去倒杯水喝，代謝才會順暢！")
    else:
        praises.append(f"飲水 {today_rec['water_cc']}cc 達標，細胞水噹噹，代謝全開！")

    # 睡眠檢查
    if not today_rec["slept_on_time"]:
        if hard_mode:
            roasts.append(f"超過 {user_info['sleep_deadline']} 還不睡覺，是在熬夜幫脂肪開派對嗎？皮質醇飆高、瘦素下降，明天起床直接水腫給你看！")
        else:
            roasts.append(f"昨晚超過 {user_info['sleep_deadline']} 才睡，熬夜會影響減脂荷爾蒙，今晚記得早點休息！")
    else:
        praises.append(f"準時在 {user_info['sleep_deadline']} 前就寢，睡眠燃脂力滿分！")

    # 熱量檢查
    if today_rec["calories"] > user_info["calorie_limit"]:
        over = today_rec["calories"] - user_info["calorie_limit"]
        if hard_mode:
            roasts.append(f"熱量超標 {over} kcal！你嘴裡嚼的每一口快樂，明天都會變成肚皮上的游泳圈，等著週末噴 $100 罰款吧！")
        else:
            roasts.append(f"今日熱量超出上限 {over} kcal，下一餐記得多吃原型食物與蔬菜平衡一下。")
    elif today_rec["calories"] > 0:
        praises.append(f"熱量控制在 {today_rec['calories']} kcal（上限 {user_info['calorie_limit']}），飲食紀律超強！")

    # 運動檢查
    if today_rec["exercise"] == "無":
        if hard_mode:
            roasts.append("今天運動掛零？沙發是有塗強力膠把你黏住嗎？對手都在偷偷流汗搶 $1000 了，你還在躺平！")
        else:
            roasts.append("今天還沒運動喔，哪怕抽空做 20 分鐘有氧或核心雕塑也好，動起來！")
    else:
        praises.append(f"完成「{today_rec['exercise']}」，汗水就是脂肪哭泣的眼淚！")

    # 排便檢查
    if "未排便" in today_rec["poop"]:
        roasts.append("今天還沒排便，滿肚子宿便體重計當然不會對你客氣，多喝水＋補充膳食纖維！")

    if roasts:
        header = f"🔥 **【犀利毒舌教練對 {user_name} 的靈魂拷問】**\n\n" if hard_mode else f"💡 **【給 {user_name} 的今日提醒】**\n\n"
        body = "\n".join([f"- {r}" for r in roasts])
        if praises:
            body += f"\n\n✨ *勉強值得誇獎的地方：{praises[0]}*"
        return "roast", header + body
    else:
        header = f"🏆 **【今日自律王者：{user_name}】**\n\n"
        body = "太狠了！今天所有指標全部完美達標！\n" + "\n".join([f"- ✅ {p}" for p in praises])
        body += "\n\n照這個節奏下去，$1000 獎金根本是你的囊中物！"
        return "praise", header + body

def get_week_dates(ref_date):
    monday = ref_date - timedelta(days=ref_date.weekday())
    return [monday + timedelta(days=i) for i in range(7)]

# ==========================================
# 4. 頂部標題與 $1000 終極大獎戰況看板
# ==========================================
st.title("🔥 Anna & Fergal 情侶減脂生死鬥")
st.caption("先達成個人「體重＋體脂」雙目標者，獨得 **$1,000 元獎金** ｜ 每週結算未達標一項 **罰款 $100**")

anna_prog, _, _, anna_win = calc_goal_progress(data["users"]["Anna"])
fergal_prog, _, _, fergal_win = calc_goal_progress(data["users"]["Fergal"])

if anna_win or fergal_win:
    winner = "Anna" if anna_win else "Fergal"
    st.balloons()
    st.success(f"🎉🎉 恭喜 **{winner}** 率先同時達成體重與體脂終極目標，贏得 **$1,000 元** 大獎！！ 🎉🎉")

with st.container(border=True):
    st.subheader("🏆 $1,000 元大獎爭奪進度條")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.write(f"👩 **Anna 總達成率：{anna_prog*100:.1f}%**")
        st.progress(anna_prog)
    with col_b2:
        st.write(f"👨 **Fergal 總達成率：{fergal_prog*100:.1f}%**")
        st.progress(fergal_prog)

# ==========================================
# 5. 可點選的個人紀錄框 (Anna vs Fergal)
# ==========================================
st.markdown("### 👇 點選切換個人紀錄框")
col_u1, col_u2 = st.columns(2)

for col, uname in zip([col_u1, col_u2], ["Anna", "Fergal"]):
    u = data["users"][uname]
    is_active = st.session_state.selected_user == uname
    diff_w = u["current_weight"] - u["target_weight"]
    with col:
        active_class = "profile-active" if is_active else ""
        st.markdown(f"""
        <div class="profile-card {active_class}">
            <h3>{u['avatar']} {uname} {'🔥 (檢視中)' if is_active else ''}</h3>
            <p style="font-size:1.3rem; font-weight:bold; margin:4px 0;">
                目前體重：{u['current_weight']:.1f} kg ｜ 體脂：{u['current_bf']:.1f}%
            </p>
            <p style="color:gray; margin:0;">
                目標：{u['target_weight']:.1f} kg / {u['target_bf']:.1f}%（體重還差 {max(diff_w, 0):.1f} kg）
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"切換至 {uname} 的紀錄本", key=f"btn_{uname}", use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state.selected_user = uname
            st.rerun()

st.divider()

# ==========================================
# 6. 當前選中對象的儀表板與犀利教練
# ==========================================
curr_user = st.session_state.selected_user
u_info = data["users"][curr_user]
u_records = data["records"][curr_user]

col_head, col_mode = st.columns([3, 1])
with col_head:
    st.header(f"{u_info['avatar']} {curr_user} 的專屬減脂戰情室")
with col_mode:
    hard_mode = st.toggle("🔥 地獄級犀利毒舌模式", value=True)

today_str = date.today().isoformat()
today_rec = u_records.get(today_str, None)
mood, coach_msg = generate_coach_message(curr_user, u_info, today_rec, hard_mode=hard_mode)

box_class = "coach-box-roast" if mood == "roast" else "coach-box-praise"
st.markdown(f'<div class="{box_class}">{coach_msg}</div>', unsafe_allow_html=True)

# ==========================================
# 7. 三大功能分頁
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📝 每日任務與飲食紀錄",
    "📈 體重體脂曲線與目標設定",
    "💸 每週運動累積與罰款結算"
])

# ------------------------------------------
# TAB 1: 每日任務紀錄
# ------------------------------------------
with tab1:
    sel_date = st.date_input("選擇紀錄日期", value=date.today())
    sel_date_str = sel_date.isoformat()
    existing = u_records.get(sel_date_str, {})

    # 可隨時更改的睡眠門禁時間設定
    with st.expander("⏰ 修改每日睡眠門禁時間（目前設定：" + u_info["sleep_deadline"] + " 前睡覺）"):
        h, m = map(int, u_info["sleep_deadline"].split(":"))
        new_sleep_time = st.time_input("設定新的睡覺門禁時間", value=time(h, m))
        if st.button("更新睡眠門禁時間"):
            u_info["sleep_deadline"] = new_sleep_time.strftime("%H:%M")
            save_data(data)
            st.success(f"已將 {curr_user} 的睡眠門禁更新為 **{u_info['sleep_deadline']}**！")
            st.rerun()

    with st.form("daily_log_form"):
        st.subheader(f"📅 {sel_date_str} 任務打卡")
        c1, c2 = st.columns(2)

        with c1:
            ex_options = ["無", "有氧運動", "體態雕塑", "有氧 + 體態雕塑"]
            ex_idx = ex_options.index(existing.get("exercise", "無")) if existing.get("exercise") in ex_options else 0
            exercise = st.selectbox("🏃 今日運動（有氧 / 體態雕塑任選）", ex_options, index=ex_idx)

            water_cc = st.number_input(
                "💧 今日飲水量 (cc) — 目標 1800cc",
                min_value=0, max_value=6000, step=100,
                value=int(existing.get("water_cc", 1800))
            )

            slept_on_time = st.checkbox(
                f"😴 昨晚有在 {u_info['sleep_deadline']} 前睡覺",
                value=bool(existing.get("slept_on_time", True))
            )

        with c2:
            poop_options = ["順暢 (1次)", "順暢 (2次以上)", "微卡/少許", "❌ 今日未排便"]
            poop_idx = poop_options.index(existing.get("poop", "順暢 (1次)")) if existing.get("poop") in poop_options else 0
            poop = st.selectbox("💩 今日排便紀錄", poop_options, index=poop_idx)

            calories = st.number_input(
                f"🍱 今日攝取總熱量 (kcal) — 建議上限 {u_info['calorie_limit']} kcal",
                min_value=0, max_value=10000, step=50,
                value=int(existing.get("calories", 0))
            )

            diet_note = st.text_area(
                "🥗 飲食內容紀錄（三餐 / 零食 / 飲料）",
                value=existing.get("diet_note", ""),
                placeholder="例如：早餐無糖拿鐵+蛋餅、午餐雞胸肉便當、晚餐燙青菜..."
            )

        st.markdown("---")
        st.markdown("**⚖️ 今日體重與體脂測量（有量再更新即可）**")
        w_col1, w_col2 = st.columns(2)
        with w_col1:
            weight_val = st.number_input(
                "體重 (kg)", min_value=30.0, max_value=200.0, step=0.1,
                value=float(existing.get("weight", u_info["current_weight"]))
            )
        with w_col2:
            bf_val = st.number_input(
                "體脂率 (%)", min_value=3.0, max_value=60.0, step=0.1,
                value=float(existing.get("body_fat", u_info["current_bf"]))
            )

        submitted = st.form_submit_button("💾 儲存今日紀錄", use_container_width=True, type="primary")
        if submitted:
            u_records[sel_date_str] = {
                "exercise": exercise,
                "water_cc": water_cc,
                "slept_on_time": slept_on_time,
                "calories": calories,
                "diet_note": diet_note,
                "poop": poop,
                "weight": weight_val,
                "body_fat": bf_val
            }
            # 若為最新日期則同步更新目前體重體脂
            latest_date = max(u_records.keys())
            u_info["current_weight"] = u_records[latest_date]["weight"]
            u_info["current_bf"] = u_records[latest_date]["body_fat"]
            save_data(data)
            st.success(f"✅ {curr_user} 在 {sel_date_str} 的紀錄已儲存！")
            st.rerun()

# ------------------------------------------
# TAB 2: 體重體脂曲線與個人目標設定
# ------------------------------------------
with tab2:
    st.subheader(f"📈 {curr_user} 體重與體脂變化趨勢圖")

    if u_records:
        sorted_dates = sorted(u_records.keys())
        df_chart = pd.DataFrame([
            {
                "日期": d,
                "體重 (kg)": u_records[d]["weight"],
                "體脂率 (%)": u_records[d]["body_fat"],
                "熱量 (kcal)": u_records[d]["calories"],
                "運動": u_records[d]["exercise"],
                "排便": u_records[d]["poop"]
            }
            for d in sorted_dates
        ])

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(
                x=df_chart["日期"], y=df_chart["體重 (kg)"],
                name="體重 (kg)", mode="lines+markers",
                line=dict(color="#ff4b4b", width=3), marker=dict(size=8)
            ),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=df_chart["日期"], y=df_chart["體脂率 (%)"],
                name="體脂率 (%)", mode="lines+markers",
                line=dict(color="#00b4d8", width=3, dash="dot"), marker=dict(size=8)
            ),
            secondary_y=True
        )
        # 目標參考線
        fig.add_hline(y=u_info["target_weight"], line_dash="dash", line_color="#ff4b4b",
                      annotation_text=f"目標體重 {u_info['target_weight']}kg", secondary_y=False)

        fig.update_layout(
            height=400,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig.update_yaxes(title_text="體重 (kg)", secondary_y=False)
        fig.update_yaxes(title_text="體脂率 (%)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 查看完整歷史明細表"):
            st.dataframe(df_chart, use_container_width=True)
    else:
        st.info("目前還沒有歷史紀錄，快去「每日任務」新增第一筆吧！")

    st.divider()
    with st.expander(f"🎯 修改 {curr_user} 的個人體重/體脂目標與熱量上限"):
        with st.form("goal_form"):
            g1, g2, g3 = st.columns(3)
            with g1:
                new_tw = st.number_input("目標體重 (kg)", value=float(u_info["target_weight"]), step=0.1)
            with g2:
                new_tbf = st.number_input("目標體脂率 (%)", value=float(u_info["target_bf"]), step=0.1)
            with g3:
                new_cal = st.number_input("每日熱量上限 (kcal)", value=int(u_info["calorie_limit"]), step=50)
            if st.form_submit_button("更新個人目標"):
                u_info["target_weight"] = new_tw
                u_info["target_bf"] = new_tbf
                u_info["calorie_limit"] = new_cal
                save_data(data)
                st.success("目標已更新！")
                st.rerun()

# ------------------------------------------
# TAB 3: 每週運動累積與罰款結算
# ------------------------------------------
with tab3:
    st.subheader(f"💸 {curr_user} 每週運動累積與罰款結算（未達標一項扣 $100）")
    week_ref = st.date_input("選擇結算週期內的任一天（自動抓取該週一至週日）", value=date.today(), key="week_picker")
    week_days = get_week_dates(week_ref)
    st.caption(f"結算區間：**{week_days[0].isoformat()} (週一)** ～ **{week_days[-1].isoformat()} (週日)**")

    cardio_count = 0
    sculpt_count = 0
    water_fail_days = []
    sleep_fail_days = []
    cal_fail_days = []
    logged_days = 0

    for d in week_days:
        d_str = d.isoformat()
        if d_str in u_records:
            logged_days += 1
            rec = u_records[d_str]
            if "有氧" in rec["exercise"]:
                cardio_count += 1
            if "體態" in rec["exercise"]:
                sculpt_count += 1
            if rec["water_cc"] < 1800:
                water_fail_days.append(f"{d_str} ({rec['water_cc']}cc)")
            if not rec["slept_on_time"]:
                sleep_fail_days.append(d_str)
            if rec["calories"] > u_info["calorie_limit"]:
                cal_fail_days.append(f"{d_str} ({rec['calories']}kcal)")

    # 每週運動指標檢查
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        cardio_ok = cardio_count >= 2
        st.metric(
            label="🏃 本週有氧運動累積（目標 2~3 次）",
            value=f"{cardio_count} 次",
            delta="✅ 達標" if cardio_ok else f"❌ 還差 {2 - cardio_count} 次 (-$100)",
            delta_color="normal" if cardio_ok else "inverse"
        )
        st.progress(min(cardio_count / 3.0, 1.0))

    with c_m2:
        sculpt_ok = sculpt_count >= 3
        st.metric(
            label="🏋️ 本週體態雕塑累積（目標 3~4 次）",
            value=f"{sculpt_count} 次",
            delta="✅ 達標" if sculpt_ok else f"❌ 還差 {3 - sculpt_count} 次 (-$100)",
            delta_color="normal" if sculpt_ok else "inverse"
        )
        st.progress(min(sculpt_count / 4.0, 1.0))

    st.markdown("---")
    st.markdown("#### 🧾 本週罰款明細清單（每未達標一項扣 $100）")

    penalties = []
    if not cardio_ok:
        penalties.append(("每週有氧未達 2 次", 100))
    if not sculpt_ok:
        penalties.append(("每週體態雕塑未達 3 次", 100))
    for wd in water_fail_days:
        penalties.append((f"飲水未滿 1800cc：{wd}", 100))
    for sd in sleep_fail_days:
        penalties.append((f"未在 {u_info['sleep_deadline']} 前睡覺：{sd}", 100))
    for cd in cal_fail_days:
        penalties.append((f"熱量爆表超標：{cd}", 100))

    total_penalty = sum(p[1] for p in penalties)

    if penalties:
        df_pen = pd.DataFrame(penalties, columns=["未達標違規項目", "罰款金額 (元)"])
        st.table(df_pen)
        st.error(f"💸 **{curr_user} 本週累計罰款總額：${total_penalty} 元**（共 {len(penalties)} 項未達標，請自覺上繳公積金！）")
    else:
        st.success(f"🎉 太強了！{curr_user} 本週目前 **0 違規、罰款 $0 元**，荷包與身材都守住了！")

# ==========================================
# 8. 側邊欄：重置範例資料按鈕
# ==========================================
with st.sidebar:
    st.header("⚙️ 系統管理")
    st.write("首次開啟已自動載入示範數據供預覽曲線圖。")
    if st.button("🗑️ 清空示範紀錄（重新開始計算）"):
        fresh = get_default_data()
        fresh["records"]["Anna"] = {}
        fresh["records"]["Fergal"] = {}
        save_data(fresh)
        st.success("已清空所有歷史紀錄！")
        st.rerun()
