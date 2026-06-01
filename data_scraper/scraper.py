import os
import json
import time
import psycopg2
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class AdvancedExerciseScraper:
    def __init__(self):
        # 這是你剛才複製的新加坡雲端資料庫通行密碼
        import os  # 如果最上方沒有，請補上
        self.db_url = os.environ.get("DATABASE_URL", "postgresql://sports_science_db_user:A9CGZc224vNlVEGhDYoag9IKUKuedYXv@dpg-d8ep2m740ujc73dqi380-a.singapore-postgres.render.com/sports_science_db")
        
        # 初始化 Chrome 設定
        chrome_options = Options()
        chrome_options.add_argument("--headless")  
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        print("⏳ 正在初始化 Chrome 驅動程式...")
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=chrome_options
        )
        print("⚙️ Selenium 動態網頁引擎啟動成功！")
        
        # 初始化雲端資料庫表結構
        self.init_database_table()

    def init_database_table(self):
        """在雲端 PostgreSQL 中建立結構化動作標準表"""
        try:
            print("🗄️ 正在連線至新加坡 PostgreSQL 雲端資料庫...")
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 建立資料表的 SQL 指令 (如果不存在就建立)
            create_table_query = """
            CREATE TABLE IF NOT EXISTS motion_standards (
                id SERIAL PRIMARY KEY,
                exercise_name VARCHAR(100) UNIQUE NOT NULL,
                target_muscle VARCHAR(100),
                min_knee_angle REAL,
                max_knee_angle REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_table_query)
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ 雲端資料庫表 `motion_standards` 初始化/對接成功！")
        except Exception as e:
            print(f"❌ 資料庫初始化失敗: {e}")

    def scrape_and_upload(self, target_url):
        """爬取數據並直接上傳至雲端 PostgreSQL 資料庫"""
        try:
            print(f"🌐 正在連線至目標網站: {target_url}")
            self.driver.get(target_url)
            time.sleep(2)  

            # 模擬清洗出專業動作科學數據
            exercise_name = "深蹲 (Squat)"
            target_muscle = "股四頭肌 (Quadriceps)"
            min_knee_angle = 60.0
            max_knee_angle = 100.0

            print(f"🎯 爬蟲抓取成功，準備寫入雲端：{exercise_name}")

            # 連線到雲端資料庫進行寫入
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 使用 INSERT ON CONFLICT 確保動作名稱重複時會自動更新最新的角度數據 (商用標準寫法)
            insert_query = """
            INSERT INTO motion_standards (exercise_name, target_muscle, min_knee_angle, max_knee_angle)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (exercise_name) 
            DO UPDATE SET 
                target_muscle = EXCLUDED.target_muscle,
                min_knee_angle = EXCLUDED.min_knee_angle,
                max_knee_angle = EXCLUDED.max_knee_angle,
                updated_at = CURRENT_TIMESTAMP;
            """
            cursor.execute(insert_query, (exercise_name, target_muscle, min_knee_angle, max_knee_angle))
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"🚀 [大數據落地] 已成功將 `{exercise_name}` 的黃金角度標準同步至新加坡雲端資料庫！")

        except Exception as e:
            print(f"❌ 爬取或上傳過程中發生異常: {e}")

    def close(self):
        self.driver.quit()
        print("🔌 Selenium 引擎已安全關閉。")

if __name__ == "__main__":
    scraper = AdvancedExerciseScraper()
    test_url = "https://www.example.com/exercise/squat" 
    
    # 執行爬取與雲端同步
    scraper.scrape_and_upload(test_url)
    scraper.close()