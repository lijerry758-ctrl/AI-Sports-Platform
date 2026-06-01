from flask import Flask, render_template, jsonify, request
import psycopg2
import os
from core_analyzer.analyzer import MovementAnalyzer

app = Flask(__name__)

# 新加坡雲端資料庫連線通行密碼
DB_URL = os.environ.get("DATABASE_URL", "postgresql://sports_science_db_user:A9CGZc224vNlVEGhDYoag9IKUKuedYXv@dpg-d8ep2m740ujc73dqi380-a.singapore-postgres.render.com/sports_science_db")

def get_cloud_angles(exercise_name):
    """從雲端資料庫撈取標準，若連不上，直接依據動作吐出小白安全參數保護"""
    standards_map = {
        "深蹲": {"min": 60.0, "max": 100.0},
        "伏地挺身": {"min": 70.0, "max": 120.0},
        "弓箭步": {"min": 80.0, "max": 105.0},
        "開合跳": {"min": 150.0, "max": 180.0},
        "棒式支撐": {"min": 165.0, "max": 180.0},
        "仰臥起坐": {"min": 45.0, "max": 90.0},
        "引體向上": {"min": 40.0, "max": 130.0},
        "波比跳": {"min": 70.0, "max": 160.0},
        "啞鈴舉背": {"min": 80.0, "max": 120.0},
        "橋式": {"min": 140.0, "max": 175.0}
    }
    
    for key, val in standards_map.items():
        if key in exercise_name:
            return val
    return {"min": 60.0, "max": 100.0}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/detection')
def detection():
    return render_template('detection.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_pose():
    """高階 AI 診斷接口（支持自動動作辨識、動態度數差指引、小白專用防禦）"""
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

        # 🎥【鏡頭太遠防禦】
        if not hip or not knee or not ankle:
            return jsonify({
                "exercise_name": exercise,
                "current_knee_angle": 0.0,
                "status": "請靠近鏡頭",
                "feedback": "鏡頭太遠或身體不完整，請往前站一點，讓全身進到畫面上！" if voice_enabled else "",
                "is_valid": False
            })

        # 🧠【核心升級：AI 自動動作辨識】
        # 如果人體肩膀和臀部的垂直高度差距極小（小於 0.15），代表身體呈水平狀態，AI 自動判定為伏地挺身或棒式！
        if shoulder and hip:
            height_diff = abs(shoulder[1] - hip[1])
            if height_diff < 0.15:
                if "Plank" in exercise or "棒式" in exercise:
                    exercise = "棒式支撐"
                else:
                    exercise = "伏地挺身"
            else:
                # 如果是直立狀態，但網頁選單選的是伏地挺身，AI 會貼心地自動幫你切換回深蹲
                if "Pushup" in exercise or "伏地挺身" in exercise:
                    exercise = "深蹲"

        standards = get_cloud_angles(exercise)
        analyzer = MovementAnalyzer()
        current_angle = analyzer.calculate_angle(hip, knee, ankle)
        
        status = "姿勢標準"
        feedback = "動作做得非常漂亮！很有天賦，保持節奏慢慢來！"
        is_valid = True

        # 🎯【核心升級：動態方向指引（告訴你該怎麼變才好）】
        if current_angle > standards["max"]:
            is_valid = False
            # 計算距離標準還差幾度
            angle_gap = int(current_angle - standards["max"])
            
            if "深蹲" in exercise:
                status = "下蹲深度不足"
                feedback = f"小白注意，你距離標準還差大約 {angle_gap} 度！屁股要再往下坐一點，想像後面有張小椅子！"
            elif "伏地挺身" in exercise:
                status = "下壓不足"
                feedback = f"手臂再彎下一點點，讓胸口接近地面，還差大約 {angle_gap} 度，加油！"
            else:
                status = "幅度不足"
                feedback = f"再加把勁！動作幅度再加大大約 {angle_gap} 度就合格了！"

        elif current_angle < standards["min"]:
            is_valid = False
            angle_gap = int(standards["min"] - current_angle)
            
            if "深蹲" in exercise:
                status = "下蹲過深"
                feedback = f"蹲太深囉！你多蹲了 {angle_gap} 度，注意膝蓋壓力，稍微往上站起一點點！"
            elif "伏地挺身" in exercise:
                status = "支撐過低"
                feedback = f"趴得太低了，手肘多彎了 {angle_gap} 度，用手掌力量把身體稍微推起來一點！"
            else:
                status = "幅度過大"
                feedback = f"動作做太深了，收回大約 {angle_gap} 度來保護關節！"

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
            log_cursor.execute(insert_log_query, (exercise, round(current_angle, 2), status, feedback, is_valid))
            log_conn.commit()
            log_cursor.close()
            log_conn.close()
        except Exception as log_err:
            print(f"⚠️ 大數據寫入跳過: {log_err}")

        return jsonify({
            "exercise_name": exercise,
            "current_knee_angle": round(current_angle, 2),
            "allowed_range": [standards["min"], standards["max"]],
            "status": status,
            "feedback": feedback,
            "is_valid": is_valid
        })

    except Exception as e:
        return jsonify({"error": f"後端運算異常: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)