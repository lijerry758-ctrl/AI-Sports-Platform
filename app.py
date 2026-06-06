from flask import Flask, render_template, request, jsonify, session
import math

app = Flask(__name__)
app.secret_key = "cyberfit_fujen_secret_key"

COUNTER_DB = {
    "counter": 0,
    "status": "就位準備",
    "stage": "up",
    "mode": "reps"
}

def calculate_angle(p1, p2, p3):
    if not p1 or not p2 or not p3: return 180
    try:
        a = math.sqrt((p2[0] - p3[0])**2 + (p2[1] - p3[1])**2)
        b = math.sqrt((p1[0] - p3[0])**2 + (p1[1] - p3[1])**2)
        c = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        return round(math.degrees(math.acos((a**2 + c**2 - b**2) / (2 * a * c))))
    except: return 180

@app.route('/')
def index():
    return render_template('detection.html', username=session.get('username', '訪客'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/reset_counter', methods=['POST'])
def reset_counter():
    print("📡 收到重設次數請求")
    COUNTER_DB["counter"] = 0
    COUNTER_DB["stage"] = "up"
    COUNTER_DB["status"] = "數據已重置"
    return jsonify({"counter": 0, "status": "數據已重置"})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json() or {}
    exercise = data.get('exercise', '深蹲')
    mode = data.get('mode', 'reps')
    
    # 🛡️ 接收前端傳來的所有關節數據
    sh, el, wr = data.get('shoulder'), data.get('elbow'), data.get('wrist')
    hp, kn, ak = data.get('hip'), data.get('knee'), data.get('ankle')

    current_angle = 180
    feedback = "請開始動作"
    is_valid = True
    play_ping = False
    
    # ⚙️ 方案 A 鎖定判定邏輯
    if exercise == "深蹲" and hp and kn and ak:
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
            feedback = "標準"
        else:
            feedback = "標準" if COUNTER_DB["stage"] == "down" else f"下蹲深度不足，差 {current_angle - 100}°"
    
    elif exercise == "伏地挺身" and sh and el and wr:
        current_angle = calculate_angle(sh, el, wr)
        if current_angle > 150:
            COUNTER_DB["status"] = "手臂打直"
            if COUNTER_DB["stage"] == "down":
                COUNTER_DB["stage"] = "up"
                COUNTER_DB["counter"] += 1
                play_ping = True
        elif current_angle < 90:
            COUNTER_DB["status"] = "下壓頂峰"
            COUNTER_DB["stage"] = "down"
            feedback = "標準"
        else:
            feedback = "標準" if COUNTER_DB["stage"] == "down" else "下壓深度不夠"

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