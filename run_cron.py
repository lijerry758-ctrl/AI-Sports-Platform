import sys
import os

# 修正模組引用路徑，強迫系統認識 data_scraper 資料夾
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("⏰ [商業武器 1] 雲端自動排程啟動：正在追蹤全球最新運動科學文獻數據...")
    
    # 呼叫你寫好的頂級爬蟲大腦
    from data_scraper.scraper import AdvancedExerciseScraper
    
    scraper = AdvancedExerciseScraper()
    # 執行爬取並自動同步至新加坡 PostgreSQL
    scraper.run()
    
    print("✅ [商業武器 1] 文獻大數據自動覆蓋更新成功！系統已進化至最新版本。")
except Exception as e:
    print(f"❌ 排程自動更新失敗，原因: {e}")