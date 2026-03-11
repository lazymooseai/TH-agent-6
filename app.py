import streamlit as st
import datetime
import pandas as pd
import pytz
import requests

# --- KONFIGURAATIO ---
st.set_page_config(page_title="TH Tuottavuusagentti", page_icon="🚕", layout="centered", initial_sidebar_state="collapsed")
HELSINKI_TZ = pytz.timezone('Europe/Helsinki')

# --- CSS INJEKTIO (Lovable-teema) ---
st.markdown("""
<style>
    /* Tausta ja perusfontti */
    .stApp { background-color: #0B0E14; color: #E2E8F0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    
    /* Yläpalkki */
    .top-bar { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
    .clock-container { display: flex; align-items: baseline; gap: 5px; }
    .time-hours { font-size: 3.5rem; font-weight: 800; color: #FFFFFF; letter-spacing: -2px; line-height: 1; }
    .time-seconds { font-size: 1.5rem; font-weight: 600; color: #4ADE80; }
    
    .weather-widget { background: #151923; padding: 10px 15px; border-radius: 12px; text-align: right; border: 1px solid #2D313E; }
    .weather-temp { font-size: 1.3rem; font-weight: 700; color: #FFFFFF; display: flex; align-items: center; gap: 8px; }
    .weather-desc { font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px;}

    /* Yleiset korttityylit */
    .section-title { font-size: 0.85rem; font-weight: 800; color: #94A3B8; text-transform: uppercase; margin: 30px 0 10px 0; letter-spacing: 1px; display: flex; align-items: center; gap: 8px;}
    .lv-card { background: #151923; border: 1px solid #2D313E; border-radius: 16px; padding: 16px; margin-bottom: 12px; position: relative; }
    
    /* Jackpot Kortti */
    .jackpot-card { border: 1px solid #4A1D24; background: linear-gradient(145deg, #1A131A 0%, #151923 100%); }
    .jackpot-title { color: #F87171; font-size: 1.2rem; font-weight: 800; display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .jackpot-desc { color: #94A3B8; font-size: 0.9rem; }
    
    /* Hälytyspalkki */
    .alert-banner { background: rgba(248, 113, 113, 0.1); border: 1px solid #F87171; border-radius: 12px; padding: 12px 16px; display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
    .alert-text { color: #F87171; font-weight: 600; font-size: 0.9rem; }

    /* Juna & Laivakortit */
    .item-card { display: flex; align-items: center; justify-content: space-between; }
    .item-icon { font-size: 1.5rem; padding-right: 15px; color: #4ADE80; }
    .item-icon.delayed { color: #FBBF24; }
    .item-details { flex-grow: 1; }
    .item-name { font-size: 1.1rem; font-weight: 700; color: #FFFFFF; display: flex; align-items: center; gap: 8px; }
    .item-sub { font-size: 0.85rem; color: #94A3B8; margin-top: 2px; }
    .item-time { font-size: 1.8rem; font-weight: 800; color: #4ADE80; text-align: right; }
    .item-time.delayed { color: #FBBF24; }
    
    .live-badge { background: rgba(74, 222, 128, 0.15); color: #4ADE80; padding: 2px 6px; border-radius: 4px; font-size: 0.6rem; font-weight: 800; letter-spacing: 0.5px; }
    
    /* Napit */
    div[data-testid="stButton"] button { border-radius: 10px; font-weight: 600; border: 1px solid #2D313E; background-color: #151923; color: #E2E8F0; }
    div[data-testid="stButton"] button:hover { border-color: #4ADE80; color: #4ADE80; }
</style>
""", unsafe_allow_html=True)

# --- TILANHALLINTA ---
if 'selected_station' not in st.session_state:
    st.session_state.selected_station = "HKI"

# --- YLÄPALKKI (Aika ja Sää) ---
now = datetime.datetime.now(HELSINKI_TZ)
time_hm = now.strftime("%H:%M")
time_s = now.strftime("%S")

st.markdown(f"""
<div class="top-bar">
    <div class="clock-container">
        <div class="time-hours">{time_hm}</div>
        <div class="time-seconds">{time_s}</div>
    </div>
    <div class="weather-widget">
        <div class="weather-temp">☀️ +4° <span style="font-size: 0.8rem; color: #94A3B8;">🌪️ 19m/s</span></div>
        <div class="weather-desc">SADE ALKAMASSA</div>
    </div>
</div>
""", unsafe_allow_html=True)


# --- 1. JACKPOT-ALUE & HÄLYTYKSET ---
st.markdown("""
<div class="lv-card jackpot-card">
    <div class="jackpot-title">⚡ JACKPOT-ALUE: PASILA</div>
    <div class="jackpot-desc">IC 950 Turkusta myöhässä +31 min. (x1.2 sääkerroin)</div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.button("👎 Alue hiljainen", use_container_width=True)
with col2:
    st.button("👍 Alue kuuma", use_container_width=True)

st.markdown("""
<div class="alert-banner">
    <span style="font-size: 1.5rem;">⚠️</span>
    <div>
        <div class="alert-text">VR-MYÖHÄSTYMINEN — PASILA</div>
        <div style="color: #E2E8F0; font-size: 0.85rem; margin-top: 2px;">IC 950 Turkusta myöhässä +31 min. (x1.2 sääkerroin)</div>
    </div>
</div>
""", unsafe_allow_html=True)


# --- 2. SATAMAT (LAIVAT) ---
st.markdown('<div class="section-title">⛴️ SATAMAT (LAIVAT)</div>', unsafe_allow_html=True)

# Esimerkkidata laivoista (kuten videolla)
st.markdown("""
<div class="lv-card item-card">
    <div class="item-icon">🚢</div>
    <div class="item-details">
        <div class="item-name">MyStar <span class="live-badge">🔴 LIVE</span></div>
        <div class="item-sub">Tulossa: ~379 hlö • Länsiterminaali T2</div>
    </div>
    <div class="item-time">12:30</div>
</div>

<div class="lv-card item-card">
    <div class="item-icon" style="color: #94A3B8;">⛴️</div>
    <div class="item-details">
        <div class="item-name">Finlandia <span style="font-size: 0.6rem; color: #94A3B8; border: 1px solid #2D313E; padding: 2px 6px; border-radius: 4px;">AIKATAULU</span></div>
        <div class="item-sub">Max: 2080 hlö • Länsiterminaali T2</div>
    </div>
    <div class="item-time" style="color: #E2E8F0;">14:15</div>
</div>
""", unsafe_allow_html=True)


# --- 3. JUNAT (KAUKO) ---
st.markdown('<div class="section-title">🚆 JUNAT (KAUKO)</div>', unsafe_allow_html=True)

# Aseman valintanapit (Streamlitin omat)
tab1, tab2, tab3 = st.columns(3)
with tab1:
    if st.button("HELSINKI", use_container_width=True, type="primary" if st.session_state.selected_station == "HKI" else "secondary"): st.session_state.selected_station = "HKI"; st.rerun()
with tab2:
    if st.button("PASILA", use_container_width=True, type="primary" if st.session_state.selected_station == "PSL" else "secondary"): st.session_state.selected_station = "PSL"; st.rerun()
with tab3:
    if st.button("TIKKURILA", use_container_width=True, type="primary" if st.session_state.selected_station == "TKL" else "secondary"): st.session_state.selected_station = "TKL"; st.rerun()

# Mock-data videon pohjalta (tämän voi myöhemmin kytkeä takaisin Fintraffic API:in)
st.markdown("""
<div class="lv-card item-card">
    <div class="item-icon delayed">🚆</div>
    <div class="item-details">
        <div class="item-name">IC 950 Turku <span class="live-badge">🔴 LIVE</span></div>
        <div class="item-sub" style="color: #FBBF24;">Myöhässä +31 min</div>
    </div>
    <div class="item-time delayed">12:11</div>
</div>

<div class="lv-card item-card">
    <div class="item-icon">🚆</div>
    <div class="item-details">
        <div class="item-name">IC 36 Oulu <span class="live-badge">🔴 LIVE</span></div>
        <div class="item-sub">Aikataulussa</div>
    </div>
    <div class="item-time">12:44</div>
</div>
""", unsafe_allow_html=True)


# --- 4. TAPAHTUMAT TÄNÄÄN ---
st.markdown('<div class="section-title">🎫 TAPAHTUMAT TÄNÄÄN</div>', unsafe_allow_html=True)

st.markdown("""
<div class="lv-card">
    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
        <div>
            <div style="color: #94A3B8; font-size: 0.7rem; text-transform: uppercase;">Messukeskus</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #FFFFFF;">Messutapahtuma</div>
        </div>
        <div style="font-size: 1.5rem; font-weight: 800; color: #FBBF24;">10:00</div>
    </div>
    <div style="background: rgba(148, 163, 184, 0.1); padding: 4px 8px; border-radius: 4px; display: inline-block; font-size: 0.7rem; color: #94A3B8; margin-bottom: 15px;">SUURI TAPAHTUMA</div>
</div>
""", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1: st.button("✓ OHI", use_container_width=True, key="e1_1")
with c2: st.button("➖ NORMAALI", use_container_width=True, type="primary", key="e1_2")
with c3: st.button("⚠️ JONO!", use_container_width=True, key="e1_3")


# --- 5. KAMERAT - LIIKENNETILANNE ---
st.markdown('<div class="section-title">📷 KAMERAT - LIIKENNETILANNE (4)</div>', unsafe_allow_html=True)

# Fintrafficin oikeita avoimia kameralinkkejä (päivittyvät automaattisesti)
cam1, cam2 = st.columns(2)
with cam1:
    st.image("https://weathercam.digitraffic.fi/C0450701.jpg", caption="Kehä I Leppävaara")
    st.image("https://weathercam.digitraffic.fi/C0150701.jpg", caption="Hakamäentie / Pasila")
with cam2:
    st.image("https://weathercam.digitraffic.fi/C0150201.jpg", caption="Länsiväylä (Lauttasaari)")
    st.image("https://weathercam.digitraffic.fi/C0450401.jpg", caption="Tuusulanväylä (Käpylä)")

# Tyhjää tilaa pohjalle, jotta näyttää hyvältä mobiilissa
st.markdown("<br><br><br>", unsafe_allow_html=True)
