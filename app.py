from flask import Flask, render_template

app = Flask(__name__)

# 1. 這是我們網站的主頁
@app.route('/')
def home():
    return render_template('home.html')

# 2. 這是新加的：AI 運動偵測頁面
@app.route('/detection')
def detection():
    # 讓 Flask 去 templates 資料夾找 detection.html 並渲染出來
    return render_template('detection.html')

if __name__ == '__main__':
    app.run(debug=True)