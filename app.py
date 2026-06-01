from flask import Flask, render_template, jsonify, request
import psycopg2
# 修改成商用模組化路徑：
from core_analyzer.analyzer import MovementAnalyzer

app = Flask(__name__)

# 新加坡雲端資料庫連線通行密碼
DB_URL = "postgresql://sports_science_db_user:A9CGZc224vNlVEGhDYoag9IKUKuedYXv@dpg-d8ep2m740ujc73dqi380-a.singapore-postgres.render.com/sports_science_db"

def get_cloud_angles(exercise_name="深蹲 (Squat)"):
    """從雲端 PostgreSQL 資料庫即時讀取爬蟲抓到的黃金角度標準"""
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # 查詢特定動作的角度限制
        query = "SELECT min_knee_angle, max_knee_angle FROM motion_standards WHERE exercise_name = %s;"
        cursor.execute(query, (exercise_name,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            return {"min": result[0], "max": result[1]}
    except Exception as e:
        print(f"⚠️ 讀取雲端資料庫失敗，使用內建安全防禦參數。錯誤: {e}")
    
    # 如果資料庫連線異常，提供商用預設防禦數據，確保系統不崩潰
    return {"min": 60.0, "max": 100.0}

# # 1. 這是我們網站的主頁
@app.route('/')
def home():
    return render_template('home.html')

# # 2. 這是新加坡的：AI 運動偵測頁面
@app.route('/detection')
def detection():
    # 讓 Flask 去 templates 資料夾找 detection.html 並渲染出來
    return render_template('detection.html')

# ====== 🚀 商業級 API 接口：提供給前端網頁或 Jetson Orin Nano 進行即時姿勢判定 ======
@app.route('/api/analyze', methods=['POST'])
def analyze_pose():
    """
    接收來自前端網頁相機或 Jetson Orin Nano 傳過來的即時關節座標，
    並結合雲端資料庫的角度標準進行即時運算診斷。
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少關節座標數據"}), 400
        
        # 解析傳入的四個關鍵關節點座標 [x, y]
        shoulder = data.get("shoulder")
        hip = data.get("hip")
        knee = data.get("knee")
        ankle = data.get("ankle")
        exercise = data.get("exercise", "深蹲 (Squat)")

        # 1. 從雲端資料庫動態撈取爬蟲抓到的黃金角度標準
        standards = get_cloud_angles(exercise)

        # 2. 初始化幾何分析引擎
        analyzer = MovementAnalyzer()
        
        # 3. 進行即時幾何運算
        knee_angle = analyzer.calculate_angle(hip, knee, ankle)
        
        # 4. 根據資料庫撈出來的標準進行動態判定
        status = "姿勢標準"
        feedback = "姿勢標準，請繼續保持！"
        is_valid = True

        if knee_angle > standards["max"]:
            status = "下蹲深度不足"
            feedback = "屁股再往下坐一點，讓大腿接近平行地面！"
            is_valid = False
        elif knee_angle < standards["min"]:
            status = "下蹲過深"
            feedback = "蹲得太深了，注意膝蓋與韌帶壓力，稍微上提！"
            is_valid = False

        # 回傳商業級 JSON 診斷報告
        return jsonify({
            "exercise_name": exercise,
            "current_knee_angle": round(knee_angle, 2),
            "allowed_range": [standards["min"], standards["max"]],
            "status": status,
            "feedback": feedback,
            "is_valid": is_valid
        })

    except Exception as e:
        return jsonify({"error": f"後端運算異常: {str(e)}"}), 500

if __name__ == '__main__':
    # 讓同一個 Wi-Fi 底下的手機平板都能連進來
    app.run(host='0.0.0.0', port=5000, debug=True)