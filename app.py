from flask import Flask, render_template

app = Flask(__name__)

# 這是我們網站的主頁路由
@app.route('/')
def home():
    # 讓 Flask 去 templates 資料夾找 home.html 並渲染出來
    return render_template('home.html')

if __name__ == '__main__':
    # 啟動本地測試伺服器，並開啟 debug 模式方便排錯
    app.run(debug=True)