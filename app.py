from flask import Flask, render_template, jsonify, request
import psycopg2
import os
from core_analyzer.analyzer import MovementAnalyzer

app = Flask(__name__)

# 新加坡雲端資料庫連線通行密碼
DB_URL = os.environ.get("DATABASE_URL", "postgresql://sports_science_db_user:A9CGZc224vNlVEGhDYoag9IKUKuedYXv@dpg-d8ep2m740ujc73dqi380-a.singapore-postgres.render.com/sports_science_db")

# 🧠 全域狀態記憶庫（支援次數與秒數雙模式）
workout_counter = {
    "counter": 0,          # 顯示在網頁面板上的主數字
    "seconds": 0.0,        # 精確秒數累積
    "stage": "up",         # 次數型狀態機狀態
    "current_exercise": ""
}

# 📊 商業級核心配置包：動態指定各運動項目該看的「關鍵關節」與「幾何標準」
EXERCISE_CONFIGS = {
    "深蹲": {"type": "reps", "joints": "leg", "min": 60.0, "max": 100.0, "up": 150.0},
    "弓箭步": {"type": "reps", "joints": "leg", "min": 80.0, "max": 105.0, "up": 150.0},
    "橋式": {"type": "reps", "joints": "leg", "min": 140.0, "max": 175.0, "up": 130.0},
    "伏地挺身": {"type": "reps", "joints": "arm", "min": 70.0, "max": 120.0, "up": 160.0},
    "引體向上": {"type": "reps", "joints": "arm", "min": 40.0, "max": 130.0, "up": 160.0},
    "啞鈴舉背": {"type": "reps", "joints": "arm", "min": 80.0, "max": 120.0, "up": 160.0},
    "仰臥起坐": {"type": "reps", "joints": "core", "min": 45.0, "max": 90.0, "up": 160.0},
    "開合跳": {"type": "reps", "joints": "leg", "min": 150.0, "max": 180.0, "up": 140.0},
    "波比跳": {"type": "reps", "joints": "leg", "min": 70.0, "max": 160.0, "up": 150.0},
    "棒式支撐": {"type": "seconds", "joints": "plank", "min": 160.0, "max": 180.0, "up": 0.0}
}

def init_workout_log_table():
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS user_workout_logs (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) DEFAULT '陳品宸',
            exercise_name VARCHAR(100) NOT NULL,
            current_angle REAL NOT NULL,
            status VARCHAR(100) NOT NULL,
            feedback TEXT NOT NULL,
            is_valid BOOLEAN NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)
        conn.commit()
        cursor.close()
        conn.close()
        print("🗄️ 雲端大數據訓練日誌表同步成功！")
    except Exception as e:
        print(f"⚠️ 大數據表初始化失敗: {e}")

init_workout_log_table()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/detection')
def detection():
    return render_template('detection.html')

# 📡 新增防刷網新接口：重新整理網頁時，主動把大腦還記得的次數拋給網頁，次數就不會歸零！
@app.route('/api/get_current_counter', methods=['GET'])
def get_current_counter():
    global workout_counter
    config = EXERCISE_CONFIGS.get(workout_counter["current_exercise"], {"type": "reps"})
    return jsonify({
        "counter": workout_counter["counter"],
        "mode": config["type"]
    })

@app.route('/api/reset_counter', methods=['POST'])
def reset_counter():
    global workout_counter
    workout_counter["counter"] = 0
    workout_counter["seconds"] = 0.0
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
        
        # 🎯 接收前端傳來的自訂模式設定 ("reps" 或 "seconds")
        user_mode = data.get("mode", "reps")
        
        shoulder = data.get("shoulder")
        hip = data.get("hip")
        knee = data.get("knee")
        ankle = data.get("ankle")
        elbow = data.get("elbow")
        wrist = data.get("wrist")

        if not hip or not knee or not ankle:
            return jsonify({
                "exercise_name": exercise,
                "exercise_type": user_mode,
                "current_knee_angle": 0.0,
                "status": "請靠近鏡頭",
                "feedback": "鏡頭太遠或身體不完整，請往前站一點！" if voice_enabled else "",
                "is_valid": False,
                "counter": workout_counter["counter"]
            })

        current_exec_name = "深蹲"
        for key in EXERCISE_CONFIGS.keys():
            if key in exercise:
                current_exec_name = key
                break

        if workout_counter["current_exercise"] != current_exec_name:
            workout_counter["current_exercise"] = current_exec_name
            workout_counter["counter"] = 0
            workout_counter["seconds"] = 0.0
            workout_counter["stage"] = "up"

        config = EXERCISE_CONFIGS[current_exec_name]
        analyzer = MovementAnalyzer()
        
        if config["joints"] == "arm" and elbow:
            current_angle = analyzer.calculate_angle(shoulder, elbow, wrist)
        elif config["joints"] == "plank" and shoulder:
            current_angle = analyzer.calculate_angle(shoulder, hip, knee)
        elif config["joints"] == "core" and shoulder:
            current_angle = analyzer.calculate_angle(shoulder, hip, knee)
        else:
            current_angle = analyzer.calculate_angle(hip, knee, ankle)

        status, feedback, is_valid, play_ping = "姿勢標準", "標準", True, False
        BUFFER = 3.0

        if config["joints"] == "plank":
            is_horizontal = True
            if shoulder and hip:
                y_diff = abs(shoulder[1] - hip[1])
                x_diff = abs(shoulder[0] - hip[0]) + 0.0001
                if (y_diff / x_diff) > 1.0:
                    is_horizontal = False
            if not is_horizontal:
                is_valid = False
                status, feedback = "請趴下準備", "偵測到您目前為直立姿態，請趴下進入標準姿勢！"

        if is_valid:
            if current_angle > (config["max"] + BUFFER):
                is_valid = False
                angle_gap = int(current_angle - config["max"])
                status = "幅度不足"
                feedback = f"再低一點，還差 {angle_gap} 度。"
                if "棒式" in current_exec_name:
                    status, feedback = "屁股太低", "核心收緊挺直，肚子不要掉下去！"
            elif current_angle < (config["min"] - BUFFER):
                is_valid = False
                status = "幅度過大"
                feedback = "動作太深了，請調整。"
                if "棒式" in current_exec_name:
                    status, feedback = "屁股太高", "屁股抬太高了，身體往下壓保持平直！"

        # 🔄 大腦依據前端傳來的需求，動態切換計時/計次算法
        if user_mode == "seconds":
            if is_valid:
                workout_counter["seconds"] += 0.3
                new_sec = int(workout_counter["seconds"])
                if new_sec > workout_counter["counter"]:
                    workout_counter["counter"] = new_sec
                    play_ping = True
            else:
                if status != "請趴下準備": status = "計時暫停"
        else:
            if is_valid and current_angle <= (config["max"] + BUFFER) and current_angle >= (config["min"] - BUFFER):
                if workout_counter["stage"] == "up": workout_counter["stage"] = "down"
            elif current_angle > config["up"] and workout_counter["stage"] == "down":
                workout_counter["stage"] = "up"
                workout_counter["counter"] += 1
                play_ping = True

        return jsonify({
            "exercise_name": current_exec_name,
            "exercise_type": user_mode,
            "current_knee_angle": round(current_angle, 2),
            "status": status,
            "feedback": feedback if voice_enabled else "",
            "is_valid": is_valid,
            "counter": workout_counter["counter"],
            "play_ping": play_ping
        })
    except Exception as e:
        return jsonify({"error": f"後端運算異常: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)