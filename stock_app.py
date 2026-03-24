import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import time
import os
import json

# --- 核心邏輯：手寫技術指標 (避開套件衝突) ---
def get_indicators(df):
    # MA5, MA20
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    # RSI (手寫簡易版)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# --- 頁面配置 ---
st.set_page_config(page_title="台股AI分析系統", layout="wide")
st.markdown("<h1 style='color:#00f2fe;'>🚀 台股 AI 專業分析系統</h1>", unsafe_allow_html=True)

# --- 側邊欄 ---
symbol = st.sidebar.text_input("輸入股票代號", value="2330")
lookback = st.sidebar.selectbox("查找範圍", ["3個月", "6個月", "1年"], index=1)
days_map = {"3個月": 60, "6個月": 120, "1年": 250}

if symbol:
    with st.spinner('AI 正在分析中...'):
        try:
            # 抓取資料
            t = yf.Ticker(f"{symbol}.TW")
            df = t.history(period="1y")
            
            if df.empty:
                t = yf.Ticker(f"{symbol}.TWO")
                df = t.history(period="1y")

            if not df.empty:
                df = get_indicators(df)
                l = df.iloc[-1]
                
                # 顯示數據
                c1, c2, c3 = st.columns(3)
                c1.metric("當前股價", f"{l['Close']:.2f}")
                c2.metric("RSI 指標", f"{l['RSI']:.1f}")
                c3.metric("5日均線", f"{l['MA5']:.2f}")
                
                st.write("### 📈 技術趨勢圖")
                st.line_chart(df[['Close', 'MA5', 'MA20']].tail(days_map[lookback]))
                
                st.success(f"✅ {symbol} 分析完成！")
            else:
                st.error("找不到該股票資料，請檢查代號是否正確。")
        except Exception as e:
            st.error(f"發生錯誤: {e}")

st.info("⚠️ 投資警語：本系統資訊僅供參考，投資需謹慎。")
