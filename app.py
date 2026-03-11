import streamlit as st
import datetime
import pandas as pd
import pytz
import requests

# --- KONFIGURAATIO ---
st.set_page_config(page_title="TH Tuottavuusagentti", page_icon="🚕", layout="centered", initial_sidebar_state="collapsed")
HELSINKI_TZ = pytz.timezone('Europe/Helsinki')

# --- CSS INJEKTIO ---
st.markdown("""
<style>
    .stApp { background-color: #0F111A; color: #E2E8F0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
    
    /* Suuremmat fontit */
    .time-display { font-size: 3.5rem; font-weight: 800; color: #FFFFFF; letter-spacing: -2px; }
    .time-display span { color: #4ADE80; }
    .weather-widget { background: rgba(255,255,255,0.05); padding: 12px 16px; border-radius: 8px; text-align: right; }
    .weather-temp { font-size: 1.5rem; font-weight: 700; color: #FFFFFF; }
    .weather-desc { font-size: 0.8rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px;}
    
    /* Korttien tyylit ja suuremmat tekstit */
    .th-card { background: #191B24; border: 1px solid #2D313E; border-radius: 12px; padding: 20px; margin-bottom: 16px; position: relative; transition: transform 0.2s; }
    .th-card:hover { transform: scale(1.02); background: #1F222E; }
    .th-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 6px; background: #4ADE80; border-radius: 12px 0 0 12px; }
    .card-title { font-size: 1.4rem; font-weight: 800; color: #FFFFFF; margin-bottom: 4px; z-index: 2; position: relative;}
    .card-subtitle { font-size: 1.0rem; color: #94A3B8; margin-bottom: 8px; z-index: 2; position: relative;}
    .card-time { position: absolute; right: 20px; top: 20px; font-size: 1.5rem; font-weight: 800; color: #4ADE80; z-index: 2;}
    .section-title { font-size: 1.0rem; font-weight: 800; color: #94A3B8; text-transform: uppercase; margin: 30px 0 15px 0; letter-spacing: 1px;}
    
    /* Koko kortin kattava linkki */
    .card-link { position: absolute; top: 0; left: 0; height: 100%; width: 100%; z-index: 1; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# --- TILANHALLINTA ---
if 'selected_station' not in st.session_state:
    st.session_state.selected_station = "HKI"

if 'alue_data' not in st.session_state:
    st.session_state.alue_data = pd.DataFrame({
        'Alue': ['Lentokenttä', 'Keskusta', 'Jätkäsaari', 'Pasila', 'Kallio'],
        'Perus_Kysyntä': [85, 70, 60, 40, 30],
        'Kuljettajan_Kerroin': [1.0, 1.0, 1.0, 1.0, 1.0],
        'Kommentti': ['Aasian lennot saapuneet', '', 'Kevätmessut päättyy klo 18', '', '']
    })

# --- API-HAKU (FINTRAFFIC) ---
@st.cache_data(ttl=60)
def fetch_live_trains(station_code):
    # Haetaan enemmän junia varmuuden vuoksi, jotta saadaan suodatettua 5 sopivaa
    url = f"https://rata.digitraffic.fi/api/v1/live-trains/station/{station_code}?arriving_trains=40&departing_trains=0&include_nonstopping=false"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return []
        trains = res.json()
        valid_trains = []
        
        now = datetime.datetime.now(HELSINKI_TZ)
        
        for t in trains:
            # Vain kaukoliikenne
            if t.get('trainCategory') == 'Long-distance':
                timetable = t.get('timeTableRows', [])
                if not timetable: continue
                
                # Tarkistetaan onko pääteasema Helsinki (HKI)
                if timetable[-1].get('stationShortCode') == 'HKI':
                    
                    # Etsitään valitun aseman saapumisaika
                    for row in timetable:
                        if row.get('stationShortCode') == station_code and row.get('type') == 'ARRIVAL':
                            scheduled_utc = datetime.datetime.fromisoformat(row['scheduledTime'].replace('Z', '+00:00'))
                            scheduled_hel = scheduled_utc.astimezone(HELSINKI_TZ)
                            
                            # Näytetään vain tulevat junat
                            if scheduled_hel > now - datetime.timedelta(minutes=5):
                                valid_trains.append({
                                    "id": f"{t.get('trainType', '')} {t.get('trainNumber', '')}",
                                    "time": scheduled_hel.strftime('%H:%M'),
                                    "sort_time": scheduled_hel
                                })
                            break
        
        # Järjestetään ajan mukaan ja otetaan 5 ensimmäistä
        valid_trains.sort(key=lambda x: x['sort_time'])
        return valid_trains[:5]
    except:
        return []

# --- KÄYTTÖLIITTYMÄ ---

# 1. Yläpalkki (Iso kello)
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

st.markdown("# 🚕 TH Tuottavuusagentti")

# 2. Alueiden kysyntä
st.markdown('<div class="section-title">📍 ALUEIDEN KYSYNTÄ & PARVIÄLY</div>', unsafe_allow_html=True)
for index, row in st.session_state.alue_data.iterrows():
    kommentti_teksti = f" | 📝 {row['Kommentti']}" if row['Kommentti'] else ""
    with st.expander(f"{row['Alue']} - Kysyntä: {int(row['Perus_Kysyntä'])}/100{kommentti_teksti}"):
        st.write("Tänne voi lisätä kertoimien säädön.")

# 3. Junat ja Asema-valikko
st.markdown('<div class="section-title">🚆 LIVE: SAAPUVAT KAUKOJUNAT</div>', unsafe_allow_html=True)

# Aseman valintanapit
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("HELSINKI", use_container_width=True, type="primary" if st.session_state.selected_station == "HKI" else "secondary"):
        st.session_state.selected_station = "HKI"
        st.rerun()
with col2:
    if st.button("PASILA", use_container_width=True, type="primary" if st.session_state.selected_station == "PSL" else "secondary"):
        st.session_state.selected_station = "PSL"
        st.rerun()
with col3:
    if st.button("TIKKURILA", use_container_width=True, type="primary" if st.session_state.selected_station == "TKL" else "secondary"):
        st.session_state.selected_station = "TKL"
        st.rerun()

# URL-osoitteet PDF-dokumentin mukaan
urls = {
    "HKI": "https://www.vr.fi/radalla?station=HKI&direction=ARRIVAL&stationFilters=%7B%22trainCategory%22%3A%22Long-distance%22%7D",
    "PSL": "https://www.vr.fi/radalla?station=PSL&direction=ARRIVAL&stationFilters=%7B%22trainCategory%22%3A%22Long-distance%22%7D",
    "TKL": "https://www.vr.fi/radalla?station=TKL&direction=ARRIVAL&stationFilters=%7B%22trainCategory%22%3A%22Long-distance%22%7D"
}
current_url = urls[st.session_state.selected_station]
asemien_nimet = {"HKI": "Helsinkiin", "PSL": "Pasilaan", "TKL": "Tikkurilaan"}

# Junien renderöinti
trains = fetch_live_trains(st.session_state.selected_station)

if trains:
    for t in trains:
        st.markdown(f"""
        <div class="th-card">
            <a href="{current_url}" target="_blank" class="card-link"></a>
            <div class="card-title">{t['id']}</div>
            <div class="card-subtitle">Saapuu {asemien_nimet[st.session_state.selected_station]} (Pääteasema: HKI)</div>
            <div class="card-time">{t['time']}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info(f"Ei saapuvia kaukojunia asemalle {asemien_nimet[st.session_state.selected_station]} lähiaikoina.")

# 4. Vision Agentti
st.markdown('<div class="section-title">📷 VISION-AGENTTI</div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Ota kuva Cabmanista tai tolpasta", type=["jpg", "jpeg", "png"])
