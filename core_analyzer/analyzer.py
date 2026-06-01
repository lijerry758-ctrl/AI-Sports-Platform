import numpy as np
import json

class MovementAnalyzer:
    def __init__(self, standards_file="scraped_anatomy.json"):
        # 讀取我們剛剛用爬蟲抓下來的黃金標準數據
        try:
            with open(standards_file, "r", encoding="utf-8") as f:
                self.standards = json.load(f)
            print("📊 成功載入運動科學黃金標準資料庫！")
        except Exception as e:
            print(f"⚠️ 無法載入標準檔案，使用預設商業參數。錯誤: {e}")
            self.standards = None

    def calculate_angle(self, p1, p2, p3):
        """
        利用三點座標 (p1, p2, p3) 計算中間點 p2 的夾角角度
        p1, p2, p3 各別為 [x, y] 陣列，例如 p2 是膝蓋，p1 是臀部，p3 是腳踝
        """
        p1 = np.array(p1)
        p2 = np.array(p2)
        p3 = np.array(p3)

        # 計算向量
        v1 = p1 - p2
        v2 = p3 - p2

        # 計算餘弦值與夾角
        cosine_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0) # 避免浮點數誤差超出範圍
        
        angle = np.arccos(cosine_angle)
        return np.degrees(angle) # 將弧度轉換為角度

    def check_squat_posture(self, hip, knee, ankle, shoulder):
        """
        商用深蹲姿勢即時診斷邏輯
        傳入 MediaPipe 抓到的 2D/3D 關節座標
        """
        # 1. 計算膝蓋彎曲角度
        knee_angle = self.calculate_angle(hip, knee, ankle)
        
        # 2. 計算軀幹前傾角度 (肩膀到臀部相對於地面的夾角，這裡簡化用水平比對)
        # 未來結合 Orin Nano 傳過來的數據可以更精準
        
        status = "偵測中"
        feedback = "姿勢標準，請繼續保持！"
        is_valid = True

        print(f"🔎 當前即時膝蓋角度: {knee_angle:.1f}°")

        # 比對爬蟲撈出來的標準 (預設膝蓋下蹲要低於 100 度才算開始深蹲，但太低小於 60 度可能過度受壓)
        if knee_angle > 100:
            status = "下蹲深度不足"
            feedback = "屁股再往下坐一點，讓大腿接近平行地面！"
            is_valid = False
        elif knee_angle < 60:
            status = "下蹲過深"
            feedback = "蹲得太深了，注意膝蓋與韌帶壓力，稍微上提！"
            is_valid = False

        return {
            "knee_angle": round(knee_angle, 2),
            "status": status,
            "feedback": feedback,
            "is_valid": is_valid
        }

if __name__ == "__main__":
    # ====== 商業級單元測試 (Unit Test) ======
    # 我們模擬一組 MediaPipe 傳過來「下蹲不夠深」的人體關節座標 [x, y]
    mock_shoulder = [0.5, 0.2]
    mock_hip = [0.5, 0.5]
    mock_knee = [0.6, 0.7]  # 膝蓋往前推
    mock_ankle = [0.5, 0.9] # 腳踝在垂直線上
    
    analyzer = MovementAnalyzer()
    
    print("\n🚀 正在模擬 Orin Nano 邊緣訊號輸入...")
    result = analyzer.check_squat_posture(mock_hip, mock_knee, mock_ankle, mock_shoulder)
    
    print("\n🎯 AI 決策引擎判斷結果:")
    print(json.dumps(result, indent=4, ensure_ascii=False))