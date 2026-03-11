import streamlit as st
import datetime
import pandas as pd
import pytz
import requests
from bs4 import BeautifulSoup
import random
import time

# --- KONFIGURAATIO ---
st.set_page_config(page_title="TH Tuottavuusagentti", page_icon="🚕", layout="centered", initial_sidebar_state="collapsed")
HELSINKI_TZ = pytz.timezone('Europe/Helsinki')

# --- CSS INJEKTIO (TH5 Tyylit) ---
st.markdown("""
<style>
    .stApp { background-color: #0F111A; color: #E2E8F0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .time-display { font-size: 2.5rem; font-weight: 800; color: #FFFFFF; letter-spacing: -1px; }
    .time-display span { color: #4ADE80; }
    .weather-widget { background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 8px; text-align: right; }
    .weather-temp { font-size: 1.2rem; font-weight: 700; color: #FFFFFF; }
    .weather-desc { font-size: 0.7rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px;}
    .th-card { background: #191B24; border: 1px solid #2D313E; border-radius: 12px; padding: 16px; margin-bottom: 12px; position: relative; }
    .th-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: #4ADE80; border-radius: 12px 0 0 12px; }
    .card-title { font-size: 1.1rem; font-weight: 700; color: #FFFFFF; margin-bottom: 2px; z-index: 2; position: relative;}
    .card-subtitle { font-size: 0.85rem; color: #94A3B8; margin-bottom: 8px; z-index: 2; position: relative;}
    .card-time { position: absolute; right: 16px; top: 16px; font-size: 1.8rem; font-weight: 800; color: #4ADE80; letter-spacing: -1px; z-index: 2;}
    .section-title { font-size: 0.85rem; font-weight: 800; color: #94A3B8; text-transform: uppercase; margin: 24px 0 12px 0; letter-spacing: 1px;}
</style>
""", unsafe_allow_html=True)

# --- TILANHALLINTA (Session State) ---
# Yhdistetty TH Agentin alue-data ja TH5:n tapahtumatilat
if 'alue_data' not in st.session_state:
    st.session_state.alue_data = pd.DataFrame({
        'Alue': ['Keskusta', 'Pasila', 'Jätkäsaari', 'Kallio', 'Lentokenttä'],
        'Perus_Kysyntä': [70, 40, 60, 30, 85],
        'Kuljettajan_Kerroin': [1.0, 1.0, 1.0, 1.0, 1.0],
        'Kommentti': ['', '', 'Kevätmessut päättyy klo 18', '', 'Aasian lennot saapuneet']
    })

if 'event_states' not in st.session_state:
    st.session_state.event_states = {"Messukeskus": "NORMAALI", "Jäähalli": "NORMAALI"}

def update_event_status(event_name, new_status):
    st.session_state.event_states[event_name] = new_status

# --- AGENTIT (Tiedonhaku) ---
@st.cache_data(ttl=60)
def fetch_live_trains():
    # Yksinkertaistettu juna-agentti HKI asemalle esimerkkinä
    url = "https://rata.digitraffic.fi/api/v1/live-trains/station/HKI?arriving_trains=5&departing_trains=0"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json()
    except:
        return []
    return []

# --- KÄYTTÖLIITTYMÄ ---

# 1. Yläpalkki
now = datetime.datetime.now(HELSINKI_TZ)
time_str = now.strftime("%H") + "<span>:</span>" + now.strftime("%M")
st.markdown(f"""
<div class="top-bar">
    <div class="time-display">{time_str}</div>
    <div class="weather-widget">
        <div class="weather-temp">🌦️ +5°</div>
        <div class="weather-desc">SADE ALKAMASSA</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.title("🚖 TH Tuottavuusagentti")

# 2. Kuljettajien yhteistyö (Kuumimmat alueet)
st.markdown('<div class="section-title">📍 ALUEIDEN KYSYNTÄ & PARVIÄLY</div>', unsafe_allow_html=True)
st.session_state.alue_data['Lopullinen_Kysyntä'] = (st.session_state.alue_data['Perus_Kysyntä'] * st.session_state.alue_data['Kuljettajan_Kerroin']).clip(0, 100)

for index, row in st.session_state.alue_data.sort_values(by='Lopullinen_Kysyntä', ascending=False).iterrows():
    with st.expander(f"{row['Alue']} - Kysyntä: {int(row['Lopullinen_Kysyntä'])}/100 | 📝 {row['Kommentti']}"):
        uusi_kerroin = st.slider(f"Säädä kerrointa ({row['Alue']})", 0.0, 3.0, float(row['Kuljettajan_Kerroin']), 0.1, key=f"slider_{index}")
        uusi_kommentti = st.text_input(f"Tilannetieto muille", value=row['Kommentti'], key=f"kommentti_{index}")
        if st.button(f"Päivitä data", key=f"btn_{index}"):
            st.session_state.alue_data.at[index, 'Kuljettajan_Kerroin'] = uusi_kerroin
            st.session_state.alue_data.at[index, 'Kommentti'] = uusi_kommentti
            st.rerun()

# 3. Live-Data (Junat esimerkkinä)
st.markdown('<div class="section-title">🚆 LIVE: SAAPUVAT JUNAT (HKI)</div>', unsafe_allow_html=True)
trains = fetch_live_trains()
if trains:
    for t in trains[:3]: # Näytetään 3 ensimmäistä
        st.markdown(f"""
        <div class="th-card">
            <div class="card-title">{t.get('trainType', '')} {t.get('trainNumber', '')}</div>
            <div class="card-subtitle">Saapuu Helsinkiin</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Ei junadataa saatavilla tällä hetkellä.")

# 4. Vision Agentti (Tekoäly)
st.markdown('<div class="section-title">📷 VISION-AGENTTI</div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Ota kuva Cabmanista tai tolpasta", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    st.image(uploaded_file, caption="Analysoidaan kuvaa...", width=300)
    with st.spinner('Tekoäly lukee arvoja kuvasta...'):
        time.sleep(2) # Simuloidaan API-kutsu
        st.success("✅ Tekoäly luki datan onnistuneesti! (Simulaatio)")
        st.info("Sijainnin Keskusta kysyntäkerrointa nostettu kuvadatan perusteella.")
