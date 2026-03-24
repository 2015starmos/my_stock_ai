import streamlit as st
import yfinance as yf
import pandas as pd
import urllib3
import os
import json
import requests
import time

# 1. 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 2. 頁面配置 ---
st.set_page_config(
    page_title="台股AI專業分析系統",
    page_icon="📈",
    layout="wide"
)

# --- 3. CSS 注入 (完全保留你的原始設計) ---
st.markdown("""
    <style>
    [data-testid="stStatusWidget"] { display: none !important; }
    
    .startup-overlay {
        position: fixed !important; top: 0 !important; left: 0 !important;
        width: 100vw !important; height: 100vh !important;
        background: radial-gradient(circle at center, #1e3a8a 0%, #020617 100%) !important;
        display: flex !important; justify-content: center !important; align-items: center !important;
        flex-direction: column !important; z-index: 999999 !important;
    }
    .startup-box { display: flex; flex-direction: column; align-items: center; animation: quick-zoom 0.5s ease-out forwards; }
    .startup-rocket { font-size: 100px; filter: drop-shadow(0 0 20px #00f2fe); margin-bottom: 20px; }
    .startup-text { color: #00f2fe; font-size: 2.2rem; font-weight: 900; letter-spacing: 6px; text-shadow: 0 0 15px rgba(0,242,254,0.8); }
    @keyframes quick-zoom { 0% { transform: scale(0.8); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }

    .ultra-huge-title {
        font-size: clamp(2rem, 5vw, 4.5rem) !important; font-weight: 900 !important;
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 20px !important;
    }

    .analysis-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 25px; border-radius: 15px; color: white; margin-bottom: 20px;
    }

    .info-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155; border-radius: 12px; padding: 20px;
        color: white; margin-bottom: 15px; position: relative; overflow: hidden;
    }
    .info-container::after {
        content: "📊"; position: absolute; right: -10px; bottom: -10px;
        font-size: 100px; opacity: 0.05; transform: rotate(-15deg);
    }
    .sector-tag {
        background: rgba(59, 130, 246, 0.2); border: 1px solid #3b82f6;
        padding: 4px 12px; border-radius: 20px; font-size: 0.95rem; color: #60a5fa;
    }
    .summary-text { line-height: 1.7; color: #cbd5e1; margin-top: 10px; font-size: 1rem; }

    .core-data-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 25px; border-radius: 15px; border: 1px solid #334155;
        color: white; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .core-data-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
    .data-item { border-left: 3px solid #3b82f6; padding-left: 15px; }
    .data-label { color: #94a3b8; font-size: 0.9rem; margin-bottom: 5px; }
    .data-value { color: #f8fafc; font-size: 1.6rem; font-weight: 800; }

    [data-testid="stForm"] { border: none !important; padding: 0 !important; }
    [data-testid="stExpander"] [data-testid="stVerticalBlock"] { gap: 0rem !important; padding: 0.2rem !important; }
    .stTextInput { margin-top: -5px !important; }
    
    .disclaimer-box { background-color: #fffde7; border: 1px solid #fff59d; border-radius: 8px; padding: 15px; margin: 30px 0 0 0; color: #795548; font-size: 0.95rem; line-height: 1.5; }
    .footer-container { text-align: center; margin-top: 10px; padding-bottom: 20px; line-height: 1.2; }
    .footer-line { color: gray; font-size: 0.9rem; margin: 0 !important; padding: 0 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. 工具函數 ---
def translate_to_chinese(text):
    if not text or text == "暫無資料": return text
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-TW&dt=t&q={requests.utils.quote(text)}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            result = res.json(); return "".join([part[0] for part in result[0] if part[0]])
    except: pass
    return text

W_FILE, N_FILE = "watchlist.txt", "names_map.json"

@st.cache_data(ttl=86400)
def get_official_taiwan_names():
    official_dict = {}
    urls = ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]
    for url in urls:
        try:
            res = requests.get(url, verify=False, timeout=10)
            dfs = pd.read_html(res.text)
            if dfs:
                df = dfs[0]; df.columns = df.iloc[0]; df = df.iloc[1:]
                for item in df['有價證券代號及名稱'].dropna():
                    if '\u3000' in item:
                        code, name = item.split('\u3000', 1); official_dict[code.strip()] = name.strip()
        except: continue
    return official_dict

def load_config():
    w, n = [], {}
    if os.path.exists(W_FILE):
        with open(W_FILE, "r", encoding="utf-8") as f: w = [l.strip() for l in f.readlines() if l.strip()]
    if os.path.exists(N_FILE):
        try:
            with open(N_FILE, "r", encoding="utf-8") as f: n = json.load(f)
        except: n = {}
    return w, n

def save_config(w, n):
    with open(W_FILE, "w", encoding="utf-8") as f: [f.write(f"{i}\n") for i in w]
    with open(N_FILE, "w", encoding="utf-8") as f: json.dump(n, f, ensure_ascii=False)

@st.cache_data(ttl=3600)
def fetch_stock_full_info(symbol):
    for ext in [".TW", ".TWO"]:
        try:
            t = yf.Ticker(f"{symbol}{ext}"); df = t.history(period="1y")
            if not df.empty: return {"df": df, "info": t.info, "name": t.info.get('longName', '')}
        except: continue
    return None

@st.cache_data(ttl=5, show_spinner=False)
def get_realtime_multi(symbols):
    try:
        url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
        headers = {"User-Agent": "Mozilla/5.0"}
        ex_ch = "|".join([f"tse_{s}.tw" for s in symbols])
        res = requests.get(url, params={"ex_ch": ex_ch, "json": "1", "delay": "0"}, headers=headers, timeout=3)
        data = res.json()
        result = {}
        for s in data.get("msgArray", []):
            code = s["c"]
            result[code] = {
                "price": float(s.get("z") or 0),
                "open": float(s.get("o") or 0),
                "vol": float(s.get("v") or 0)
            }
        return result
    except: return {}

def ai_signal(price, ma5, rsi, vol, vol_ma):
    score = 0
    if rsi < 30: score += 2
    elif rsi < 40: score += 1
    if price > ma5: score += 1
    if vol > vol_ma * 1.5: score += 2
    if score >= 4: return "🚀 強力買進", "高勝率"
    elif score >= 2: return "📈 可觀察", "中勝率"
    else: return "⚠️ 觀望", "低勝率"

def detect_volume(vol, vol_ma):
    if vol > vol_ma * 2: return "🔥 爆量"
    elif vol > vol_ma * 1.5: return "⚡ 放量"
    return ""

def trigger_search(symbol):
    st.session_state.search_target = symbol
    st.session_state.app_mode = "個股深度分析"

# --- 5. 狀態初始化 ---
if 'initialized' not in st.session_state:
    startup_holder = st.empty()
    with startup_holder.container():
        st.markdown("""<div class="startup-overlay"><div class="startup-box"><div class="startup-rocket">🚀</div><div class="startup-text">AI火星帶你進入股票世界</div></div></div>""", unsafe_allow_html=True)
        st.session_state.official_db = get_official_taiwan_names()
        st.session_state.watchlist, st.session_state.names_map = load_config()
        st.session_state.search_target = st.session_state.watchlist[0] if st.session_state.watchlist else None
        st.session_state.initialized = True
        st.session_state.app_mode = "個股深度分析"
        time.sleep(1.2)
    startup_holder.empty()
    st.rerun()

# --- 6. 側邊欄與導覽 ---
st.sidebar.markdown('### 🧭 系統導覽')
st.session_state.app_mode = st.sidebar.radio("切換功能頁面", ["個股深度分析", "🚀 多股票監控模組"])

st.sidebar.markdown('---')
st.sidebar.markdown('### 🖥️ 監控中心')
if st.session_state.watchlist:
    try: s_idx = st.session_state.watchlist.index(st.session_state.search_target)
    except: s_idx = 0
    selected = st.sidebar.selectbox("🔄 快速切換標的", st.session_state.watchlist, index=s_idx, key="selector_box",
        format_func=lambda x: f"{x} {st.session_state.names_map.get(x, st.session_state.official_db.get(x, ''))}")
    if selected != st.session_state.search_target:
        st.session_state.search_target = selected
        st.session_state.app_mode = "個股深度分析"
        st.rerun()

with st.sidebar.form(key="add_stock_sidebar_form", clear_on_submit=True):
    a_code = st.text_input("➕ 新增代號", placeholder="如 2603")
    if st.form_submit_button("確認加入", use_container_width=True):
        if a_code and a_code not in st.session_state.watchlist:
            st.session_state.watchlist.append(a_code)
            save_config(st.session_state.watchlist, st.session_state.names_map)
            st.rerun()

if st.session_state.watchlist:
    with st.sidebar.expander("🛠️ 名單編輯"):
        for i, c in enumerate(st.session_state.watchlist):
            cols = st.columns([1.5, 0.8, 0.8, 0.8])
            with cols[0]:
                st.button(f"🔍{c}", key=f"src_btn_{c}", on_click=trigger_search, args=(c,))
            with cols[1]:
                if st.button("🔼", key=f"up_{c}") and i > 0:
                    st.session_state.watchlist[i], st.session_state.watchlist[i-1] = st.session_state.watchlist[i-1], st.session_state.watchlist[i]
                    save_config(st.session_state.watchlist, st.session_state.names_map)
                    st.rerun()
            with cols[2]:
                if st.button("🔽", key=f"dn_{c}") and i < len(st.session_state.watchlist)-1:
                    st.session_state.watchlist[i], st.session_state.watchlist[i+1] = st.session_state.watchlist[i+1], st.session_state.watchlist[i]
                    save_config(st.session_state.watchlist, st.session_state.names_map)
                    st.rerun()
            with cols[3]:
                if st.button("❌", key=f"del_{c}"):
                    st.session_state.watchlist.remove(c)
                    save_config(st.session_state.watchlist, st.session_state.names_map)
                    st.rerun()
            
            cur_n = st.session_state.names_map.get(c, st.session_state.official_db.get(c, ""))
            new_n = st.text_input(f"n_{c}", value=cur_n, key=f"edit_input_{c}", label_visibility="collapsed")
            if new_n != cur_n:
                st.session_state.names_map[c] = new_n
                save_config(st.session_state.watchlist, st.session_state.names_map)
            st.markdown('<hr style="margin:3px 0; border:0.5px solid #eee;">', unsafe_allow_html=True)

st.sidebar.write("---")
fc1, fc2 = st.sidebar.columns(2)
with fc1:
    if st.button("⚠️ 清空名單", use_container_width=True):
        if os.path.exists(W_FILE): os.remove(W_FILE)
        if os.path.exists(N_FILE): os.remove(N_FILE)
        st.session_state.watchlist = []
        st.session_state.names_map = {}
        st.session_state.search_target = None
        st.sidebar.success("名單已清空")
        st.rerun()
with fc2:
    if st.button("💾 儲存設定", use_container_width=True):
        save_config(st.session_state.watchlist, st.session_state.names_map)
        st.sidebar.success("設定已存檔")

# --- 7. 主頁面內容分流 ---
if st.session_state.app_mode == "個股深度分析":
    st.markdown('<p class="ultra-huge-title">台股 AI 專業分析系統</p>', unsafe_allow_html=True)
    with st.form(key="main_search_form"):
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            m_input = st.text_input("輸入股票代碼", placeholder="例如: 2330", key="main_search_input", label_visibility="collapsed").strip()
        with c2:
            lookback = st.selectbox("查找範圍", ["3個月", "6個月", "1年"], index=1, label_visibility="collapsed")
            lookback_map = {"3個月": 60, "6個月": 120, "1年": 250}
            st.session_state.period_days = lookback_map[lookback]
        with c3:
            if st.form_submit_button("🚀 執行 AI 分析", use_container_width=True):
                if m_input:
                    st.session_state.search_target = m_input
                    st.rerun()

    if st.session_state.get('search_target'):
        symbol = st.session_state.search_target
        data = fetch_stock_full_info(symbol)
        if not data:
            st.error(f"❌ 找不到 {symbol}")
        else:
            df, info = data['df'] if 'df' in data else None, data['info'] if 'info' in data else None
            if df is not None:
                # --- 取代 pandas_ta 的手動計算部分 ---
                df['MA5'] = df['Close'].rolling(window=5).mean()
                df['MA20'] = df['Close'].rolling(window=20).mean()
                # 手寫 RSI 公式
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                f_name = st.session_state.names_map.get(symbol, st.session_state.official_db.get(symbol, data['name']))
                
                st.markdown(f'<div class="analysis-banner"><h2>📊 分析標的：{symbol} {f_name}</h2></div>', unsafe_allow_html=True)
                tab1, tab2 = st.tabs(["💎 核心數據", "📈 技術圖表"])
                
                with tab1:
                    SECTOR_MAP = {"Technology": "資訊科技/半導體", "Financial Services": "金融服務", "Consumer Cyclical": "消費性電子/週期性消費", "Communication Services": "通訊服務", "Industrials": "工業/航運/傳產", "Consumer Defensive": "民生必需品", "Healthcare": "醫療保健", "Real Estate": "房地產/營建", "Utilities": "公用事業", "Basic Materials": "基礎材料/塑化/鋼鐵", "Energy": "能源"}
                    s_cn = SECTOR_MAP.get(info.get('sector', ''), info.get('sector', '未知'))
                    sm_cn = translate_to_chinese(info.get('longBusinessSummary', '暫無資料'))
                    st.markdown(f"""<div class="info-container"><p><b>📖 產業類別：</b> <span class="sector-tag">{s_cn}</span></p><div class="summary-text"><b>📄 業務摘要：</b><br>{sm_cn}</div></div>""", unsafe_allow_html=True)
                    fc1, fc2, fc3, fc4 = st.columns(4)
                    fc1.metric("EPS", f"{info.get('trailingEps', 'N/A')}")
                    fc2.metric("P/E (本益比)", f"{info.get('trailingPE', 'N/A'):.2f}" if isinstance(info.get('trailingPE'), (float, int)) else "N/A")
                    fc3.metric("P/B (股淨比)", f"{info.get('priceToBook', 'N/A'):.2f}" if isinstance(info.get('priceToBook'), (float, int)) else "N/A")
                    dv = info.get('dividendYield', 0)
                    fc4.metric("殖利率", f"{dv*100:.2f}%" if dv else "0.00%")

                with tab2:
                    l = df.iloc[-1]
                    m5, rsi = float(l['MA5']), float(l['RSI'])
                    adv = "⚖️ 持平" if 40 <= rsi <= 60 else "🚀 強勢買進" if rsi < 30 else "📉 建議賣出" if rsi > 70 else "📈 超跌買進"
                    st.markdown(f"""<div class="core-data-container"><div class="core-data-grid"><div class="data-item"><div class="data-label">當前股價</div><div class="data-value">{float(l['Close']):.2f}</div></div><div class="data-item"><div class="data-label">MA5 均線</div><div class="data-value">{m5:.2f}</div></div><div class="data-item"><div class="data-label">RSI 指標</div><div class="data-value">{rsi:.1f}</div></div><div class="data-item"><div class="data-label">AI 建議</div><div class="data-value" style="color:#4facfe;">{adv}</div></div></div></div>""", unsafe_allow_html=True)
                    st.markdown(f"### 📈 技術繪圖 ({lookback if 'lookback' in locals() else '6個月'})")
                    days = st.session_state.get('period_days', 120)
                    st.line_chart(df[['Close', 'MA5', 'MA20']].tail(days))

else:
    st.markdown('<p class="ultra-huge-title">🚀 即時多股票監控中心</p>', unsafe_allow_html=True)
    
    default_watchlist = ",".join(st.session_state.watchlist) if st.session_state.watchlist else "2330,2317"
    
    col_input, col_save = st.columns([4, 1])
    with col_input:
        watch_symbols_str = st.text_input("監控股票", default_watchlist, key="monitor_input_page", label_visibility="collapsed")
    with col_save:
        if st.button("💾 儲存監控清單", use_container_width=True):
            new_list = [s.strip() for s in watch_symbols_str.split(",") if s.strip()]
            st.session_state.watchlist = new_list
            save_config(st.session_state.watchlist, st.session_state.names_map)
            st.success("清單已儲存！")
            st.rerun()

    symbols = [s.strip() for s in watch_symbols_str.split(",") if s.strip()]
    
    if symbols:
        with st.spinner("正在獲取即時數據與 AI 診斷..."):
            rt_data = get_realtime_multi(symbols)
            rows = []
            for s in symbols:
                data = fetch_stock_full_info(s)
                if not data: continue

                df = data["df"]
                # --- 取代 pandas_ta 的手動計算部分 ---
                df['MA5'] = df['Close'].rolling(window=5).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                last = df.iloc[-1]

                ma5 = last['MA5']
                rsi = last['RSI']
                vol_ma = df['Volume'].rolling(5).mean().iloc[-1]

                rt = rt_data.get(s, {})
                price = rt.get("price", last['Close'])
                vol = rt.get("vol", last['Volume'])

                signal, winrate = ai_signal(price, ma5, rsi, vol, vol_ma)
                vol_tag = detect_volume(vol, vol_ma)

                rows.append({
                    "代碼": s,
                    "名稱": st.session_state.names_map.get(s, st.session_state.official_db.get(s, "")),
                    "即時價": round(price, 2),
                    "RSI": round(rsi, 1),
                    "成交量狀態": vol_tag,
                    "AI建議": signal,
                    "勝率預估": winrate
                })
            
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# --- 頁尾 (完全保留) ---
st.markdown("""
<div class="disclaimer-box">⚠️ <b>投資警語：</b>本系統所提供之所有資訊、數據及分析結果僅供參考，不構成任何形式之投資建議、合約或承諾。市場有風險，投資需謹慎。使用者應獨立評估風險，並對其投資行為結果自行負。</div>
<div class="footer-container">
    <p class="footer-line">🖥️鄧小智製作 | 感謝您的使用🖥️</p>
    <p class="footer-line">💰謹慎投資保護您的錢錢以免不見💰</p>
    <p class="footer-line">⚠️投資一定有風險，理財投資有賺有賠！⚠️</p>
</div>
""", unsafe_allow_html=True)
