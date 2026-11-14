import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, date, time, timedelta

# ==========================================
# 1. 頁面基本設定與全套粉色系自訂樣式
# ==========================================
st.set_page_config(
    page_title="Anna & Fergal 減脂生死鬥",
    page_icon="🎀",
    layout="wide"
)

st.markdown("""
<style>
    /* 整體背景與主文字顏色（櫻花粉漸層） */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #fff5f8 0%, #ffe6ef 100%);
        color: #4a1525;
    }
    [data-testid="stHeader"] {
        background: rgba(255, 245, 248, 0.8);
    }
    /* 側邊欄玫瑰粉背景 */
    [data-testid="stSidebar"] {
        background-color: #ffeaf2;
        border-right: 1px solid #ffc2d6;
    }
    /* 標題與一般文字深莓果色，確保手機深色模式也清晰好讀 */
    h1, h2, h3, h4, p, label, .stMarkdown {
        color: #4a1525 !important;
    }
    /* 主要按鈕（桃粉色） */
    button[kind="primary"] {
        background-color: #ff5c8a !important;
        border-color: #ff5c8a !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        font-weight: bold !important;
    }
    button[kind="primary"]:hover {
        background-color: #e04372 !important;
        border-color: #e04372 !important;
    }
    /* 次要按鈕（白底粉框） */
    button[kind="secondary"] {
        background-color: #ffffff !important;
        border: 1.5px solid #ff8fab !important;
        color: #c9184a !important;
        border-radius: 10px !important;
    }
    button[kind="secondary"]:hover {
        background-color: #fff0f5 !important;
        border-color: #ff477e !important;
    }
    /* 進度條粉色漸層 */
    [data-testid="stProgress"] > div > div > div > div {
        background-image: linear-gradient(90deg, #ff8fab, #ff477e) !important;
    }
    /* 分頁標籤（Tabs）粉色高亮 */
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #d6336c !important;
        border-bottom-color: #ff477e !important;
    }
    /* 雙人切換卡片 */
    .profile-card {
        padding: 18px;
        border-radius: 16px;
        background-color: rgba(255, 255, 255, 0.85);
        border: 2px solid #ffc2d6;
        text-align: center;
        box-shadow: 0 4px 12px rgba(255, 92, 138, 0.10);
        transition: 0.3s;
        margin-bottom: 8px;
    }
    .profile-active {
        border: 3px solid #ff477e;
        background-color: #fff0f6;
        box-shadow: 0 6px 18px rgba(255, 71, 126, 0.22);
    }
    /* 毒舌教練框（深莓果紅粉底＋亮粉紅邊框） */
    .coach-box-roast {
        padding: 16px 20px;
        border-radius: 14px;
        background-color: #590d22;
        border-left: 6px solid #ff4d6d;
        color: #ffe5ec !important;
        font-size: 1.05rem;
        margin-bottom: 18px;
        box-shadow: 0 4px 14px rgba(89, 13, 34, 0.18);
    }
    .coach-box-roast p, .coach-box-roast li, .coach-box-roast strong, .coach-box-roast em {
        color: #ffe5ec !important;
    }
    /* 鼓勵教練框（柔粉白底＋甜美桃粉框） */
    .coach-box-praise {
        padding: 16px 20px;
        border-radius: 14px;
        background-color: #fff0f6;
        border: 1.5px solid #ff8fab;
        border-left: 6px solid #ff477e;
        color: #590d22 !important;
        font-size: 1.05rem;
        margin-bottom: 18px;
        box-shadow: 0 4px 14px rgba(255, 143, 171, 0.2);
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "fat_loss_data_v3.json"

ACTIVITY_LEVELS = {
    "久坐少動 (辦公室/幾乎不運動 ×1.2)": 1.2,
    "輕度活動 (每週運動 1~3 天 ×1.375)": 1.375,
    "中度活動 (每週運動 3~5 天 ×1.55)": 1.55,
    "高度活動 (每週運動 6~7 天 ×1.725)": 1.725
}

# ==========================================
# 2. 核心健康計算公式：BMI、BMR 與活動消耗量
# ==========================================
def calc_bmi(weight_kg, height_cm):
    h_m = height_cm / 100.0
    if h_m <= 0:
        return 0.0, "未知"
    bmi = weight_kg / (h_m ** 2)
    if bmi < 18.5:
        status = "體重過輕"
    elif bmi < 24.0:
        status = "正常範圍"
    elif bmi < 27.0:
        status = "過重"
    else:
        status = "肥胖"
    return bmi, status

def calc_bmr_and_allowable(user_info):
    weight = float(user_info.get("current_weight", 50.0))
    height = float(user_info.get("height", 160.0))
    age = int(user_info.get("age", 26))
    gender = user_info.get("gender", "女")
    act_factor = float(user_info.get("activity_factor", 1.375))

    if gender == "男":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    total_allowable = bmr * act_factor
    activity_burn = total_allowable - bmr
    return round(bmr), round(activity_burn), round(total_allowable)

# ==========================================
# 3. 資料讀寫與初始化（已更新雙方最新目標）
# ==========================================
def get_default_data():
    today = date.today()
    d1 = (today - timedelta(days=1)).isoformat()
    return {
        "users": {
            "Anna": {
                "avatar": "👩🏻",
                "gender": "女",
                "age": 26,
                "height": 151.0,
                "start_weight": 42.1,
                "current_weight": 42.1,
                "target_weight": 40.5,
                "start_bf": 22.6,
                "current_bf": 22.6,
                "target_bf": 20.0,
                "activity_factor": 1.375,
                "sleep_deadline": "02:00"
            },
            "Fergal": {
                "avatar": "👨🏻",
                "gender": "男",
                "age": 26,
                "height": 171.0,
                "start_weight": 68.1,
                "current_weight": 68.1,
                "target_weight": 65.5,
                "start_bf": 21.6,
                "current_bf": 21.6,
                "target_bf": 18.0,
                "activity_factor": 1.375,
                "sleep_deadline": "02:00"
            }
        },
        "records": {
            "Anna": {
                d1: {
                    "exercise": "有氧運動",
                    "exercise_burn": 220,
                    "water_cc": 1900,
                    "slept_on_time": True,
                    "breakfast_note": "無糖豆漿 + 水煮蛋",
                    "breakfast_cal": 260,
                    "lunch_note": "雞胸肉溫沙拉",
                    "lunch_cal": 450,
                    "dinner_note": "清蒸魚 + 燙青菜 + 半碗飯",
                    "dinner_cal": 520,
                    "snack_note": "無糖拿鐵",
                    "snack_cal": 120,
                    "poop": "順暢 (1次)",
                    "weight": 42.1,
                    "body_fat": 22.6
                }
            },
            "Fergal": {
                d1: {
                    "exercise": "體態雕塑",
                    "exercise_burn": 320,
                    "water_cc": 2000,
                    "slept_on_time": True,
                    "breakfast_note": "美式咖啡 + 鮪魚蛋吐司",
                    "breakfast_cal": 420,
                    "lunch_note": "舒肥雞腿健康餐盒",
                    "lunch_cal": 680,
                    "dinner_note": "牛排 + 炒時蔬",
                    "dinner_cal": 750,
                    "snack_note": "乳清蛋白一份",
                    "snack_cal": 140,
                    "poop": "順暢 (1次)",
                    "weight": 68.1,
                    "body_fat": 21.6
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
# 4. 目標進度、熱量加減法與犀利語錄邏輯
# ==========================================
def get_record_calories(rec):
    intake = (
        int(rec.get("breakfast_cal", 0))
        + int(rec.get("lunch_cal", 0))
        + int(rec.get("dinner_cal", 0))
        + int(rec.get("snack_cal", 0))
    )
    burn = int(rec.get("exercise_burn", 0))
    net = intake - burn
    return intake, burn, net

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
    bmr, act_burn, allowable_cal = calc_bmr_and_allowable(user_info)

    if not today_rec:
        return (
            "roast",
            f"📢 **【系統警報】{user_name} 今天完全還沒打卡！** 怎麼，是已經放棄 $1000 獎金，打算把錢雙手奉上給另一半了嗎？快點填寫今天的飲食與運動數據，別想裝死躲過結算！"
        )

    if today_rec.get("water_cc", 0) < 1800:
        short = 1800 - today_rec.get("water_cc", 0)
        if hard_mode:
            roasts.append(f"水才喝 {today_rec.get('water_cc', 0)}cc（還差 {short}cc），你是仙人掌嗎？身體缺水代謝直接當機，脂肪想燒都燒不動，快去灌水！")
        else:
            roasts.append(f"今天喝水量還差 {short}cc 才到 1800cc 喔，快去倒杯水喝，代謝才會順暢！")
    else:
        praises.append(f"飲水 {today_rec.get('water_cc', 0)}cc 達標，細胞水噹噹，代謝全開！")

    if not today_rec.get("slept_on_time", True):
        if hard_mode:
            roasts.append(f"超過 {user_info['sleep_deadline']} 還不睡覺，是在熬夜幫脂肪開派對嗎？皮質醇飆高、瘦素下降，明天起床直接水腫給你看！")
        else:
            roasts.append(f"昨晚超過 {user_info['sleep_deadline']} 才睡，熬夜會影響減脂荷爾蒙，今晚記得早點休息！")
    else:
        praises.append(f"準時在 {user_info['sleep_deadline']} 前就寢，睡眠燃脂力滿分！")

    intake, burn, net_cal = get_record_calories(today_rec)
    if intake == 0:
        roasts.append("今天四餐熱量都填 0？別想靠不填寫來逃避熱量計算，快把早午晚餐和零食老實招來！")
    elif net_cal > allowable_cal:
        over = net_cal - allowable_cal
        if hard_mode:
            roasts.append(
                f"熱量未達標！總食入 {intake} kcal 扣掉運動 {burn} kcal 後，淨攝取高達 **{net_cal} kcal**，硬生生超出你每日可攝取上限（{allowable_cal} kcal）足足 **{over} kcal**！你嘴裡嚼的每一口零食，都會變成週末的 $100 罰款！"
            )
        else:
            roasts.append(
                f"今日淨攝取熱量 {net_cal} kcal（食入 {intake} - 運動 {burn}），超出了每日可攝取上限 {allowable_cal} kcal 約 {over} kcal，記得多動一下或調整下一餐喔！"
            )
    else:
        remain = allowable_cal - net_cal
        praises.append(
            f"熱量完美達標！總食入 {intake} - 運動 {burn} = **淨攝取 {net_cal} kcal**（低於上限 {allowable_cal} kcal，還製造了 {remain} kcal 熱量赤字）！"
        )

    if today_rec.get("exercise", "無") == "無":
        if hard_mode:
            roasts.append("今天運動掛零？沙發是有塗強力膠把你黏住嗎？對手都在偷偷流汗消耗熱量搶 $1000 了，你還在躺平！")
        else:
            roasts.append("今天還沒運動喔，抽空動一動可以增加熱量赤字，讓飲食額度更寬裕！")
    else:
        praises.append(f"完成「{today_rec.get('exercise')}」（消耗 {burn} kcal），汗水就是脂肪哭泣的眼淚！")

    if "未排便" in today_rec.get("poop", ""):
        roasts.append("今天還沒排便，滿肚子宿便體重計當然不會對你客氣，多喝水＋補充膳食纖維！")

    if roasts:
        header = f"🔥 **【犀利毒舌教練對 {user_name} 的靈魂拷問】**\n\n" if hard_mode else f"💡 **【給 {user_name} 的今日提醒】**\n\n"
        body = "\n".join([f"- {r}" for r in roasts])
        if praises:
            body += f"\n\n✨ *勉強值得誇獎的地方：{praises[0]}*"
        return "roast", header + body
    else:
        header = f"👑 **【今日自律王者：{user_name}】**\n\n"
        body = "太狠了！今天所有指標全部完美達標！\n" + "\n".join([f"- ✅ {p}" for p in praises])
        body += "\n\n照這個節奏下去，$1000 獎金根本是你的囊中物！"
        return "praise", header + body

def get_week_dates(ref_date):
    monday = ref_date - timedelta(days=ref_date.weekday())
    return [monday + timedelta(days=i) for i in range(7)]

# ==========================================
# 5. 頂部標題與 $1000 終極大獎戰況看板
# ==========================================
st.title("🎀 Anna & Fergal 情侶減脂生死鬥")
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
        st.write(f"👩🏻 **Anna 總達成率：{anna_prog*100:.1f}%**（目標 40.5kg / 20%）")
        st.progress(anna_prog)
    with col_b2:
        st.write(f"👨🏻 **Fergal 總達成率：{fergal_prog*100:.1f}%**（目標 65.5kg / 18%）")
        st.progress(fergal_prog)

# ==========================================
# 6. 可點選的個人紀錄框 (Anna vs Fergal)
# ==========================================
st.markdown("### 👇 點選切換個人紀錄框")
col_u1, col_u2 = st.columns(2)

for col, uname in zip([col_u1, col_u2], ["Anna", "Fergal"]):
    u = data["users"][uname]
    is_active = st.session_state.selected_user == uname
    diff_w = u["current_weight"] - u["target_weight"]
    diff_bf = u["current_bf"] - u["target_bf"]
    bmi_val, bmi_status = calc_bmi(u["current_weight"], u.get("height", 160.0))
    bmr_v, act_v, allow_v = calc_bmr_and_allowable(u)

    with col:
        active_class = "profile-active" if is_active else ""
        st.markdown(f"""
        <div class="profile-card {active_class}">
            <h3 style="margin-bottom:6px;">{u['avatar']} {uname} {'💖 (檢視中)' if is_active else ''}</h3>
            <p style="font-size:1.25rem; font-weight:bold; margin:4px 0; color:#c9184a !important;">
                目前：{u['current_weight']:.1f} kg ｜ 體脂：{u['current_bf']:.1f}%
            </p>
            <p style="font-size:0.98rem; margin:4px 0;">
                身高：{u.get('height', 160):.0f} cm ｜ <b>BMI：{bmi_val:.1f}（{bmi_status}）</b>
            </p>
            <p style="font-size:0.95rem; color:#d6336c !important; margin:4px 0;">
                每日可攝取熱量：<b>{allow_v} kcal</b>（基礎 {bmr_v} + 活動 {act_v}）
            </p>
            <p style="color:#80233f !important; font-size:0.92rem; margin:4px 0 0 0;">
                🎯 目標：<b>{u['target_weight']:.1f} kg / {u['target_bf']:.1f}%</b>（還差 {max(diff_w, 0):.1f} kg、{max(diff_bf, 0):.1f}%）
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"切換至 {uname} 的紀錄本", key=f"btn_{uname}", use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state.selected_user = uname
            st.rerun()

st.divider()

# ==========================================
# 7. 當前選中對象的儀表板與犀利教練
# ==========================================
curr_user = st.session_state.selected_user
u_info = data["users"][curr_user]
u_records = data["records"][curr_user]
bmr_curr, act_curr, allowable_curr = calc_bmr_and_allowable(u_info)

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
# 8. 三大功能分頁
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📝 每日任務與四餐飲食紀錄",
    "📈 曲線圖、BMI計算機與代謝設定",
    "💸 每週運動累積與罰款結算"
])

# ------------------------------------------
# TAB 1: 每日任務與早午晚零食紀錄
# ------------------------------------------
with tab1:
    sel_date = st.date_input("選擇紀錄日期", value=date.today(), key=f"date_{curr_user}")
    sel_date_str = sel_date.isoformat()
    existing = u_records.get(sel_date_str, {})

    with st.expander("⏰ 修改每日睡眠門禁時間（目前設定：" + u_info["sleep_deadline"] + " 前睡覺）"):
        h, m = map(int, u_info["sleep_deadline"].split(":"))
        new_sleep_time = st.time_input("設定新的睡覺門禁時間", value=time(h, m), key=f"sleep_t_{curr_user}")
        if st.button("更新睡眠門禁時間", key=f"save_sleep_{curr_user}", type="primary"):
            u_info["sleep_deadline"] = new_sleep_time.strftime("%H:%M")
            save_data(data)
            st.success(f"已將 {curr_user} 的睡眠門禁更新為 **{u_info['sleep_deadline']}**！")
            st.rerun()

    with st.form(f"daily_log_form_{curr_user}"):
        st.subheader(f"📅 {sel_date_str} 任務與熱量打卡")
        st.info(f"💡 **{curr_user} 今日熱量標準**：基礎代謝 `{bmr_curr}` + 活動量 `{act_curr}` = **每日可攝取 `{allowable_curr}` kcal**（規則：`總食入熱量 － 運動消耗熱量 ≤ {allowable_curr} kcal` 才算達標！）")

        c1, c2 = st.columns(2)
        with c1:
            ex_options = ["無", "有氧運動", "體態雕塑", "有氧 + 體態雕塑"]
            ex_idx = ex_options.index(existing.get("exercise", "無")) if existing.get("exercise") in ex_options else 0
            exercise = st.selectbox("🏃 今日運動（有氧 / 體態雕塑任選）", ex_options, index=ex_idx)

            exercise_burn = st.number_input(
                "🔥 今日運動消耗熱量 (kcal)",
                min_value=0, max_value=3000, step=10,
                value=int(existing.get("exercise_burn", 0))
            )

        with c2:
            water_cc = st.number_input(
                "💧 今日飲水量 (cc) — 目標 1800cc",
                min_value=0, max_value=6000, step=100,
                value=int(existing.get("water_cc", 1800))
            )

            slept_on_time = st.checkbox(
                f"😴 昨晚有在 {u_info['sleep_deadline']} 前睡覺",
                value=bool(existing.get("slept_on_time", True))
            )

            poop_options = ["順暢 (1次)", "順暢 (2次以上)", "微卡/少許", "❌ 今日未排便"]
            poop_idx = poop_options.index(existing.get("poop", "順暢 (1次)")) if existing.get("poop") in poop_options else 0
            poop = st.selectbox("💩 今日排便紀錄", poop_options, index=poop_idx)

        st.markdown("---")
        st.markdown("#### 🍽️ 每日飲食紀錄（早 / 午 / 晚 / 額外零食）")
        m1, m2 = st.columns(2)
        with m1:
            b_note = st.text_input("🌅 早餐內容", value=existing.get("breakfast_note", ""), placeholder="例如：無糖豆漿 + 水煮蛋")
            b_cal = st.number_input("🌅 早餐熱量 (kcal)", min_value=0, max_value=3000, step=10, value=int(existing.get("breakfast_cal", 0)))

            l_note = st.text_input("☀️ 午餐內容", value=existing.get("lunch_note", ""), placeholder="例如：雞胸肉便當半飯")
            l_cal = st.number_input("☀️ 午餐熱量 (kcal)", min_value=0, max_value=3000, step=10, value=int(existing.get("lunch_cal", 0)))

        with m2:
            d_note = st.text_input("🌙 晚餐內容", value=existing.get("dinner_note", ""), placeholder="例如：燙青菜 + 煎鮭魚")
            d_cal = st.number_input("🌙 晚餐熱量 (kcal)", min_value=0, max_value=3000, step=10, value=int(existing.get("dinner_cal", 0)))

            s_note = st.text_input("🍪 額外零食 / 飲料內容", value=existing.get("snack_note", ""), placeholder="例如：手搖飲微糖、餅乾兩片")
            s_cal = st.number_input("🍪 額外零食 / 飲料熱量 (kcal)", min_value=0, max_value=3000, step=10, value=int(existing.get("snack_cal", 0)))

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

        submitted = st.form_submit_button("💖 儲存今日紀錄並計算熱量達標結果", use_container_width=True, type="primary")
        if submitted:
            u_records[sel_date_str] = {
                "exercise": exercise,
                "exercise_burn": exercise_burn,
                "water_cc": water_cc,
                "slept_on_time": slept_on_time,
                "breakfast_note": b_note,
                "breakfast_cal": b_cal,
                "lunch_note": l_note,
                "lunch_cal": l_cal,
                "dinner_note": d_note,
                "dinner_cal": d_cal,
                "snack_note": s_note,
                "snack_cal": s_cal,
                "poop": poop,
                "weight": weight_val,
                "body_fat": bf_val
            }
            latest_date = max(u_records.keys())
            u_info["current_weight"] = u_records[latest_date]["weight"]
            u_info["current_bf"] = u_records[latest_date]["body_fat"]
            save_data(data)
            st.success(f"✅ {curr_user} 在 {sel_date_str} 的紀錄已儲存！")
            st.rerun()

# ------------------------------------------
# TAB 2: 體重體脂曲線、BMI計算機與代謝設定
# ------------------------------------------
with tab2:
    st.subheader(f"📈 {curr_user} 體重與體脂變化趨勢圖")

    if u_records:
        sorted_dates = sorted(u_records.keys())
        rows = []
        for d in sorted_dates:
            r = u_records[d]
            intake, burn, net = get_record_calories(r)
            rows.append({
                "日期": d,
                "體重 (kg)": r["weight"],
                "體脂率 (%)": r["body_fat"],
                "總食入 (kcal)": intake,
                "運動消耗 (kcal)": burn,
                "淨攝取 (kcal)": net,
                "運動": r["exercise"],
                "排便": r["poop"]
            })
        df_chart = pd.DataFrame(rows)

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(
                x=df_chart["日期"], y=df_chart["體重 (kg)"],
                name="體重 (kg)", mode="lines+markers",
                line=dict(color="#e63973", width=3.5), marker=dict(size=9, color="#c9184a")
            ),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=df_chart["日期"], y=df_chart["體脂率 (%)"],
                name="體脂率 (%)", mode="lines+markers",
                line=dict(color="#ff85a1", width=3, dash="dot"), marker=dict(size=8, color="#ff477e")
            ),
            secondary_y=True
        )
        fig.add_hline(
            y=u_info["target_weight"], line_dash="dash", line_color="#c9184a",
            annotation_text=f"目標體重 {u_info['target_weight']}kg", secondary_y=False
        )
        fig.update_layout(
            height=380,
            paper_bgcolor="rgba(255,255,255,0.6)",
            plot_bgcolor="rgba(255,240,245,0.6)",
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

    # 專屬 BMI 計算機區塊
    st.subheader("🧮 專屬 BMI 身體質量指數計算機")
    bmi_c1, bmi_c2 = st.columns([1, 1])
    with bmi_c1:
        calc_h = st.number_input("輸入身高 (cm)", min_value=100.0, max_value=230.0, value=float(u_info.get("height", 151.0)), step=0.5, key=f"bmi_h_{curr_user}")
        calc_w = st.number_input("輸入體重 (kg)", min_value=30.0, max_value=200.0, value=float(u_info["current_weight"]), step=0.1, key=f"bmi_w_{curr_user}")
    with bmi_c2:
        res_bmi, res_status = calc_bmi(calc_w, calc_h)
        ideal_min = 18.5 * ((calc_h / 100.0) ** 2)
        ideal_max = 24.0 * ((calc_h / 100.0) ** 2)
        st.metric(label="試算 BMI 數值", value=f"{res_bmi:.2f}", delta=f"體位判定：{res_status}")
        st.write(f"📏 該身高對應的標準健康體重區間（BMI 18.5 ~ 24）：**{ideal_min:.1f} kg ～ {ideal_max:.1f} kg**")
        st.caption("台灣衛福部成人 BMI 標準：< 18.5 過輕 ｜ 18.5 ~ 24 正常 ｜ 24 ~ 27 過重 ｜ ≥ 27 肥胖")

    st.divider()

    with st.expander(f"🎯 修改 {curr_user} 的身高、目標體重/體脂與活動量等級"):
        with st.form(f"goal_form_{curr_user}"):
            g1, g2, g3 = st.columns(3)
            with g1:
                new_h = st.number_input("身高 (cm)", value=float(u_info.get("height", 151.0)), step=0.5)
                new_age = st.number_input("年齡 (歲)", min_value=15, max_value=90, value=int(u_info.get("age", 26)), step=1)
            with g2:
                new_tw = st.number_input("目標體重 (kg)", value=float(u_info["target_weight"]), step=0.1)
                new_tbf = st.number_input("目標體脂率 (%)", value=float(u_info["target_bf"]), step=0.1)
            with g3:
                act_labels = list(ACTIVITY_LEVELS.keys())
                act_vals = list(ACTIVITY_LEVELS.values())
                curr_act_idx = act_vals.index(u_info.get("activity_factor", 1.375)) if u_info.get("activity_factor") in act_vals else 1
                sel_act_label = st.selectbox("日常活動量等級（計算每日可攝取熱量用）", act_labels, index=curr_act_idx)

            if st.form_submit_button("更新個人資料與代謝設定", type="primary"):
                u_info["height"] = new_h
                u_info["age"] = new_age
                u_info["target_weight"] = new_tw
                u_info["target_bf"] = new_tbf
                u_info["activity_factor"] = ACTIVITY_LEVELS[sel_act_label]
                save_data(data)
                st.success("個人資料與每日可攝取熱量已更新！")
                st.rerun()

# ------------------------------------------
# TAB 3: 每週運動累積與罰款結算
# ------------------------------------------
with tab3:
    st.subheader(f"💸 {curr_user} 每週運動累積與罰款結算（未達標一項扣 $100）")
    week_ref = st.date_input("選擇結算週期內的任一天（自動抓取該週一至週日）", value=date.today(), key=f"week_picker_{curr_user}")
    week_days = get_week_dates(week_ref)
    st.caption(f"結算區間：**{week_days[0].isoformat()} (週一)** ～ **{week_days[-1].isoformat()} (週日)**")

    cardio_count = 0
    sculpt_count = 0
    water_fail_days = []
    sleep_fail_days = []
    cal_fail_days = []

    for d in week_days:
        d_str = d.isoformat()
        if d_str in u_records:
            rec = u_records[d_str]
            if "有氧" in rec.get("exercise", ""):
                cardio_count += 1
            if "體態" in rec.get("exercise", ""):
                sculpt_count += 1
            if rec.get("water_cc", 0) < 1800:
                water_fail_days.append(f"{d_str} (僅喝 {rec.get('water_cc', 0)}cc)")
            if not rec.get("slept_on_time", True):
                sleep_fail_days.append(d_str)

            intake, burn, net_cal = get_record_calories(rec)
            if intake > 0 and net_cal > allowable_curr:
                cal_fail_days.append(
                    f"{d_str} (食入 {intake} - 運動 {burn} = 淨攝取 {net_cal} > 上限 {allowable_curr} kcal)"
                )

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
        penalties.append((f"淨熱量超標未達標：{cd}", 100))

    total_penalty = sum(p[1] for p in penalties)

    if penalties:
        df_pen = pd.DataFrame(penalties, columns=["未達標違規項目", "罰款金額 (元)"])
        st.table(df_pen)
        st.error(f"💸 **{curr_user} 本週累計罰款總額：${total_penalty} 元**（共 {len(penalties)} 項未達標，請自覺上繳公積金！）")
    else:
        st.success(f"🎉 太強了！{curr_user} 本週目前 **0 違規、罰款 $0 元**，荷包與身材都守住了！")

# ==========================================
# 9. 側邊欄：重置範例資料按鈕
# ==========================================
with st.sidebar:
    st.header("🎀 系統管理")
    st.write(f"目前檢視：**{curr_user}**")
    st.write(f"目標：**{u_info['target_weight']} kg / {u_info['target_bf']}%**")
    st.write(f"基礎代謝 (BMR)：`{bmr_curr}` kcal")
    st.write(f"活動消耗量：`{act_curr}` kcal")
    st.write(f"每日可攝取上限：`{allowable_curr}` kcal")
    st.divider()
    if st.button("🗑️ 清空示範紀錄（重新開始計算）"):
        fresh = get_default_data()
        fresh["records"]["Anna"] = {}
        fresh["records"]["Fergal"] = {}
        save_data(fresh)
        st.success("已清空所有歷史紀錄！")
        st.rerun()
