from flask import Flask, render_template, jsonify, request
import psycopg2
import os
from core_analyzer.analyzer import MovementAnalyzer

app = Flask(__name__)

# 新加坡雲端資料庫連線通行密碼
DB_URL = os.environ.get("DATABASE_URL", "postgresql://sports_science_db_user:A9CGZc224vNlVEGhDYoag9IKUKuedYXv@dpg-d8ep2m740ujc73dqi380-a.singapore-postgres.render.com/sports_science_db")

# 🧠 全域狀態記憶庫（加入秒數累積變數）
workout_counter = {
    "counter": 0,          # 用來顯示次數或秒數
    "seconds": 0.0,        # 精確秒數小數點（用來做秒數型計時）
    "stage": "up",         # up 或 down 狀態
    "current_exercise": ""
}

def get_cloud_angles(exercise_name):
    """【防崩潰防禦】撈取標準，並針對 10 大項目設定不同的判定關節、運動類型(次數/秒數)與角度限制"""
    standards_map = {
        "深蹲": {"min": 60.0, "max": 100.0, "up_threshold": 150.0, "type": "reps"},
        "伏地挺身": {"min": 70.0, "max": 120.0, "up_threshold": 160.0, "type": "reps"},
        "弓箭步": {"min": 80.0, "max": 105.0, "up_threshold": 150.0, "type": "reps"},
        "開合跳": {"min": 150.0, "max": 180.0, "up_threshold": 140.0, "type": "reps"},
        "棒式支撐": {"min": 160.0, "max": 180.0, "up_threshold": 0.0, "type": "seconds"}, # 身體呈一直線
        "仰臥起坐": {"min": 45.0, "max": 90.0, "up_threshold": 160.0, "type": "reps"},
        "引體向上": {"min": 40.0, "max": 130.0, "up_threshold": 160.0, "type": "reps"},
        "波比跳": {"min": 70.0, "max": 160.0, "up_threshold": 150.0, "type": "reps"},
        "啞鈴舉背": {"min": 80.0, "max": 120.0, "up_threshold": 160.0, "type": "reps"},
        "橋式": {"min": 140.0, "max": 175.0, "up_threshold": 130.0, "type": "reps"}
    }
    
    for key, val in standards_map.items():
        if key in exercise_name:
            return val
    return {"min": 60.0, "max": 100.0, "up_threshold": 150.0, "type": "reps"}

def init_workout_log_table():
    """在雲端建立大數據訓練日誌表"""
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
        print("🗄️ [商業武器 2] 雲端用戶大數據訓練日誌表同步成功！")
    except Exception as e:
        print(f"⚠️ 大數據表初始化失敗: {e}")

init_workout_log_table()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/detection')
def detection():
    return render_template('detection.html')

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
        
        shoulder = data.get("shoulder")
        hip = data.get("hip")
        knee = data.get("knee")
        ankle = data.get("ankle")

        if not hip or not knee or not ankle:
            return jsonify({
                "exercise_name": exercise,
                "exercise_type": "reps",
                "current_knee_angle": 0.0,
                "status": "請靠近鏡頭",
                "feedback": "鏡頭太遠或身體不完整，請往前站一點，讓全身進到畫面上！" if voice_enabled else "",
                "is_valid": False,
                "counter": workout_counter["counter"]
            })

        # AI 自動動作辨識
        current_exec_name = exercise.split(" ")[0]
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

        # 切換動作時，計數器與計時器自動歸零
        if workout_counter["current_exercise"] != current_exec_name:
            workout_counter["current_exercise"] = current_exec_name
            workout_counter["counter"] = 0
            workout_counter["seconds"] = 0.0
            workout_counter["stage"] = "up"

        standards = get_cloud_angles(current_exec_name)
        analyzer = MovementAnalyzer()
        current_angle = analyzer.calculate_angle(hip, knee, ankle)
        
        status = "姿勢標準"
        feedback = "標準"
        is_valid = True
        play_ping = False

        BUFFER = 3.0

        # 1. 姿勢錯誤判定
        if current_angle > (standards["max"] + BUFFER):
            is_valid = False
            angle_gap = int(current_angle - standards["max"])
            if "深蹲" in current_exec_name:
                status = "下蹲不足"
                feedback = f"再低一點，還差 {angle_gap} 度。"
            elif "伏地挺身" in current_exec_name:
                status = "下壓不足"
                feedback = f"再低一點，還差 {angle_gap} 度。"
            elif "棒式" in current_exec_name:
                status = "屁股太低"
                feedback = f"小白注意，屁股太低塌腰了，腰部再挺直一點！"
            else:
                status = "幅度不足"
                feedback = f"再低一點，還差 {angle_gap} 度。"

        elif current_angle < (standards["min"] - BUFFER):
            is_valid = False
            angle_gap = int(standards["min"] - current_angle)
            if "深蹲" in current_exec_name:
                status = "下蹲過深"
                feedback = f"再高一點，多蹲了 {angle_gap} 度。"
            elif "伏地挺身" in current_exec_name:
                status = "支撐過低"
                feedback = f"再高一點，低了 {angle_gap} 度。"
            elif "棒式" in current_exec_name:
                status = "屁股太高"
                feedback = f"小白注意，屁股抬太高了，腰部再往下沉一點！"
            else:
                status = "幅度過大"
                feedback = f"再高一點。"

        # 🎯【高階核心：次數（Reps）與秒數（Seconds）雙模式狀態機】
        if standards.get("type") == "seconds":
            # ⏱️ 秒數型判定（如：棒式）
            if is_valid:
                workout_counter["seconds"] += 0.3 # 前端每 300 毫秒傳一次資料，我們加 0.3 秒
                new_sec = int(workout_counter["seconds"])
                if new_sec > workout_counter["counter"]:
                    workout_counter["counter"] = new_sec
                    play_ping = True # 每過一秒「叮！」一聲
            else:
                # 姿勢不標準時，計時暫停！
                status = "計時暫停"
        else:
            # 🎯 次數型判定（如：深蹲、伏地挺身）
            # A. 進入下蹲狀態
            if current_angle <= (standards["max"] + BUFFER) and current_angle >= (standards["min"] - BUFFER):
                if workout_counter["stage"] == "up":
                    workout_counter["stage"] = "down"

            # B. 站直完成動作，次數＋1
            elif current_angle > standards["up_threshold"] and workout_counter["stage"] == "down":
                workout_counter["stage"] = "up"
                workout_counter["counter"] += 1
                play_ping = True

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
            "exercise_type": standards.get("type", "reps"), # 拋給前端判斷是秒數還是次數
            "current_knee_angle": round(current_angle, 2),
            "allowed_range": [standards["min"], standards["max"]],
            "status": status,
            "feedback": feedback,
            "is_valid": is_valid,
            "counter": workout_counter["counter"],
            "play_ping": play_ping
        })

    except Exception as e:
        return jsonify({"error": f"後端運算異常: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)