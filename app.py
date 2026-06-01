from flask import Flask, render_template

app = Flask(__name__)

# 這是我們網站的主頁路由
@app.route('/')
def home():
    return "<h1>歡迎來到 AI 運動科技鏡像平台！</h1><p>這是我們小組的期末專案主頁。</p>"

if __name__ == '__main__':
    # 啟動本地測試伺服器，並開啟 debug 模式方便排錯
    app.run(debug=True)