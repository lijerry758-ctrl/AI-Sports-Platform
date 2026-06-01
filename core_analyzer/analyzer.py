import numpy as np

class MovementAnalyzer:
    def __init__(self):
        # 🚀 商用升級：完全移除舊的 JSON 檔案讀取邏輯。
        # 因為我們已經有強大的新加坡雲端資料庫了，這裡的大腦只需要維持純淨的數學幾何運算能力！
        print("🧠 幾何分析大腦模組初始化成功（純淨運算版）")

    def calculate_angle(self, p1, p2, p3):
        """
        計算三個連續關節點之間的夾角（例如：髖-膝-踝 或 肩-肘-腕）
        傳入參數: p1, p2, p3 分別為 [x, y] 座標列表
        """
        try:
            if not p1 or not p2 or not p3:
                return 0.0

            # 轉換為 NumPy 向量進行高階幾何運算
            a = np.array(p1)
            b = np.array(p2) # 中間點（角頂點）
            c = np.array(p3)

            ba = a - b
            bc = c - b

            # 計算餘弦值
            cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
            cosine_angle = np.clip(cosine_angle, -1.0, 1.0) # 防止浮點數運算溢出

            # 轉為角度制
            angle = np.arccos(cosine_angle)
            return float(np.degrees(angle))
            
        except Exception as e:
            print(f"⚠️ 幾何大腦角度運算異常: {e}")
            return 0.0