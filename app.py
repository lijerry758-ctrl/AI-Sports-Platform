from flask import Flask, render_template, jsonify, request
import psycopg2
import os
from core_analyzer.analyzer import MovementAnalyzer

app = Flask(__name__)

DB_URL = os.environ.get("DATABASE_URL", "postgresql://sports_science_db_user:A9CGZc224vNlVEGhDYoag9IKUKuedYXv@dpg-d8ep2m740ujc73dqi380-a.singapore-postgres.render.com/sports_science_db")

# 🧠 全域狀態記憶庫（用來記住目前的次數與動作狀態）
# stage: "up" 代表人在上面/站立，"down" 代表成功蹲下去/及格
workout_counter = {
    "counter": 0,
    "stage": "up",
    "current_exercise": ""
}

def get_cloud_angles(exercise_name):
    standards_map = {
        "深蹲": {"min": 60.0, "max": 100.0, "up_threshold": 150.0},
        "伏地挺身": {"min": 70.0, "max": 120.0, "up_threshold": 160.0},
        "弓箭步": {"min": 80.0, "max": 105.0, "up_threshold": 150.0},
        "開合跳": {"min": 150.0, "max": 180.0, "up_threshold": 140.0},
        "棒式支撐": {"min": 165.0, "max": 180.0, "up_threshold": 160.0},
        "仰臥起坐": {"min": 45.0, "max": 90.0, "up_threshold": 160.0},
        "引體向上": {"min": 40.0, "max": 130.0, "up_threshold": 160.0},
        "波比跳": {"min": 70.0, "max": 160.0, "up_threshold": 150.0},
        "啞鈴舉背": {"min": 80.0, "max": 120.0, "up_threshold": 160.0},
        "橋式": {"min": 140.0, "max": 175.0, "up_threshold": 130.0}
    }
    for key, val in standards_map.items():
        if key in exercise_name:
            return val
    return {"min": 60.0, "max": 100.0, "up_threshold": 150.0}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/detection')
def detection():
    return render_template('detection.html')

# 🎯 新增：重設計數器的接口（換動作或按暫停時可以歸零）
@app.route('/api/reset_counter', methods=['POST'])
def reset_counter():
    global workout_counter
    workout_counter["counter"] = 0
    workout_counter["stage"] = "up"
    return jsonify({"status": "success", "counter": 0})

@app.route('/api/analyze', methods=['POST'])
def analyze_pose():
    global workout_counter
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少關節座標數據"}), 400
        
        voice_enabled = data.get("voice_enabled", True)
        exercise = data.get("exercise", "深蹲 (Squat)")
        
        shoulder = data.get("shoulder")
        hip = data.get("hip")
        knee = data.get("knee")
        ankle = data.get("ankle")

        if not hip or not knee or not ankle:
            return jsonify({
                "exercise_name": exercise,
                "current_knee_angle": 0.0,
                "status": "請靠近鏡頭",
                "feedback": "鏡頭太遠或身體不完整，請往前站一點，讓全身進到畫面上！" if voice_enabled else "",
                "is_valid": False,
                "counter": workout_counter["counter"]
            })

        # AI 自動動作辨識
        if shoulder and hip:
            height_diff = abs(shoulder[1] - hip[1])
            if height_diff < 0.15:
                if "Plank" in exercise or "棒式" in exercise:
                    current_exec_name = "棒式支撐"
                else:
                    current_exec_name = "伏地挺身"
            else:
                if "Pushup" in exercise or "伏地挺身" in exercise:
                    current_exec_name = "深蹲"
                else:
                    current_exec_name = exercise.split(" ")[0]

        # 如果使用者突然在網頁或肉身換了動作，計數器貼心地自動歸零重算
        if workout_counter["current_exercise"] != current_exec_name:
            workout_counter["current_exercise"] = current_exec_name
            workout_counter["counter"] = 0
            workout_counter["stage"] = "up"

        standards = get_cloud_angles(current_exec_name)
        analyzer = MovementAnalyzer()
        current_angle = analyzer.calculate_angle(hip, knee, ankle)
        
        status = "姿勢標準"
        feedback = "標準"
        is_valid = True
        play_ping = False # 🚀 用來控制前端要不要發出「叮咚！」計數音效

        BUFFER = 3.0

        # 🎯【高階核心升級：動作次數狀態機計數邏輯】
        # 1. 判定蹲下（進入合格範圍）
        if current_angle <= (standards["max"] + BUFFER) and current_angle >= (standards["min"] - BUFFER):
            if workout_counter["stage"] == "up":
                workout_counter["stage"] = "down" # 狀態切換：成功蹲下了！

        # 2. 判定站起（回到直立範圍，且之前有確實蹲下去過）
        elif current_angle > standards["up_threshold"] and workout_counter["stage"] == "down":
            workout_counter["stage"] = "up" # 狀態切換：成功站起來了！
            workout_counter["counter"] += 1 # 真正完美的一下，次數＋1！
            play_ping = True # 通知前端敲鐘！

        # 3. 判定姿勢錯誤（太淺或太深）
        if current_angle > (standards["max"] + BUFFER):
            is_valid = False
            angle_gap = int(current_angle - standards["max"])
            status = "下蹲不足"
            feedback = f"再低一點，還差 {angle_gap} 度。"

        elif current_angle < (standards["min"] - BUFFER):
            is_valid = False
            angle_gap = int(standards["min"] - current_angle)
            status = "下蹲過深"
            feedback = f"再高一點，多蹲了 {angle_gap} 度。"

        if not voice_enabled:
            feedback = ""

        # 自動寫入雲端大數據庫
        try:
            log_conn = psycopg2.connect(DB_URL)
            log_cursor = log_conn.cursor()
            insert_log_query = """
            INSERT INTO user_workout_logs (exercise_name, current_angle, status, feedback, is_valid)
            VALUES (%s, %s, %s, %s, %s);
            """
            log_cursor.execute(insert_log_query, (current_exec_name, round(current_angle, 2), status, feedback, is_valid))
            log_conn.commit()
            log_cursor.close()
            log_conn.close()
        except Exception as log_err:
            print(f"⚠️ 大數據寫入跳過: {log_err}")

        return jsonify({
            "exercise_name": current_exec_name,
            "current_knee_angle": round(current_angle, 2),
            "allowed_range": [standards["min"], standards["max"]],
            "status": status,
            "feedback": feedback,
            "is_valid": is_valid,
            "counter": workout_counter["counter"], # 拋給前端顯示
            "play_ping": play_ping # 告訴前端要不要發出叮咚聲
        })

    except Exception as e:
        return jsonify({"error": f"後端運算異常: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)