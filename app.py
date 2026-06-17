from flask import Flask, render_template, request, jsonify, session
import math

app = Flask(__name__)
app.secret_key = "cyberfit_fujen_secret_key"

# 🛠️ 全域運動計數與狀態資料庫（新增：模組 A 歷史數據統計池）
COUNTER_DB = {
    "counter": 0,
    "status": "就位準備",
    "stage": "up",
    "mode": "reps",
    # 📊 專屬大腦記憶庫：儲存學員在本次 Session 中各動作的「真實累計總次數」
    "history": {
        "深蹲": 0,
        "伏地挺身": 0,
        "捲腹": 0,
        "橋式": 0,
        "棒式支撐": 0
    }
}

def calculate_angle(p1, p2, p3):
    """計算三個點形成的夾角"""
    if not p1 or not p2 or not p3: return 180
    try:
        a = math.sqrt((p2[0] - p3[0])**2 + (p2[1] - p3[1])**2)
        b = math.sqrt((p1[0] - p3[0])**2 + (p1[1] - p3[1])**2)
        c = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        return round(math.degrees(math.acos((a**2 + c**2 - b**2) / (2 * a * c))))
    except: 
        return 180

# =========================================================================
# 🌐 基礎頁面與功能通道（確保所有路由都在 app.run 之前註冊完畢）
# =========================================================================

@app.route('/')
def index():
    return render_template('detection.html', username=session.get('username', '訪客'))

@app.route('/dashboard')
def dashboard():
    # 🛡️ 臨時防護線：如果找不到 dashboard.html 就先降階渲染主頁，防止直接噴 Jinja2 錯誤崩潰
    try:
        return render_template('dashboard.html')
    except:
        return render_template('detection.html', username=session.get('username', '訪客'))

@app.route('/profile')
def profile_page():
    return render_template('profile.html')

@app.route('/api/reset_counter', methods=['POST'])
def reset_counter():
    data = request.get_json() or {}
    current_exercise = data.get('exercise', '深蹲')
    
    # 📦 結算心法：在清除當前畫面的 0 之前，把剛剛做完的次數「累加」進去歷史池
    if current_exercise in COUNTER_DB["history"]:
        COUNTER_DB["history"][current_exercise] += COUNTER_DB["counter"]
        
    COUNTER_DB["counter"] = 0
    COUNTER_DB["stage"] = "center" if "stage" in COUNTER_DB else "up"
    COUNTER_DB["status"] = "今日數據已結算存入控制艙"
    
    return jsonify({
        "counter": 0, 
        "status": "數據已重置及結算存入控制艙",
        "history": COUNTER_DB["history"]
    })

@app.route('/api/get_session_status')
def get_session_status():
    return jsonify({
        "user_profile_status": session.get('user_profile_status', 'guest'),
        "ai_schedule": session.get('ai_schedule', []),
        "ai_medical_notes": session.get('ai_medical_notes', [])
    })

# =========================================================================
# 📊 模組 A：提供 Chart.js 讀取真實運動歷史數據的全新數據通道
# =========================================================================
@app.route('/api/get_workout_stats')
def get_workout_stats():
    # 將後端統計好的真實次數，分包打包傳給前端前端控制艙
    labels = list(COUNTER_DB["history"].keys())
    data = list(COUNTER_DB["history"].values())
    return jsonify({
        "labels": labels,
        "data": data,
        "total_today": sum(data)
    })

# =========================================================================
# ⚙️ 方案 A 鎖定機制：動作分析引擎（防暴走完全體防禦網）
# =========================================================================
@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json() or {}
    exercise = data.get('exercise', '深蹲')
    
    sh, el, wr = data.get('shoulder'), data.get('elbow'), data.get('wrist')
    hp, kn, ak = data.get('hip'), data.get('knee'), data.get('ankle')

    current_angle = 180
    feedback = "請開始動作"
    is_valid = True
    play_ping = False
    
    # 🛡️ 鋼鐵防線一：依照個別動作隔離判定，絕不交叉代償
    if exercise == "深蹲":
        if hp and kn and ak:
            current_angle = calculate_angle(hp, kn, ak)
            if current_angle > 160:
                COUNTER_DB["status"] = "站直準備"
                if COUNTER_DB["stage"] == "down":
                    COUNTER_DB["stage"] = "up"
                    COUNTER_DB["counter"] += 1
                    play_ping = True
            elif current_angle < 100:
                COUNTER_DB["status"] = "下蹲頂峰"
                COUNTER_DB["stage"] = "down"
                feedback = "標準深度！穩住核心"
            else:
                feedback = "標準" if COUNTER_DB["stage"] == "down" else f"下蹲深度不足，請再蹲低 {current_angle - 100}°"
        else:
            feedback = "⚠️ 請將下肢、膝蓋與腳踝退至鏡頭內"

    elif exercise == "弓箭步":
        if hp and kn and ak:
            current_angle = calculate_angle(hp, kn, ak)
            if current_angle > 160:
                COUNTER_DB["status"] = "雙腳站立準備"
                if COUNTER_DB["stage"] == "down":
                    COUNTER_DB["stage"] = "up"
                    COUNTER_DB["counter"] += 1
                    play_ping = True
            elif current_angle < 110:
                COUNTER_DB["status"] = "跨步下蹲狀態"
                COUNTER_DB["stage"] = "down"
                feedback = "核心收緊，骨盆垂直下壓成功"
            else:
                feedback = "請繼續保持跨步蹲幅"
        else:
            feedback = "⚠️ 請側身面向鏡頭，露出完整的髖、膝、踝點"

    elif exercise == "橋式":
        if sh and hp and kn:
            current_angle = calculate_angle(sh, hp, kn)
            if current_angle > 165:
                COUNTER_DB["status"] = "臀部頂峰收縮"
                if COUNTER_DB["stage"] == "down":
                    COUNTER_DB["stage"] = "up"
                    COUNTER_DB["counter"] += 1
                    play_ping = True
                    feedback = "夾緊臀部，動作非常標準！"
            elif current_angle < 130:
                COUNTER_DB["status"] = "臀部下放預備"
                COUNTER_DB["stage"] = "down"
        else:
            feedback = "⚠️ 請躺姿側對鏡頭，確保肩膀到膝蓋在畫面內"

    elif exercise == "棒式支撐":
        if sh and hp and kn:
            current_angle = calculate_angle(sh, hp, kn)
            if 160 <= current_angle <= 200:
                COUNTER_DB["status"] = "完美棒式直線"
                feedback = "核心持續發力，姿勢極度標準！"
            else:
                COUNTER_DB["status"] = "無效不良姿勢"
                is_valid = False
                feedback = "🚨 塌腰代償！請挺起肚子" if current_angle < 160 else "🚨 屁股抬得太高了！請壓回直線"
        else:
            feedback = "⚠️ 請側面對鏡頭，以便AI計算身體直線度"

    # 🛡️ 鋼鐵防線二：其餘動作，未開闢精準公式前鎖定計數，絕不給自動灌水的機會！
    else:
        COUNTER_DB["status"] = f"{exercise}自主訓練中"
        feedback = "請手動維持動作行程，AI 正進行姿態收集"

    return jsonify({
        "counter": COUNTER_DB["counter"],
        "status": COUNTER_DB["status"],
        "current_knee_angle": current_angle,
        "feedback": feedback,
        "is_valid": is_valid,
        "play_ping": play_ping
    })

# =========================================================================
# 🦾 模組 B：AI 醫學精準排課演算法
# =========================================================================
@app.route('/api/ai_generate_schedule', methods=['POST'])
def ai_generate_schedule():
    data = request.get_json() or {}
    weight = float(data.get('weight', 70))
    height = float(data.get('height', 170))
    experience = data.get('experience', 'beginner')
    core_strength = data.get('core_strength', 'weak')
    
    bmi = weight / ((height / 100) ** 2)
    recommended_schedule = []
    medical_notes = []
    
    if experience == 'beginner':
        if bmi >= 28:
            medical_notes.append("⚠️ AI 醫學評估：檢測到目前關節壓力指數較高且神經連結尚未建立。")
            medical_notes.append("💡 降階處方：已將高衝擊的『弓箭步』安全置換為保護膝蓋的『🍑 橋式』，避免重力加速度摧毀髕骨。")
            recommended_schedule = [
                {"action": "深蹲", "target": 8, "type": "reps", "sets": 3},
                {"action": "橋式", "target": 12, "type": "reps", "sets": 3},
                {"action": "棒式支撐", "target": 15, "type": "seconds", "sets": 3}
            ]
        else:
            medical_notes.append("🔰 AI 智慧提示：新學員入門，系統已為您隱藏超高難度動作。")
            recommended_schedule = [
                {"action": "深蹲", "target": 12, "type": "reps", "sets": 3},
                {"action": "伏地挺身", "target": 8, "type": "reps", "sets": 3},
                {"action": "捲腹", "target": 10, "type": "reps", "sets": 3}
            ]
    else:
        medical_notes.append("🔥 AI 戰力評估：高階老手艙解鎖！11 大動作核心禁區全面開放。")
        plank_time = 60 if core_strength == 'strong' else 30
        recommended_schedule = [
            {"action": "波比跳", "target": 12, "type": "reps", "sets": 4},
            {"action": "引體向上", "target": 8, "type": "reps", "sets": 3},
            {"action": "棒式支撐", "target": plank_time, "type": "seconds", "sets": 3}
        ]

    session['ai_schedule'] = recommended_schedule
    session['ai_medical_notes'] = medical_notes
    session['user_profile_status'] = "has_profile"
    
    return jsonify({
        "status": "success",
        "schedule": recommended_schedule,
        "notes": medical_notes
    })

# =========================================================================
# 🚀 終極啟動控制核心（這行必須永遠放在檔案的最後一根底線！）
# =========================================================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)