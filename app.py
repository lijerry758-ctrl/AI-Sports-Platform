from flask import Flask, render_template, jsonify, request
import psycopg2
import os
from core_analyzer.analyzer import MovementAnalyzer

app = Flask(__name__)

# 新加坡雲端資料庫連線通行密碼
DB_URL = os.environ.get("DATABASE_URL", "postgresql://sports_science_db_user:A9CGZc224vNlVEGhDYoag9IKUKuedYXv@dpg-d8ep2m740ujc73dqi380-a.singapore-postgres.render.com/sports_science_db")

def get_cloud_angles(exercise_name="深蹲 (Squat)"):
    """【防崩潰防禦機制】從雲端資料庫撈取標準，若連不上，直接依據 10 大動作吐出最安全的小白保護角度"""
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        query = "SELECT min_knee_angle, max_knee_angle FROM motion_standards WHERE exercise_name = %s;"
        cursor.execute(query, (exercise_name,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            return {"min": result[0], "max": result[1]}
    except Exception as e:
        print(f"⚠️ 雲端連線跳過，啟動小白本地安全參數保護: {e}")
    
    # 🎯 這裡直接擴充到 10 種起跳的熱門健身項目，文獻數據隨時防禦
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

@app.route('/api/analyze', methods=['POST'])
def analyze_pose():
    """商業級 API 診斷接口（全面支持 10+ 動作、鏡頭距離改善、語音開關、小白防禦模式）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少關節座標數據"}), 400
        
        # 自由開關語音功能：接收前端傳來的語音開關狀態（預設為 True 開啟）
        voice_enabled = data.get("voice_enabled", True)
        exercise = data.get("exercise", "深蹲 (Squat)")
        
        shoulder = data.get("shoulder")
        hip = data.get("hip")
        knee = data.get("knee")
        ankle = data.get("ankle")

        # 🎥【鏡頭太遠優化機制】：如果人站太遠，座標點數值會極度接近或接近 0
        # 如果關鍵座標缺失，後端直接給予明確提示，不盲目亂判定，徹底解決太遠抓不到的問題
        if not hip or not knee or not ankle:
            return jsonify({
                "exercise_name": exercise,
                "current_knee_angle": 0.0,
                "allowed_range": [0, 0],
                "status": "請靠近鏡頭",
                "feedback": "鏡頭太遠或身體不完整，請往前站一點，讓全身進到畫面上！" if voice_enabled else "",
                "is_valid": False
            })

        standards = get_cloud_angles(exercise)
        analyzer = MovementAnalyzer()
        current_angle = analyzer.calculate_angle(hip, knee, ankle)
        
        # 👶【一律當我是新手小白模式】
        # 不管算出來的角度多精準，核心邏輯提示永遠用最溫柔、最白話、最細心的文字來引導你，不使用任何高深晦澀的術語！
        status = "姿勢標準"
        feedback = "動作做得非常漂亮！很有天賦，保持節奏慢慢來！"
        is_valid = True

        if current_angle > standards["max"]:
            is_valid = False
            if "深蹲" in exercise:
                status = "下蹲深度不足"
                feedback = "注意，屁股要再往下坐一點，想像後面有張小椅子！"
            elif "伏地挺身" in exercise:
                status = "下壓不足"
                feedback = "手臂再彎一點點，讓胸口更接近地面，慢慢來不用急！"
            elif "弓箭步" in exercise:
                status = "下蹲深度不足"
                feedback = "腳步踩穩，身體再往下沉一點，讓前後腳接近九十度！"
            else:
                status = "幅度不足"
                feedback = "動作幅度再加大一點點，你做得到的，加油！"

        elif current_angle < standards["min"]:
            is_valid = False
            if "深蹲" in exercise:
                status = "下蹲過深"
                feedback = "蹲太深囉！注意膝蓋壓力，稍微往上站起一點點！"
            elif "伏地挺身" in exercise:
                status = "支撐過低"
                feedback = "趴得太低了，手肘壓力太重，用手掌力量把身體推起來！"
            elif "弓箭步" in exercise:
                status = "下蹲過深"
                feedback = "太深了，後腳膝蓋快撞到地板了，稍微抬高一點！"
            else:
                status = "幅度過大"
                feedback = "注意，動作做太深了，收回一點點來保護關節！"

        # 🔇 如果使用者關閉語音，後端直接把 feedback 語音文字清空，不發出聲音！
        if not voice_enabled:
            feedback = ""

        # [商業武器 2] 自動寫入雲端 PostgreSQL 大數據庫
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