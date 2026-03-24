import streamlit as st
import yfinance as yf
import pandas as pd

# 設定頁面
st.set_page_config(page_title="台股AI分析系統", layout="wide")

st.title("🚀 台股 AI 專業分析系統")

# 側邊欄
symbol = st.sidebar.text_input("輸入股票代號 (例如: 2330)", value="2330")

if symbol:
    try:
        # 抓取資料 (自動嘗試 TW 或 TWO)
        ticker_list = [f"{symbol}.TW", f"{symbol}.TWO"]
        df = pd.DataFrame()
        
        for t_code in ticker_list:
            data = yf.Ticker(t_code).history(period="1y")
            if not data.empty:
                df = data
                break
        
        if not df.empty:
            # 手動計算均線 (不依賴額外套件)
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            
            # 顯示儀表板
            last_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            diff = last_price - prev_price
            
            col1, col2 = st.columns(2)
            col1.metric("當前股價", f"{last_price:.2f}", f"{diff:.2f}")
            col2.metric("5日均線", f"{df['MA5'].iloc[-1]:.2f}")
            
            st.write("### 📈 技術趨勢圖 (收盤價 / MA5 / MA20)")
            st.line_chart(df[['Close', 'MA5', 'MA20']].tail(120))
            
            st.success(f"✅ {symbol} 資料分析成功！")
        else:
            st.error("查無資料，請確認代號是否正確。")
            
    except Exception as e:
        st.error(f"系統啟動中或發生錯誤: {e}")

st.info("💡 小撇步：如果看到畫面閃爍，代表伺服器正在抓取最新報價。")
