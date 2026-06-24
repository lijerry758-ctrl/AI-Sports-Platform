from flask import Flask, render_template, request, jsonify, session
import math

app = Flask(__name__)
app.secret_key = "cyberfit_fujen_secret_key"

# 🛠️ 全域運動計數與狀態資料庫
COUNTER_DB = {
    "counter": 0,
    "status": "就位準備",
    "stage": "up",
    "mode": "reps",
    # 📊 歷史數據池：Key 完美對齊前端下拉選單
    "history": {
        "深蹲": 0,
        "弓箭步": 0,
        "橋式": 0,
        "棒式支撐": 0
    }
}

# 🎯 課表組數追蹤大腦
SET_TRACKER = {
    "schedule": [],        # 儲存當前生成的動態課表
    "remaining_sets": {}   # 儲存結構: {"深蹲": 3, "橋式": 3}
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
# 🌐 基礎頁面與功能通道
# =========================================================================

@app.route('/')
def index():
    return render_template('detection.html', username=session.get('username', '訪客'))

@app.route('/dashboard')
def dashboard():
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
    
    # 📦 1. 歷史次數累加
    if current_exercise in COUNTER_DB["history"]:
        COUNTER_DB["history"][current_exercise] += COUNTER_DB["counter"]
        
    # 📉 2. 付費會員版專屬：判定是否觸發剩餘組數扣減
    if current_exercise in SET_TRACKER["remaining_sets"]:
        target_reps = 0
        for item in SET_TRACKER["schedule"]:
            if item["action"] == current_exercise:
                target_reps = item["target"]
                break
        
        # 只要達到當前組數目標次數的 70% 以上，就視為完成有效的一組，剩餘組數減 1
        if COUNTER_DB["counter"] >= (target_reps * 0.7) and SET_TRACKER["remaining_sets"][current_exercise] > 0:
            SET_TRACKER["remaining_sets"][current_exercise] -= 1
            status_msg = f"🎉 太棒了！有效完成一組，該動作剩餘組數減 1！"
        else:
            status_msg = f"💡 次數未達標（目標 {target_reps} 下），本組視為熱身，組數未扣減。"
    else:
        # 普通訪客版：自主設定，不進行後台組數扣減
        status_msg = "今日數據已成功結算存入控制艙"

    COUNTER_DB["counter"] = 0
    COUNTER_DB["stage"] = "center" if "stage" in COUNTER_DB else "up"
    COUNTER_DB["status"] = status_msg
    
    return jsonify({
        "counter": 0, 
        "status": COUNTER_DB["status"],
        "history": COUNTER_DB["history"],
        "remaining_sets": SET_TRACKER["remaining_sets"] 
    })

@app.route('/api/get_session_status')
def get_session_status():
    # 🪐 商業切換邏輯：若沒跑過排課演算法，強行判定為 guest 免費普通版
    is_member = "has_profile" if SET_TRACKER["schedule"] else "guest"
    
    updated_schedule = []
    for item in SET_TRACKER["schedule"]:
        action_name = item["action"]
        current_rem = SET_TRACKER["remaining_sets"].get(action_name, item["sets"])
        updated_schedule.append({
            "action": action_name,
            "target": item["target"],
            "type": item["type"],
            "sets": current_rem 
        })
        
    return jsonify({
        "user_profile_status": is_member,
        "ai_schedule": updated_schedule,
        "ai_medical_notes": session.get('ai_medical_notes', [])
    })

@app.route('/api/get_workout_stats')
def get_workout_stats():
    # 📊 過濾：只把「做過大於 0 下」的動作撈給 Chart.js！沒做過的動作直接隱形，不留標籤色塊
    labels = []
    data = []
    for k, v in COUNTER_DB["history"].items():
        if v > 0:
            labels.append(k)
            data.append(v)
            
    # 如果今天完全還沒開始運動，預設給個提示空狀態防止圖表報錯
    if not data:
        return jsonify({"labels": ["今日尚未開始運動"], "data": [0], "total_today": 0})
        
    return jsonify({
        "labels": labels,
        "data": data,
        "total_today": sum(data)
    })

# =========================================================================
# ⚙️ 動作分析引擎（包含全域骨骼物理屏障）
# =========================================================================
@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json() or {}
    exercise = data.get('exercise', '深蹲')
    
    # 接收前端傳入的座標與可信度分數 [x, y, visibility]
    sh, el, wr = data.get('shoulder'), data.get('elbow'), data.get('wrist')
    hp, kn, ak = data.get('hip'), data.get('knee'), data.get('ankle')

    current_angle = 180
    feedback = "請開始動作"
    is_valid = True
    play_ping = False
    
    # =========================================================================
    # 🦾 全動作下肢與核心盲區全鎖死閘門（解決頭頂晃動誤算 Bug）
    # =========================================================================
    if exercise in ["深蹲", "弓箭步", "橋式", "棒式支撐"]:
        # 1. 基礎存在判定
        if not hp or not kn or not ak:
            return jsonify({
                "counter": COUNTER_DB["counter"], "status": "⚠️ 偵測盲區", "current_knee_angle": 180,
                "feedback": "❌ 請退後，將鏡頭往下壓，讓完整的身體與雙腿進入視訊艙內",
                "is_valid": False, "play_ping": False
            })
            
        # 2. Visibility 能見度可信度防禦
        # 檢查髖、膝、踝的可信度分數，只要其中一個低於 60%（0.6），一槍斃命阻斷！
        if len(hp) > 2 and len(kn) > 2 and len(ak) > 2:
            if hp[2] < 0.6 or kn[2] < 0.6 or ak[2] < 0.6:
                return jsonify({
                    "counter": COUNTER_DB["counter"], "status": "⚠️ 核心關節遮擋", "current_knee_angle": 180,
                    "feedback": "❌ 偵測到下半身被遮擋或未入鏡！請確保髖、膝、踝清晰可見",
                    "is_valid": False, "play_ping": False
                })

        # 3. 站姿高度異常判定（深蹲、弓箭步適用）
        if exercise in ["深蹲", "弓箭步"]:
            if hp[1] < 0.45 or kn[1] < 0.55:
                return jsonify({
                    "counter": COUNTER_DB["counter"], "status": "⚠️ 姿態高度異常", "current_knee_angle": 180,
                    "feedback": "🧘 檢測到高度異常！請起身並退後兩公尺，進入完整的全身範圍",
                    "is_valid": False, "play_ping": False
                })

    # =========================================================================
    # ⚡ 各動作幾何邏輯與動態狀態機判定
    # =========================================================================
    if exercise == "深蹲":
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

    elif exercise == "弓箭步":
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

    elif exercise == "橋式":
        if sh:
            if sh[1] < 0.6:
                COUNTER_DB["status"] = "姿態高度異常"
                feedback = "🛌 橋式需要躺姿進行，請躺下並確保全身體線置於鏡頭低位"
                is_valid = False
            else:
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
            feedback = "⚠️ 請確保上半身肩膀在鏡頭內"
            is_valid = False

    elif exercise == "棒式支撐":
        if sh:
            current_angle = calculate_angle(sh, hp, kn)
            if 160 <= current_angle <= 200:
                COUNTER_DB["status"] = "完美棒式直線"
                feedback = "核心持續發力，姿勢極度標準！"
            else:
                COUNTER_DB["status"] = "無效不良姿勢"
                is_valid = False
                feedback = "🚨 塌腰代償！請挺起肚子" if current_angle < 160 else "🚨 屁股抬得太高了！請壓回直線"
        else:
            feedback = "⚠️ 請確保上半身肩膀在鏡頭內"
            is_valid = False

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
    
    bmi = weight / ((height / 100) ** 2)
    recommended_schedule = []
    medical_notes = []
    
    if experience == 'beginner':
        medical_notes.append("🔰 AI 醫學處方：採用『高分段間歇心法』，單組次數減半，保護關節與神經系統。")
        if bmi >= 28:
            medical_notes.append("💡 體重守護機制：已主動封鎖高衝擊動作，改由低關節壓力的躺姿動作切入。")
            recommended_schedule = [
                {"action": "深蹲", "target": 5, "type": "reps", "sets": 3},
                {"action": "橋式", "target": 6, "type": "reps", "sets": 3}
            ]
        else:
            recommended_schedule = [
                {"action": "深蹲", "target": 6, "type": "reps", "sets": 3},
                {"action": "弓箭步", "target": 5, "type": "reps", "sets": 2}
            ]
    else:
        medical_notes.append("🔥 老手釋放機制：開啟全量全身運動行程。")
        recommended_schedule = [
            {"action": "深蹲", "target": 12, "type": "reps", "sets": 4},
            {"action": "弓箭步", "target": 10, "type": "reps", "sets": 3}
        ]

    SET_TRACKER["schedule"] = recommended_schedule
    SET_TRACKER["remaining_sets"] = {item["action"]: item["sets"] for item in recommended_schedule}

    session['ai_medical_notes'] = medical_notes
    session['user_profile_status'] = "has_profile"
    
    return jsonify({
        "status": "success",
        "schedule": recommended_schedule,
        "notes": medical_notes
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)