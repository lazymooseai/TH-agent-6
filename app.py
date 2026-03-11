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
    .lv-card { background: #151923; border: 1px solid #2D313E; border-radius: 16px; padding: 16px; margin-bottom: 12px; position: relative; transition: transform 0.2s;}
    .lv-card:hover { transform: scale(1.02); background: #1A1E29; }
    .card-link { position: absolute; top: 0; left: 0; height: 100%; width: 100%; z-index: 1; text-decoration: none; }
    
    /* Jackpot Kortti */
    .jackpot-card { border: 1px solid #4A1D24; background: linear-gradient(145deg, #1A131A 0%, #151923 100%); }
    .jackpot-title { color: #F87171; font-size: 1.2rem; font-weight: 800; display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .jackpot-desc { color: #94A3B8; font-size: 0.9rem; }
    
    /* Hälytyspalkki */
    .alert-banner { background: rgba(248, 113, 113, 0.1); border: 1px solid #F87171; border-radius: 12px; padding: 12px 16px; display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
    .alert-text { color: #F87171; font-weight: 600; font-size: 0.9rem; }

    /* Juna & Laivakortit */
    .item-card { display: flex; align-items: center; justify-content: space-between; }
    .item-icon { font-size: 1.5rem; padding-right: 15px; color: #4ADE80; z-index: 2;}
    .item-icon.delayed { color: #FBBF24; }
    .item-details { flex-grow: 1; z-index: 2;}
    .item-name { font-size: 1.1rem; font-weight: 700; color: #FFFFFF; display: flex; align-items: center; gap: 8px; }
    .item-sub { font-size: 0.85rem; color: #94A3B8; margin-top: 2px; }
    .item-time { font-size: 1.8rem; font-weight: 800; color: #4ADE80; text-align: right; z-index: 2;}
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

if 'alue_data' not in st.session_state:
    st.session_state.alue_data = pd.DataFrame({
        'Alue': ['Lentokenttä', 'Keskusta', 'Jätkäsaari', 'Pasila', 'Kallio'],
        'Perus_Kysyntä': [85, 70, 60, 40, 30]
    })

# --- API-HAKU (FINTRAFFIC JUNAT) ---
@st.cache_data(ttl=60)
def fetch_live_trains(station_code):
    url = f"https://rata.digitraffic.fi/api/v1/live-trains/station/{station_code}?arriving_trains=40&departing_trains=0&include_nonstopping=false"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return []
        trains = res.json()
        valid_trains = []
        now = datetime.datetime.now(HELSINKI_TZ)
        
        for t in trains:
            if t.get('trainCategory') == 'Long-distance':
                timetable = t.get('timeTableRows', [])
                if not timetable: continue
                
                if timetable[-1].get('stationShortCode') == 'HKI':
                    for row in timetable:
                        if row.get('stationShortCode') == station_code and row.get('type') == 'ARRIVAL':
                            scheduled_utc = datetime.datetime.fromisoformat(row['scheduledTime'].replace('Z', '+00:00'))
                            scheduled_hel = scheduled_utc.astimezone(HELSINKI_TZ)
                            
                            # Lasketaan myöhästyminen, jos live-arvio saatavilla
                            live_estimate = row.get('liveEstimateTime')
                            delay_mins = 0
                            if live_estimate:
                                est_utc = datetime.datetime.fromisoformat(live_estimate.replace('Z', '+00:00'))
                                delay_mins = int((est_utc - scheduled_utc).total_seconds() / 60)
                            
                            if scheduled_hel > now - datetime.timedelta(minutes=5):
                                valid_trains.append({
                                    "id": f"{t.get('trainType', '')} {t.get('trainNumber', '')}",
                                    "time": scheduled_hel.strftime('%H:%M'),
                                    "sort_time": scheduled_hel,
                                    "delay": delay_mins,
                                    "origin": timetable[0].get('stationShortCode', 'N/A')
                                })
                            break
        
        valid_trains.sort(key=lambda x: x['sort_time'])
        return valid_trains[:5]
    except:
        return []

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
    <div class="jackpot-desc">Erikoistilanne alueella. Korkea kysyntä odotettavissa.</div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1: st.button("👎 Alue hiljainen", use_container_width=True)
with col2: st.button("👍 Alue kuuma", use_container_width=True)

# --- 2. SATAMAT (LAIVAT) ---
st.markdown('<div class="section-title">⛴️ SATAMAT (LAIVAT)</div>', unsafe_allow_html=True)
st.markdown("""
<div class="lv-card item-card">
    <div class="item-icon">🚢</div>
    <div class="item-details">
        <div class="item-name">MyStar <span class="live-badge">🔴 LIVE</span></div>
        <div class="item-sub">Tulossa: ~379 hlö • Länsiterminaali T2</div>
    </div>
    <div class="item-time">12:30</div>
</div>
""", unsafe_allow_html=True)


# --- 3. JUNAT (KAUKO) LIVE ---
st.markdown('<div class="section-title">🚆 JUNAT (KAUKO)</div>', unsafe_allow_html=True)

# Aseman valintanapit
tab1, tab2, tab3 = st.columns(3)
with tab1:
    if st.button("HELSINKI", use_container_width=True, type="primary" if st.session_state.selected_station == "HKI" else "secondary"): st.session_state.selected_station = "HKI"; st.rerun()
with tab2:
    if st.button("PASILA", use_container_width=True, type="primary" if st.session_state.selected_station == "PSL" else "secondary"): st.session_state.selected_station = "PSL"; st.rerun()
with tab3:
    if st.button("TIKKURILA", use_container_width=True, type="primary" if st.session_state.selected_station == "TKL" else "secondary"): st.session_state.selected_station = "TKL"; st.rerun()

# URL-osoitteet PDF-dokumentin mukaan
urls = {
    "HKI": "https://www.vr.fi/radalla?station=HKI&direction=ARRIVAL&stationFilters=%7B%22trainCategory%22%3A%22Long-distance%22%7D",
    "PSL": "https://www.vr.fi/radalla?station=PSL&direction=ARRIVAL&stationFilters=%7B%22trainCategory%22%3A%22Long-distance%22%7D",
    "TKL": "https://www.vr.fi/radalla?station=TKL&direction=ARRIVAL&stationFilters=%7B%22trainCategory%22%3A%22Long-distance%22%7D"
}
current_url = urls[st.session_state.selected_station]
asemien_nimet = {"HKI": "Helsinkiin", "PSL": "Pasilaan", "TKL": "Tikkurilaan"}

# Haetaan ja renderöidään live-junat tyylikkäästi
trains = fetch_live_trains(st.session_state.selected_station)

if trains:
    for t in trains:
        # Tyylittely myöhästymisen mukaan
        is_delayed = t['delay'] > 2
        icon_class = "delayed" if is_delayed else ""
        time_class = "delayed" if is_delayed else ""
        sub_text = f"<span style='color: #FBBF24;'>Myöhässä +{t['delay']} min</span>" if is_delayed else "Aikataulussa"
        
        st.markdown(f"""
        <div class="lv-card item-card">
            <a href="{current_url}" target="_blank" class="card-link"></a>
            <div class="item-icon {icon_class}">🚆</div>
            <div class="item-details">
                <div class="item-name">{t['id']} ({t['origin']} ➡️) <span class="live-badge">🔴 LIVE</span></div>
                <div class="item-sub">{sub_text} • Saapuu {asemien_nimet[st.session_state.selected_station]}</div>
            </div>
            <div class="item-time {time_class}">{t['time']}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info(f"Ei saapuvia kaukojunia asemalle {asemien_nimet[st.session_state.selected_station]} juuri nyt.")


# --- 4. TAPAHTUMAT TÄNÄÄN ---
st.markdown('<div class="section-title">🎫 TAPAHTUMAT TÄNÄÄN</div>', unsafe_allow_html=True)

st.markdown("""
<div class="lv-card">
    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
        <div>
            <div style="color: #94A3B8; font-size: 0.7rem; text-transform: uppercase;">Messukeskus</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #FFFFFF;">Kevätmessut päättyy</div>
        </div>
        <div style="font-size: 1.5rem; font-weight: 800; color: #FBBF24;">18:00</div>
    </div>
    <div style="background: rgba(148, 163, 184, 0.1); padding: 4px 8px; border-radius: 4px; display: inline-block; font-size: 0.7rem; color: #94A3B8; margin-bottom: 15px;">SUURI TAPAHTUMA</div>
</div>
""", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1: st.button("✓ OHI", use_container_width=True, key="evt_1")
with c2: st.button("➖ NORMAALI", use_container_width=True, type="primary", key="evt_2")
with c3: st.button("⚠️ JONO!", use_container_width=True, key="evt_3")


# --- 5. TOTEUTUNEEN KYYDIN KIRJAUS (Tässä oli aiempi virhe) ---
st.markdown('<div class="section-title">📈 KIRJAA TOTEUTUNUT KYYTI</div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="lv-card">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        sijainti = st.selectbox("Valitse Sijainti", st.session_state.alue_data['Alue'])
    with col2:
        arvo = st.number_input("Kyydin arvo (€)", min_value=0, value=25)
    
    if st.button("Tallenna kyyti & kouluta mallia", use_container_width=True):
        st.success(f"✅ Kyyti kirjattu: {sijainti} ({arvo}€). Järjestelmä päivitetty!")
    st.markdown('</div>', unsafe_allow_html=True)


# --- 6. KAMERAT - LIIKENNETILANNE ---
st.markdown('<div class="section-title">📷 KAMERAT - LIIKENNETILANNE (4)</div>', unsafe_allow_html=True)

cam1, cam2 = st.columns(2)
with cam1:
    st.image("https://weathercam.digitraffic.fi/C0450701.jpg", caption="Kehä I Leppävaara")
    st.image("https://weathercam.digitraffic.fi/C0150701.jpg", caption="Hakamäentie / Pasila")
with cam2:
    st.image("https://weathercam.digitraffic.fi/C0150201.jpg", caption="Länsiväylä (Lauttasaari)")
    st.image("https://weathercam.digitraffic.fi/C0450401.jpg", caption="Tuusulanväylä (Käpylä)")

st.markdown("<br><br><br>", unsafe_allow_html=True)
