from flask import Flask, render_template, request, jsonify, session
import math

app = Flask(__name__)
app.secret_key = "cyberfit_fujen_secret_key"

# 🛠️ 全域運動計數與狀態資料庫
COUNTER_DB = {
    "counter": 0,
    "status": "就位準備",
    "stage": "up",
    "mode": "reps"
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

@app.route('/')
def index():
    # 這裡維持對齊 detection.html 主偵測艙
    return render_template('detection.html', username=session.get('username', '訪客'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/reset_counter', methods=['POST'])
def reset_counter():
    COUNTER_DB["counter"] = 0
    COUNTER_DB["stage"] = "up"
    COUNTER_DB["status"] = "數據已重置"
    return jsonify({"counter": 0, "status": "數據已重置"})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json() or {}
    exercise = data.get('exercise', '深蹲')
    mode = data.get('mode', 'reps')
    
    # 🛡️ 接收前端傳來的所有核心骨骼關節數據 (X, Y 座標)
    sh, el, wr = data.get('shoulder'), data.get('elbow'), data.get('wrist')
    hp, kn, ak = data.get('hip'), data.get('knee'), data.get('ankle')

    current_angle = 180
    feedback = "請開始動作"
    is_valid = True
    play_ping = False
    
    # =========================================================================
    # ⚙️ 方案 A 鎖定判定邏輯 ── 依據前端選單，雷打不動只執行該動作的公式
    # =========================================================================
    
    # 1. 🦵 下肢與臀腿：深蹲 (Squat)
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
                if COUNTER_DB["stage"] == "down":
                    feedback = "正在站起..."
                else:
                    feedback = f"下蹲深度不足，請再蹲低 {current_angle - 100}°"
                    if current_angle > 140: is_valid = False
        else:
            feedback = "⚠️ 偵測提示：請將下肢、膝蓋與腳踝退至鏡頭內"

    # 2. 🧘 上肢與胸背：伏地挺身 (Pushup)
    elif exercise == "伏地挺身":
        if sh and el and wr:
            current_angle = calculate_angle(sh, el, wr)
            if current_angle > 150:
                COUNTER_DB["status"] = "手臂打直準備"
                if COUNTER_DB["stage"] == "down":
                    COUNTER_DB["stage"] = "up"
                    COUNTER_DB["counter"] += 1
                    play_ping = True
            elif current_angle < 90:
                COUNTER_DB["status"] = "下壓極限"
                COUNTER_DB["stage"] = "down"
                feedback = "胸大肌極限拉伸，標準！"
            else:
                if COUNTER_DB["stage"] == "down":
                    feedback = "正在推起軀幹..."
                else:
                    feedback = f"下壓深度不夠，手肘請再彎曲 {current_angle - 90}°"
                    if current_angle > 130: is_valid = False
        else:
            feedback = "⚠️ 偵測提示：請將上半身、手肘與手腕完整對準鏡頭"

    # 3. 🏋️ 上肢與胸背：肩推 (Press)
    elif exercise == "肩推":
        if sh and el and wr:
            current_angle = calculate_angle(sh, el, wr)
            if current_angle > 155:
                COUNTER_DB["status"] = "雙手推至頂點"
                if COUNTER_DB["stage"] == "down":
                    COUNTER_DB["stage"] = "up"
                    COUNTER_DB["counter"] += 1
                    play_ping = True
            elif current_angle < 85:
                COUNTER_DB["status"] = "手肘下放準備"
                COUNTER_DB["stage"] = "down"
                feedback = "動作到位，準備垂直上推"
            else:
                if COUNTER_DB["stage"] == "down":
                    feedback = "正往上推舉..."
                else:
                    feedback = f"手肘下放幅度不足，請再往下降 {current_angle - 85}°"
        else:
            feedback = "⚠️ 偵測提示：請確保兩側肩膀與雙手手肘在畫面內"

    # 4. 🦵 下肢與臀腿：弓箭步 (Lunge) - 使用雙腿夾角判定
    elif exercise == "弓箭步":
        if hp and kn and ak:
            current_angle = calculate_angle(hp, kn, ak)
            if current_angle > 160:
                COUNTER_DB["status"] = "雙腳站立準備"
                if COUNTER_DB["stage"] == "down":
                    COUNTER_DB["stage"] = "up"
                    COUNTER_DB["counter"] += 1
                    play_ping = True
            elif current_angle < 105:
                COUNTER_DB["status"] = "前後腿跨步下蹲"
                COUNTER_DB["stage"] = "down"
                feedback = "核心收緊，骨盆垂直下壓成功"
            else:
                feedback = f"跨步蹲深度不夠，前膝請再微蹲"
        else:
            feedback = "⚠️ 偵測提示：請側身面向鏡頭，露出完整的髖、膝、踝點"

    # 5. ⏱️ 核心與腹肌：棒式支撐 (Plank) - 計時模式範例 (角度防代償判定)
    elif exercise == "棒式支撐":
        if sh and hp and kn:
            current_angle = calculate_angle(sh, hp, kn) # 計算髖關節是否呈一直線
            if 160 <= current_angle <= 200:
                COUNTER_DB["status"] = "完美棒式直線"
                feedback = "核心持續發力，姿勢非常標準！"
            else:
                COUNTER_DB["status"] = "無效姿勢"
                is_valid = False
                if current_angle < 160:
                    feedback = "🚨 警告：塌腰代償！請用力縮肚子把下背補平"
                else:
                    feedback = "🚨 警告：皮股抬得太高了！身體請壓回一直線"
        else:
            feedback = "⚠️ 偵測提示：請將身體側面向鏡頭，以便AI計算身體直線度"

    # 6. 安全防禦：如果選了其他尚未寫入公式的自訂動作
    else:
        COUNTER_DB["status"] = f"{exercise} 偵測中"
        feedback = "自訂項目幾何數據收集中心，請保持姿勢規律性"

    return jsonify({
        "counter": COUNTER_DB["counter"],
        "status": COUNTER_DB["status"],
        "current_knee_angle": current_angle,
        "feedback": feedback,
        "is_valid": is_valid,
        "play_ping": play_ping
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)