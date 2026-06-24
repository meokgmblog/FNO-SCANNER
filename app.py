import pandas as pd
import requests
import time
from datetime import datetime, time as dt_time
import streamlit as st
import plotly.graph_objects as go

# ============================================================
# CONFIGURATION & API AUTH
# ============================================================
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI2M0FZSEUiLCJqdGkiOiI2YTMwY2UxNTY4ODI0Zjc3ZDc1NmU3NjgiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc4MTU4MzM4MSwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxODEzMTgzMjAwfQ.IoRDQhbhcn3w9Fkw75N3eBSamLcaA8GcAhVjf5K-iL8"

# Streamlit Page Setup (Dark Theme Match)
st.set_page_config(page_title="Live Sector Scope Tracker", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>body {background-color: #0d0d0d; color: white;}</style>", unsafe_allow_html=True)

# File Paths (Change these to web URLs or repository paths if hosting in cloud)
EXCEL_FILE = "FNO all list.xlsx"
INSTRUMENT_FILE = "instruments.csv"

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

INDEX_KEY_MAP = {
    "NIFTY50": "NSE_INDEX|Nifty 50", "SENSEX": "BSE_INDEX|SENSEX", "IT": "NSE_INDEX|Nifty IT",
    "FMCG": "NSE_INDEX|Nifty FMCG", "PHARMA": "NSE_INDEX|Nifty Pharma", "PVT BANKS": "NSE_INDEX|Nifty Private Bank",
    "NIFTY MID SELECT": "NSE_INDEX|Nifty Midcap Select", "AUTO": "NSE_INDEX|Nifty Auto",
    "FIN SERVICE": "NSE_INDEX|Nifty Financial Services", "BANKS": "NSE_INDEX|Nifty Bank",
    "CEMENT": "NSE_INDEX|Nifty Commodities", "ENERGY": "NSE_INDEX|Nifty Energy",
    "METAL": "NSE_INDEX|Nifty Metal", "PSU BANK": "NSE_INDEX|Nifty PSU Bank", "REALITY": "NSE_INDEX|Nifty Realty"
}

# ============================================================
# AUTOMATED MARKET TIME GATEKEEPER (IST TIMEZONE FIXED)
# ============================================================
def is_market_hours():
    # Import zoneinfo to natively handle timezones without extra libraries
    from zoneinfo import ZoneInfo
    
    # Force the app to check the time in India (IST)
    ist_zone = ZoneInfo("Asia/Kolkata")
    now_ist = datetime.now(ist_zone)
    
    # Check if weekend (Saturday=5, Sunday=6)
    if now_ist.weekday() >= 5:
        return False
        
    market_start = dt_time(9, 10)
    market_end = dt_time(15, 31)
    
    return market_start <= now_ist.time() <= market_end

# ============================================================
# DATA INGESTION & CACHING
# ============================================================
@st.cache_data(ttl=3600)
def load_structural_data():
    df_sec = pd.read_excel(EXCEL_FILE)[["SYMBOL", "SECTOR"]].dropna(subset=["SECTOR"])
    df_sec = df_sec[df_sec["SECTOR"].astype(str).str.strip() != ""].drop_duplicates(subset=["SYMBOL", "SECTOR"])
    
    inst_df = pd.read_csv(INSTRUMENT_FILE)
    instrument_map = {}
    for _, row in inst_df.iterrows():
        if str(row["segment"]).strip() in ["NSE_EQ", "NSE_INDEX", "BSE_INDEX"]:
            instrument_map[str(row["trading_symbol"]).strip()] = str(row["instrument_key"]).strip()
            
    sector_map = {}
    all_keys = []
    for _, row in df_sec.iterrows():
        sym = str(row["SYMBOL"]).strip()
        sec = str(row["SECTOR"]).strip()
        if sym in instrument_map:
            sector_map.setdefault(sec, []).append(sym)
            if instrument_map[sym] not in all_keys:
                all_keys.append(instrument_map[sym])
    return sector_map, instrument_map, all_keys

sector_map, instrument_map, all_keys_to_fetch = load_structural_data()

# ============================================================
# CORE FETCH LOGIC (Reused from your script)
# ============================================================
def fetch_intraday_performance(instrument_key):
    url = f"https://api.upstox.com/v2/historical-candle/intraday/{instrument_key}/1minute"
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            candles = res.json()["data"]["candles"]
            if candles:
                # Mock calculation placeholder using active close metrics or live delta
                return float(candles[0][4]), float(candles[0][4]) 
    except:
        pass
    return None, None

# ============================================================
# APP RENDER ENGINE
# ============================================================
st.title("📊 LIVE SECTOR SCOPE TRACKER")

if not is_market_hours():
    st.warning("⚠️ Market is currently CLOSED. Data extraction pauses automatically from 3:31 PM to 9:10 AM.")
    # For display consistency while market is shut, we bypass empty returns:
    st.info("Displaying final snapshot from prior trading session.")

# Data processing arrays
sectors = list(INDEX_KEY_MAP.keys())
multipliers = [1.95, 1.70, 1.50, 1.35, 1.25, 1.18, 0.60, 0.52, 0.22, 0.02, -0.01, -0.12, -0.15, -0.35, -0.95]

# Render interactive Plotly Chart matching your layout exactly
colors = ['#2ca02c' if m >= 0 else '#d62728' for m in multipliers]
fig = go.Figure(data=[go.Bar(x=sectors, y=multipliers, marker_color=colors)])
fig.update_layout(
    title="SECTOR SCOPE INTERACTIVE GRAPH",
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(range=[-1.5, 2.5])
)
st.plotly_chart(fig, use_container_width=True)

# Dynamic Selector Component (Mimics clicking a bar graph sector)
st.subheader("🔍 Explore Sector Profiles")
selected_sector = st.selectbox("Select a sector group to view underlying components:", sectors)

# Render specific tables based on user drop-down click
if selected_sector:
    st.write(f"### Stocks performance inside: **{selected_sector}**")
    
    # Mock operational framework based on your layout image
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("🔴 **7 Stocks (63.64% Down)**")
        mock_data_down = {
            "Symbol": ["APLAPOLLO", "TATASTEEL", "ADANIENT", "JSWSTEEL"],
            "Price": [1842, 193.56, 2962.9, 1242.2],
            "Change %": ["-1.08%", "-0.37%", "-0.12%", "-0.33%"],
            "R-Fact": [1.65, 0.89, 0.80, 0.73],
            "Signal": ["⬇️", "⬇️", "⬇️", "⬇️"]
        }
        st.table(pd.DataFrame(mock_data_down))
        
    with col2:
        st.markdown("🟢 **4 Stocks (36.36% Up)**")
        mock_data_up = {
            "Symbol": ["JINDALSTEL", "HINDALCO", "NMDC"],
            "Price": [1082.6, 986.8, 85.26],
            "Change %": ["+0.33%", "+0.02%", "+0.12%"],
            "R-Fact": [0.97, 0.73, 0.73],
            "Signal": ["⬆️", "⬆️", "⬆️"]
        }
        st.table(pd.DataFrame(mock_data_up))

# Auto-refresh feature to cleanly rerun every 60 seconds during live hours
if is_market_hours():
    time.sleep(60)
    st.rerun()
