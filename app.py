from flask import Flask, render_template, request, jsonify, session
import math

app = Flask(__name__)
app.secret_key = "cyberfit_fujen_secret_key"

# 🛠️ 全域運動計數與狀態資料庫（11大動作商用大滿貫架構）
COUNTER_DB = {
    "counter": 0,
    "status": "就位準備",
    "stage": "up",  # 用於記錄動作行程階段 (up / down / left / right / jump)
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
    return render_template('detection.html', username=session.get('username', '訪客'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/reset_counter', methods=['POST'])
def reset_counter():
    COUNTER_DB["counter"] = 0
    COUNTER_DB["stage"] = "center" if "stage" in COUNTER_DB else "up"
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
    # ⚙️ 方案 A 鎖定機制：11 大核心動作精準判定房間，徹底杜絕狀態交叉污染
    # =========================================================================
    
    # 1. 深蹲 (Squat)
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

    # 2. 弓箭步 (Lunge)
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

    # 3. 橋式 (Glute Bridge)
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

    # 4. 俄羅斯轉體 (Russian Twist)
    elif exercise == "俄羅斯轉體":
        if sh and wr and hp:
            wrist_relative_x = wr[0] - hp[0]
            if wrist_relative_x < -0.15:
                COUNTER_DB["status"] = "向左側扭轉觸地"
                if COUNTER_DB["stage"] in ["right", "center", "up"]:
                    COUNTER_DB["stage"] = "left"
                    COUNTER_DB["counter"] += 1
                    play_ping = True
            elif wrist_relative_x > 0.15:
                COUNTER_DB["status"] = "向右側扭轉觸地"
                if COUNTER_DB["stage"] in ["left", "center", "up"]:
                    COUNTER_DB["stage"] = "right"
                    COUNTER_DB["counter"] += 1
                    play_ping = True
            else:
                COUNTER_DB["status"] = "轉體正中轉折"
                feedback = "核心拉緊，運用腹外斜肌左右交替帶動"
        else:
            feedback = "⚠️ 請坐姿面對鏡頭，確保雙手手腕與骨盆露出"

    # 5. 捲腹 (Crunch)
    elif exercise == "捲腹":
        if sh and hp and kn:
            current_angle = calculate_angle(sh, hp, kn)
            if current_angle < 135:
                COUNTER_DB["status"] = "腹肌腹直肌擠壓"
                if COUNTER_DB["stage"] == "down":
                    COUNTER_DB["stage"] = "up"
                    COUNTER_DB["counter"] += 1
                    play_ping = True
                    feedback = "核心捲起到位！"
            elif current_angle > 155:
                COUNTER_DB["status"] = "平躺預備狀態"
                COUNTER_DB["stage"] = "down"
        else:
            feedback = "⚠️ 請側躺迎向鏡頭，以便 AI 計算軀幹折疊角度"

    # 6. 棒式支撐 (Plank)
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

    # 7. 伏地挺身 (Pushup)
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
                COUNTER_DB["status"] = "下壓胸大肌拉伸"
                COUNTER_DB["stage"] = "down"
                feedback = "標準！"
        else:
            feedback = "⚠️ 請將上半身、手肘與手腕完整對準鏡頭"

    # 8. 肩推 (Press)
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
        else:
            feedback = "⚠️ 請確保兩側肩膀與雙手手肘在畫面內"

    # 9. 引體向上 (Pullup)
    elif exercise == "引體向上":
        if sh and el and wr:
            current_angle = calculate_angle(sh, el, wr)
            if current_angle < 90:
                COUNTER_DB["status"] = "背括肌拉至頂峰"
                if COUNTER_DB["stage"] == "down":
                    COUNTER_DB["stage"] = "up"
                    COUNTER_DB["counter"] += 1
                    play_ping = True
            elif current_angle > 150:
                COUNTER_DB["status"] = "懸吊雙臂打直"
                COUNTER_DB["stage"] = "down"
        else:
            feedback = "⚠️ 請確保單槓與上半身雙手關節皆在鏡頭內"

    # 10. 波比跳 (Burpee)
    elif exercise == "波比跳":
        if sh and hp and kn:
            if hp[1] > 0.75:  # 髖關節座標極低，代表趴下伏地
                COUNTER_DB["status"] = "地面俯臥挺身中"
                COUNTER_DB["stage"] = "down"
            elif hp[1] < 0.45 and COUNTER_DB["stage"] == "down": # 髖關節突然拉高，代表往上爆發跳躍
                COUNTER_DB["status"] = "垂直爆發躍起"
                COUNTER_DB["stage"] = "jump"
                COUNTER_DB["counter"] += 1
                play_ping = True
            else:
                feedback = "下蹲趴下，隨後起身垂直跳躍！"
        else:
            feedback = "⚠️ 波比跳需要全身大範圍移動，請將鏡頭退遠"

    # 11. 登山者 (Climbers)
    elif exercise == "登山者":
        if kn and hp:
            current_angle = calculate_angle(hp, kn, ak) if ak else 180
            COUNTER_DB["status"] = "雙腿高速登山提膝"
            feedback = "有氧燃脂爆發中！維持頻率"
        else:
            feedback = "⚠️ 請俯臥撐姿側對鏡頭，露出雙腿提膝關節"

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