import streamlit as st
from streamlit_autorefresh import st_autorefresh
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
from datetime import datetime, timedelta
import json
import os

# ════════════════════════════════════════════════════════════════
#  PAGE CONFIG & CUSTOM CSS
# ════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Behavioural Monitor — Prototype",
    page_icon="⌚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- inject modern CSS ----------
st.markdown("""
<style>
/* ---- global ---- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ---- remove default padding ---- */
.block-container { padding-top: 2rem; padding-bottom: 0.5rem; }

/* ---- metric card ---- */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1e1e2f 0%, #2a2a40 100%);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,.25);
}
div[data-testid="stMetric"] label {
    color: #9ca3af !important;
    font-size: .82rem !important;
    letter-spacing: .03em;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-weight: 700 !important;
    font-size: 1.55rem !important;
    color: #e2e8f0 !important;
}

/* ---- section header ---- */
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #cbd5e1;
    margin: 1.2rem 0 0.6rem 0;
    letter-spacing: .02em;
}

/* ---- calm / agitated badges ---- */
.badge-calm {
    display: inline-block;
    background: linear-gradient(135deg, #059669 0%, #10b981 100%);
    color: #fff;
    font-weight: 600;
    font-size: 1.35rem;
    padding: 16px 28px;
    border-radius: 14px;
}
.badge-agitated {
    display: inline-block;
    background: linear-gradient(135deg, #dc2626 0%, #f87171 100%);
    color: #fff;
    font-weight: 600;
    font-size: 1.35rem;
    padding: 16px 28px;
    border-radius: 14px;
    animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(248,113,113,.5); }
    50% { box-shadow: 0 0 0 12px rgba(248,113,113,0); }
}

/* ---- detection alert ---- */
.detection-alert {
    background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
    color: #fff;
    padding: 12px 20px;
    border-radius: 10px;
    margin: 10px 0;
    font-weight: 500;
}
.detection-alert-warning {
    background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
    color: #fff;
    padding: 12px 20px;
    border-radius: 10px;
    margin: 10px 0;
    font-weight: 500;
}

/* ---- intervention banner ---- */
.intervention-banner {
    background: linear-gradient(90deg, #1e3a5f 0%, #2d4a6f 100%);
    border-left: 4px solid #38bdf8;
    color: #e0f2fe;
    padding: 14px 20px;
    border-radius: 0 10px 10px 0;
    margin: 12px 0;
}

/* ---- research notes ---- */
.research-note {
    background: rgba(59, 130, 246, 0.08);
    border-left: 3px solid #3b82f6;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    color: #94a3b8;
    font-size: 0.88rem;
    margin: 12px 0;
}

/* ---- CMAI section boxes ---- */
.cmai-section-box {
    background: rgba(30, 30, 47, 0.6);
    border: 1px solid rgba(255,255,255,.06);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
}
.cmai-category-header {
    font-weight: 600;
    font-size: 1.05rem;
    margin-bottom: 8px;
}
.signal-tag {
    display: inline-block;
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    font-size: 0.72rem;
    padding: 3px 8px;
    border-radius: 4px;
    margin: 2px;
    font-family: monospace;
}
.signal-tag-new {
    display: inline-block;
    background: rgba(52, 211, 153, 0.15);
    color: #34d399;
    font-size: 0.72rem;
    padding: 3px 8px;
    border-radius: 4px;
    margin: 2px;
    font-family: monospace;
}
.cmai-item-status {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 500;
}
.status-detectable { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.status-partial { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
.status-not-detectable { background: rgba(100, 116, 139, 0.2); color: #94a3b8; }

/* ---- mode indicator ---- */
.mode-live { color: #ef4444; font-weight: 600; }
.mode-offline { color: #22c55e; font-weight: 600; }

/* ---- keyword alert popup ---- */
.keyword-alert {
    background: linear-gradient(135deg, #7c3aed 0%, #4c1d95 100%);
    color: #fff;
    padding: 16px 20px;
    border-radius: 12px;
    margin: 12px 0;
    border: 2px solid #a78bfa;
    animation: glow 2s ease-in-out infinite;
}
@keyframes glow {
    0%, 100% { box-shadow: 0 0 10px rgba(167, 139, 250, 0.5); }
    50% { box-shadow: 0 0 25px rgba(167, 139, 250, 0.8); }
}
.keyword-tag {
    display: inline-block;
    background: rgba(255,255,255,0.2);
    padding: 4px 12px;
    border-radius: 20px;
    margin: 4px;
    font-weight: 600;
}
.score-badge {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 1.1rem;
}
.score-high { background: #ef4444; color: white; }
.score-medium { background: #f59e0b; color: white; }
.score-low { background: #22c55e; color: white; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  SESSION STATE INITIALIZATION
# ════════════════════════════════════════════════════════════════
if "patient_state" not in st.session_state:
    st.session_state.patient_state = "Calm"
if "cached_sensor_df" not in st.session_state:
    st.session_state.cached_sensor_df = pd.DataFrame()
if "cached_audio_df" not in st.session_state:
    st.session_state.cached_audio_df = pd.DataFrame()
if "last_fetch_time" not in st.session_state:
    st.session_state.last_fetch_time = None
if "detected_behaviours" not in st.session_state:
    st.session_state.detected_behaviours = []

# ════════════════════════════════════════════════════════════════
#  HEADER (Responsive layout)
# ════════════════════════════════════════════════════════════════
st.markdown("## ⌚ Behavioural Monitor · Prototype")

# Controls row
ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 2])
with ctrl1:
    live_mode = st.toggle("🔴 Live Mode", value=False, help="Live mode fetches data every 30s. Offline mode uses cached data.")
    if live_mode:
        st_autorefresh(interval=30000, key="refresh")  # 30 seconds to save Firebase reads
with ctrl2:
    if st.button("🔄 Refresh Now", width='stretch'):
        st.cache_data.clear()
        st.rerun()
with ctrl3:
    ist = pytz.timezone('Asia/Kolkata')
    mode_text = "<span class='mode-live'>● LIVE</span>" if live_mode else "<span class='mode-offline'>● OFFLINE</span>"
    st.markdown(f"{mode_text} &nbsp;|&nbsp; 🕒 {pd.Timestamp.now(tz=ist).strftime('%H:%M:%S  •  %d %b %Y')}", unsafe_allow_html=True)

st.markdown("---")

# ════════════════════════════════════════════════════════════════
#  FIREBASE INIT
# ════════════════════════════════════════════════════════════════
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ════════════════════════════════════════════════════════════════
#  DATA LOADING (Firebase-quota friendly)
# ════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300 if not live_mode else 30)
def load_sensor_data(_live_mode):
    """Load sensor/motion data from audio_samples (motion data) + sensor_samples (gyro data)."""
    ist = pytz.timezone("Asia/Kolkata")
    start = pd.Timestamp.now(tz=ist).normalize().tz_convert("UTC")

    limit = 200 if _live_mode else 100

    # Load motion data from audio_samples
    docs = (
        db.collection("audio_samples")
        .where("timestamp", ">=", int(start.timestamp() * 1000))
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    df = pd.DataFrame([d.to_dict() for d in docs])

    # Fallback: if no data today, grab most recent docs
    if df.empty:
        docs_fb = (
            db.collection("audio_samples")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(50)
            .stream()
        )
        df = pd.DataFrame([d.to_dict() for d in docs_fb])

    # Also load from sensor_samples to get gyro data
    gyro_docs = (
        db.collection("sensor_samples")
        .where("timestamp", ">=", int(start.timestamp() * 1000))
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    gyro_df = pd.DataFrame([d.to_dict() for d in gyro_docs])

    # Fallback for gyro data
    if gyro_df.empty:
        gyro_docs_fb = (
            db.collection("sensor_samples")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(50)
            .stream()
        )
        gyro_df = pd.DataFrame([d.to_dict() for d in gyro_docs_fb])

    if df.empty and gyro_df.empty:
        return df

    # Convert timestamps
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(ist)

        # Rename motion fields to expected names for dashboard
        if "accel_magnitude" in df.columns:
            df["accelMag"] = df["accel_magnitude"]
        if "gyro_magnitude" in df.columns:
            df["gyroMag"] = df["gyro_magnitude"]

    # Merge gyro data if available
    if not gyro_df.empty:
        gyro_df["timestamp"] = pd.to_datetime(gyro_df["timestamp"], unit="ms", utc=True).dt.tz_convert(ist)

        # Keep sensor_samples data (already correctly named: gyroX, gyroY, gyroZ, heartRate, accelMag)
        sensor_cols = ["timestamp", "gyroX", "gyroY", "gyroZ", "heartRate", "accelMag", "light"]
        sensor_cols = [c for c in sensor_cols if c in gyro_df.columns]  # Only keep columns that exist

        # Merge on timestamp (left join to keep audio_samples as primary)
        if not df.empty:
            df = pd.merge_asof(
                df.sort_values("timestamp"),
                gyro_df[sensor_cols].sort_values("timestamp"),
                on="timestamp",
                direction="nearest",
                tolerance=pd.Timedelta("1s"),
                suffixes=("_audio", "_sensor")
            )
            # Use sensor data for duplicates (sensor_samples is more reliable for motion)
            if "heartRate_sensor" in df.columns:
                df["heartRate"] = df["heartRate_sensor"]
                df = df.drop(columns=["heartRate_sensor"])
            if "accelMag_sensor" in df.columns:
                df["accelMag"] = df["accelMag_sensor"]
                df = df.drop(columns=["accelMag_sensor"])
            # Drop audio versions of motion data since we're using sensor data
            df = df.drop(columns=[c for c in ["heart_rate", "accel_magnitude"] if c in df.columns])
        else:
            # If no audio data, use sensor data as the base
            df = gyro_df[sensor_cols].copy()

    # Smooth acceleration (after merge to use sensor data)
    if not df.empty and "accelMag" in df.columns:
        df["accelMag_smooth"] = df["accelMag"].rolling(5, min_periods=1).mean()

    return df.sort_values("timestamp") if not df.empty else df

@st.cache_data(ttl=300 if not live_mode else 30)
def load_audio_data(_live_mode):
    """Load audio data with Firebase quota optimization."""
    ist = pytz.timezone("Asia/Kolkata")
    start = pd.Timestamp.now(tz=ist).normalize().tz_convert("UTC")

    limit = 100 if _live_mode else 50

    docs = (
        db.collection("audio_samples")
        .where("timestamp", ">=", int(start.timestamp() * 1000))
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    df = pd.DataFrame([d.to_dict() for d in docs])

    if df.empty:
        docs_fb = (
            db.collection("audio_samples")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(30)
            .stream()
        )
        df = pd.DataFrame([d.to_dict() for d in docs_fb])

    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(ist)
    return df.sort_values("timestamp")

@st.cache_data(ttl=60)
def load_cmai_detections(_live_mode):
    """Load keyword-based alerts from audio_samples top_keywords."""
    ist = pytz.timezone("Asia/Kolkata")
    start = pd.Timestamp.now(tz=ist).normalize().tz_convert("UTC")

    # Get recent audio samples with high agitation scores and keywords
    docs = (
        db.collection("audio_samples")
        .where("timestamp", ">=", int(start.timestamp() * 1000))
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(50)
        .stream()
    )

    alerts = []
    for doc in docs:
        data = doc.to_dict()
        keywords = data.get("top_keywords", [])
        score = data.get("combined_agitation_score", 0)

        # Only create alerts for high-agitation speech with detected keywords
        if keywords and score > 0.5:
            for kw in keywords:
                if isinstance(kw, dict) and "keyword" in kw:
                    keyword_text = kw.get("keyword", "").lower()
                    category = kw.get("category", "")

                    # Trigger alert for pain/hurt keywords
                    if any(word in keyword_text for word in ["pain", "hurt", "help", "distress"]):
                        alerts.append({
                            "timestamp": data.get("timestamp"),
                            "cmai_item": 22,
                            "behaviour": f"Speech keyword detected: {keyword_text}",
                            "confidence_level": "HIGH" if score > 0.7 else "MEDIUM",
                            "transcription": "",
                            "detected_keywords": [keyword_text],
                            "contributing_scores": {
                                "speech": data.get("speech_detection_score", 0),
                                "acoustic": data.get("acoustic_score", 0),
                                "motion": data.get("motion_score", 0)
                            }
                        })

    df = pd.DataFrame(alerts)
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(ist)
    return df.sort_values("timestamp", ascending=False)

# Load data
sensor_df = load_sensor_data(live_mode)
audio_df = load_audio_data(live_mode)
cmai_df = load_cmai_detections(live_mode)

# Update cache
st.session_state.cached_sensor_df = sensor_df
st.session_state.cached_audio_df = audio_df
st.session_state.last_fetch_time = datetime.now()

# ════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════
def latest_val(df, col, fmt=".1f"):
    if df.empty or col not in df.columns:
        return "—"
    v = df[col].dropna()
    if v.empty:
        return "—"
    return f"{v.iloc[-1]:{fmt}}"

def safe_get_stats(df, col, window=20):
    """Safely compute statistics for a column."""
    if df.empty or col not in df.columns:
        return {"available": False}
    recent = df[col].dropna().tail(window)
    if len(recent) < 3:
        return {"available": False}
    return {
        "available": True,
        "current": recent.iloc[-1],
        "mean": recent.mean(),
        "std": recent.std() if len(recent) > 1 else 0,
        "min": recent.min(),
        "max": recent.max(),
    }

def safe_get_val(df, col):
    """Safely get latest value from dataframe."""
    if df.empty or col not in df.columns:
        return None
    v = df[col].dropna()
    return v.iloc[-1] if not v.empty else None

def count_sign_changes(series):
    """Count oscillations: rapid acceleration changes (up/down motion)."""
    if series.empty or len(series) < 2:
        return 0
    # Look at deltas (changes) in acceleration magnitude
    deltas = series.diff().dropna()
    if len(deltas) < 2:
        return 0
    # Count how many times the delta changes sign (acceleration reversals)
    sign_changes = 0
    prev_sign = None
    for val in deltas:
        if val is not None and val != 0:
            current_sign = 1 if val > 0 else -1
            if prev_sign is not None and current_sign != prev_sign:
                sign_changes += 1
            prev_sign = current_sign
    return sign_changes

# ════════════════════════════════════════════════════════════════
#  CMAI DETECTION RULES (Rule-based, no ML)
#  CALIBRATED FOR SAMSUNG GALAXY WATCH 4 MICROPHONE
# ════════════════════════════════════════════════════════════════
def detect_cmai_behaviours(sensor_df, audio_df):
    """
    Rule-based CMAI behaviour detection using CALIBRATED thresholds
    for Samsung Galaxy Watch 4 microphone characteristics.

    Thresholds calibrated from actual watch data:
    - Normal audio energy: 1000-2000
    - Elevated (loud) energy: 2500-4000+
    - Normal pitch: 80-150 Hz
    - Elevated pitch: 150-200+ Hz
    - Normal spectral centroid: 1000-2000 Hz
    - Elevated (harsh) centroid: 2500-4000+ Hz
    """
    detections = []

    # Get current values
    energy = safe_get_val(audio_df, "audio_energy")
    pitch = safe_get_val(audio_df, "pitch")
    zcr = safe_get_val(audio_df, "zcr")
    spectral_centroid = safe_get_val(audio_df, "spectral_centroid")
    spectral_flux = safe_get_val(audio_df, "spectral_flux")
    speech_ratio = safe_get_val(audio_df, "speech_ratio")
    energy_variance = safe_get_val(audio_df, "energy_variance")
    spectral_bandwidth = safe_get_val(audio_df, "spectral_bandwidth")

    accel = safe_get_val(sensor_df, "accelMag_smooth")
    hr = safe_get_val(sensor_df, "heart_rate")
    gyro_mag = safe_get_val(sensor_df, "gyroMag")


    # ═══════════════════════════════════════════════════════════
    # COMPUTE BASELINE STATISTICS FOR RELATIVE DETECTION
    # ═══════════════════════════════════════════════════════════
    energy_stats = safe_get_stats(audio_df, "audio_energy", window=10)
    pitch_stats = safe_get_stats(audio_df, "pitch", window=10)
    sc_stats = safe_get_stats(audio_df, "spectral_centroid", window=10)

    # ═══════════════════════════════════════════════════════════
    # AUDIO-BASED DETECTIONS (CMAI Verbal Behaviours)
    # THRESHOLDS CALIBRATED FOR WATCH MICROPHONE
    # ═══════════════════════════════════════════════════════════

    # CMAI Item 22: Screaming / Loud Vocalization
    # CALIBRATED: Watch mic shows ~3000-4000 energy for loud sounds
    # IMPORTANT: Only detect if energy > 1500 (meaningful sound level)
    if all(v is not None for v in [energy, spectral_centroid]) and energy > 1500:
        # Count how many indicators are elevated
        scream_indicators = 0

        # High energy (above 2500 is elevated for watch mic)
        if energy > 2500:
            scream_indicators += 1
        if energy > 3500:
            scream_indicators += 1  # Extra point for very high

        # High spectral centroid (brightness/harshness)
        if spectral_centroid > 2500:
            scream_indicators += 1
        if spectral_centroid > 3500:
            scream_indicators += 1

        # Elevated pitch (above normal speech)
        if pitch is not None and pitch > 150:
            scream_indicators += 1
        if pitch is not None and pitch > 200:
            scream_indicators += 1

        # High ZCR (harsh sounds)
        if zcr is not None and zcr > 0.15:
            scream_indicators += 1

        # Relative detection: current >> baseline
        if energy_stats["available"] and energy is not None:
            if energy > energy_stats["mean"] + 2 * energy_stats["std"]:
                scream_indicators += 1

        # Decision based on number of indicators
        if scream_indicators >= 5:
            detections.append({
                "cmai_item": 22,
                "behaviour": "Screaming / Loud Vocalization",
                "confidence": "HIGH",
                "evidence": f"Energy={energy:.0f}, SC={spectral_centroid:.0f}Hz, Pitch={pitch:.0f}Hz" if pitch else f"Energy={energy:.0f}, SC={spectral_centroid:.0f}Hz",
                "category": "verbal"
            })
        elif scream_indicators >= 3:
            detections.append({
                "cmai_item": 22,
                "behaviour": "Loud Vocalization",
                "confidence": "MEDIUM",
                "evidence": f"Energy={energy:.0f}, SC={spectral_centroid:.0f}Hz ({scream_indicators} indicators)",
                "category": "verbal"
            })

    # CMAI Item 26: Strange noises (peculiar sounds, grunts, moans)
    # Clapping, banging, sudden impact sounds
    # IMPORTANT: Only detect if there's actually significant sound (energy > 500)
    if all(v is not None for v in [energy, zcr]) and energy > 500:
        strange_indicators = 0

        # High ZCR indicates non-speech noise
        if zcr > 0.2:
            strange_indicators += 1
        if zcr > 0.3:
            strange_indicators += 1

        # Elevated energy (must be meaningful, not just ambient)
        if energy > 2000:
            strange_indicators += 1

        # Low speech ratio (not normal speech) - only count if energy is significant
        if speech_ratio is not None and speech_ratio < 0.4 and energy > 1000:
            strange_indicators += 1

        # High energy variance (irregular sound)
        if energy_variance is not None and energy_variance > 1.0:
            strange_indicators += 1

        # Wide bandwidth (broadband noise like clapping)
        if spectral_bandwidth is not None and spectral_bandwidth > 2000:
            strange_indicators += 1

        if strange_indicators >= 4:
            detections.append({
                "cmai_item": 26,
                "behaviour": "Strange Noises / Impact Sounds",
                "confidence": "HIGH",
                "evidence": f"ZCR={zcr:.3f}, Energy={energy:.0f}, SpeechRatio={speech_ratio:.2f}" if speech_ratio else f"ZCR={zcr:.3f}, Energy={energy:.0f}",
                "category": "verbal"
            })
        elif strange_indicators >= 3:  # Raised from 2 to 3 to reduce false positives
            detections.append({
                "cmai_item": 26,
                "behaviour": "Unusual Sounds",
                "confidence": "MEDIUM",
                "evidence": f"ZCR={zcr:.3f}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # CMAI Item 24: Verbal aggression / Agitated speech
    # IMPORTANT: Only detect if energy > 1000 (actual speech, not silence)
    if all(v is not None for v in [energy, speech_ratio]) and energy > 1000:
        verbal_indicators = 0

        # High speech ratio (lots of talking)
        if speech_ratio > 0.5:
            verbal_indicators += 1
        if speech_ratio > 0.7:
            verbal_indicators += 1

        # Elevated energy while speaking
        if energy > 2000:
            verbal_indicators += 1
        if energy > 3000:
            verbal_indicators += 1

        # Elevated pitch
        if pitch is not None and pitch > 140:
            verbal_indicators += 1

        # High spectral centroid (tense voice)
        if spectral_centroid is not None and spectral_centroid > 2000:
            verbal_indicators += 1

        if verbal_indicators >= 4:
            detections.append({
                "cmai_item": 24,
                "behaviour": "Verbal Agitation",
                "confidence": "HIGH",
                "evidence": f"Speech={speech_ratio:.0%}, Energy={energy:.0f}, Pitch={pitch:.0f}Hz" if pitch else f"Speech={speech_ratio:.0%}, Energy={energy:.0f}",
                "category": "verbal"
            })
        elif verbal_indicators >= 2:
            detections.append({
                "cmai_item": 24,
                "behaviour": "Elevated Speech",
                "confidence": "MEDIUM",
                "evidence": f"Speech={speech_ratio:.0%}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # CMAI Item 25: Constant vocalization
    # Only detect if there's actual speech (energy > 500)
    if speech_ratio is not None and speech_ratio > 0.6 and energy is not None and energy > 500:
        detections.append({
            "cmai_item": 25,
            "behaviour": "Continuous Vocalization",
            "confidence": "MEDIUM" if speech_ratio > 0.8 else "LOW",
            "evidence": f"Speech ratio={speech_ratio:.0%}",
            "category": "verbal"
        })

    # ═══════════════════════════════════════════════════════════
    # SUDDEN SOUND DETECTION (Clapping, Banging, etc.)
    # Only detect if energy is significant (not ambient noise)
    # ═══════════════════════════════════════════════════════════
    if spectral_flux is not None and energy is not None:
        if spectral_flux > 1000 and energy > 2500:
            detections.append({
                "cmai_item": 26,
                "behaviour": "Sudden Loud Sound (Clap/Bang)",
                "confidence": "HIGH",
                "evidence": f"Flux={spectral_flux:.0f}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # ═══════════════════════════════════════════════════════════
    # MOTION-BASED DETECTIONS (CMAI Physical Behaviours)
    # ═══════════════════════════════════════════════════════════

    # CMAI Item 12: Pacing, aimless wandering + HIGH ENERGY OSCILLATIONS
    # Research basis: Sustained moderate movement without rest OR rapid repetitive motion
    if accel is not None:
        # Calculate movement statistics
        accel_stats = safe_get_stats(sensor_df, "accelMag_smooth", window=30)
        if accel_stats["available"]:
            # Original: Sustained movement with low variance = pacing
            if accel_stats["mean"] > 12 and accel_stats["std"] < 3:
                detections.append({
                    "cmai_item": 12,
                    "behaviour": "Pacing/wandering",
                    "confidence": "MEDIUM",
                    "evidence": f"Sustained movement={accel_stats['mean']:.1f}, σ={accel_stats['std']:.2f}",
                    "category": "physical"
                })

            # NEW: High-energy oscillatory motion (hand shaking, tremor, fidgeting)
            elif accel_stats["mean"] > 8 and accel_stats["std"] >= 3:
                # Rapid variation in acceleration = oscillation
                recent_accel = sensor_df["accelMag_smooth"].dropna().tail(30)
                if len(recent_accel) >= 10:
                    # Count how many times acceleration changes direction rapidly
                    accel_deltas = recent_accel.diff().dropna()
                    high_variance_count = (accel_deltas.abs() > 5).sum()

                    if high_variance_count >= 10:  # Many rapid changes
                        detections.append({
                            "cmai_item": 12,
                            "behaviour": "Agitated Fidgeting/Tremor",
                            "confidence": "MEDIUM",
                            "evidence": f"Mean={accel_stats['mean']:.1f}, σ={accel_stats['std']:.2f}, Rapid changes={high_variance_count}",
                            "category": "physical"
                        })

    # CMAI Item 20: Repetitive mannerisms (oscillatory movements - hand up/down)
    # Detection: Use gyroX to detect hand up-down oscillations
    # Get last 30 samples of gyroX and count sign changes
    if "gyroX" in sensor_df.columns:
        recent_gyroX = sensor_df["gyroX"].dropna().tail(30)
        if len(recent_gyroX) >= 10:
            # Count sign changes directly in gyroX values (not deltas)
            sign_changes = 0
            prev_sign = None
            for val in recent_gyroX:
                if val is not None and val != 0:
                    current_sign = 1 if val > 0 else -1
                    if prev_sign is not None and current_sign != prev_sign:
                        sign_changes += 1
                    prev_sign = current_sign

            # Many sign changes = oscillatory motion (hand up/down)
            if sign_changes >= 4:  # 4+ reversals in ~30 samples = oscillation
                detections.append({
                    "cmai_item": 20,
                    "behaviour": "Repetitive Mannerisms (Hand Oscillation)",
                    "confidence": "HIGH" if sign_changes >= 8 else "MEDIUM",
                    "evidence": f"GyroX sign changes={sign_changes}/30",
                    "category": "physical"
                })

    # CMAI Item 21: General restlessness
    # Research basis: High movement + elevated HR + high variance
    if all(v is not None for v in [accel, hr]):
        accel_stats = safe_get_stats(sensor_df, "accelMag_smooth", window=20)
        hr_stats = safe_get_stats(sensor_df, "heartRate", window=20)
        if accel_stats["available"] and hr_stats["available"]:
            if accel_stats["mean"] > 15 and accel_stats["std"] > 5 and hr_stats["current"] > 90:
                detections.append({
                    "cmai_item": 21,
                    "behaviour": "General restlessness",
                    "confidence": "MEDIUM",
                    "evidence": f"Move={accel_stats['mean']:.1f}±{accel_stats['std']:.1f}, HR={hr_stats['current']:.0f}",
                    "category": "physical"
                })


    # ═══════════════════════════════════════════════════════════
    # COMPOSITE DETECTIONS
    # ═══════════════════════════════════════════════════════════

    # Combined agitation indicator (high arousal state)
    arousal_indicators = 0
    if energy is not None and energy > 3000:
        arousal_indicators += 1
    if pitch is not None and pitch > 250:
        arousal_indicators += 1
    if accel is not None and accel > 15:
        arousal_indicators += 1
    if hr is not None and hr > 95:
        arousal_indicators += 1

    if arousal_indicators >= 3:
        detections.append({
            "cmai_item": 0,
            "behaviour": "High arousal state",
            "confidence": "HIGH",
            "evidence": f"{arousal_indicators}/4 indicators elevated",
            "category": "composite"
        })

    return detections

# ════════════════════════════════════════════════════════════════
#  PLOTLY THEME TOKENS
# ════════════════════════════════════════════════════════════════
BG      = "rgba(0,0,0,0)"
GRID    = "rgba(255,255,255,.06)"
FONT_C  = "#94a3b8"
ACCENT  = ["#38bdf8", "#f472b6", "#a78bfa", "#34d399", "#fbbf24", "#fb923c"]

def style_fig(fig, height=280):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(l=0, r=10, t=30, b=0),
        height=height,
        font=dict(family="Inter", color=FONT_C, size=12),
        legend=dict(orientation="h", yanchor="top", y=1.12, xanchor="left", x=0,
                    font=dict(size=11)),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=GRID, gridwidth=1),
        hovermode="x unified",
    )
    return fig

# ════════════════════════════════════════════════════════════════
#  RUN CMAI DETECTION
# ════════════════════════════════════════════════════════════════
detected_behaviours = detect_cmai_behaviours(sensor_df, audio_df)
st.session_state.detected_behaviours = detected_behaviours

# Auto-update patient state based on detections
# Trigger Agitated if: ANY HIGH confidence OR 2+ MEDIUM confidence detections
high_confidence = [d for d in detected_behaviours if d["confidence"] == "HIGH"]
medium_confidence = [d for d in detected_behaviours if d["confidence"] == "MEDIUM"]

# Get current energy level to help determine calm state
current_energy = safe_get_val(audio_df, "audio_energy")
is_quiet = current_energy is not None and current_energy < 500

if high_confidence or len(medium_confidence) >= 2:
    st.session_state.patient_state = "Agitated"
elif len(detected_behaviours) == 0 or is_quiet:
    # Set Calm if no detections OR if environment is quiet
    st.session_state.patient_state = "Calm"
elif len(detected_behaviours) == 1 and detected_behaviours[0]["confidence"] == "LOW":
    # Single LOW confidence detection = likely still calm
    st.session_state.patient_state = "Calm"

# ════════════════════════════════════════════════════════════════
#  TAB NAVIGATION
# ════════════════════════════════════════════════════════════════
tab_dashboard, tab_cmai, tab_audio = st.tabs(["📊 Live Dashboard", "🧠 CMAI Detection", "🎵 Audio Analysis"])

# ════════════════════════════════════════════════════════════════
#  TAB 1: LIVE DASHBOARD
# ════════════════════════════════════════════════════════════════
with tab_dashboard:
    # ════════════════════════════════════════════════════════════════
    #  ROW 1 — STATUS CARDS + AGITATION CONTROL
    # ════════════════════════════════════════════════════════════════
    st.markdown("<p class='section-header'>📊 &nbsp;STATUS OVERVIEW</p>", unsafe_allow_html=True)

    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns([1.6, 1, 1, 1, 1.4])

    with r1c1:
        state = st.session_state.patient_state
        if state == "Calm":
            st.markdown("<span class='badge-calm'>😌 &nbsp;Calm</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='badge-agitated'>⚠️ &nbsp;Agitated</span>", unsafe_allow_html=True)

    with r1c2:
        st.metric("❤️ Heart Rate", latest_val(sensor_df, "heartRate", ".0f"))

    with r1c3:
        st.metric("🏃 Movement", latest_val(sensor_df, "accelMag_smooth"))

    with r1c4:
        st.metric("🗣️ Speech Ratio", latest_val(audio_df, "speech_ratio", ".2f"))

    # Show agitation score breakdown if available
    cas = safe_get_val(audio_df, "combined_agitation_score")
    if cas is not None:
        sds = safe_get_val(audio_df, "speech_detection_score") or 0
        aas = safe_get_val(audio_df, "acoustic_score") or 0
        ms = safe_get_val(audio_df, "motion_score") or 0
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #1e1e2f 0%, #2a2a40 100%); padding: 12px 16px;
                    border-radius: 10px; margin: 10px 0; border: 1px solid rgba(255,255,255,.08);'>
            <div style='display: flex; justify-content: space-around; text-align: center;'>
                <div>
                    <div style='font-size: 1.8rem; font-weight: 700; color: {"#ef4444" if cas >= 0.8 else "#f59e0b" if cas >= 0.6 else "#22c55e"};'>{cas*100:.0f}%</div>
                    <div style='font-size: 0.75rem; color: #64748b;'>Combined Score</div>
                </div>
                <div style='border-left: 1px solid rgba(255,255,255,.1); padding-left: 20px;'>
                    <div style='color: #38bdf8;'>Speech: {sds*100:.0f}%</div>
                    <div style='color: #f472b6;'>Acoustic: {aas*100:.0f}%</div>
                    <div style='color: #34d399;'>Motion: {ms*100:.0f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with r1c5:
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("⚡ Trigger Agitation", width='stretch', type="primary"):
                st.session_state.patient_state = "Agitated"
                st.rerun()
        with bc2:
            if st.button("🔄 Reset to Calm", width='stretch'):
                st.session_state.patient_state = "Calm"
                st.rerun()

    # ════════════════════════════════════════════════════════════════
    # KEYWORD DETECTION ALERTS (from speech recognition)
    # ════════════════════════════════════════════════════════════════
    latest_transcription = safe_get_val(audio_df, "transcription")
    latest_score = safe_get_val(audio_df, "combined_agitation_score")
    latest_keywords = safe_get_val(audio_df, "top_keywords")

    if latest_transcription and str(latest_transcription).strip():
        score_class = "score-high" if latest_score and latest_score >= 0.8 else ("score-medium" if latest_score and latest_score >= 0.6 else "score-low")
        score_pct = f"{latest_score*100:.0f}%" if latest_score else "N/A"

        # Build keywords HTML
        keywords_html = ""
        if latest_keywords and isinstance(latest_keywords, list):
            for kw in latest_keywords[:5]:
                if isinstance(kw, dict):
                    keywords_html += f"<span class='keyword-tag'>{kw.get('keyword', '')} ({kw.get('category', '')})</span>"

        st.markdown(f"""
        <div class='keyword-alert'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <strong style='font-size: 1.1rem;'>🎤 SPEECH DETECTED</strong>
                    <span class='score-badge {score_class}' style='margin-left: 12px;'>{score_pct}</span>
                </div>
                <span style='opacity: 0.7; font-size: 0.85rem;'>Agitation Score</span>
            </div>
            <div style='margin: 12px 0; font-size: 1.2rem; font-style: italic;'>
                "{latest_transcription}"
            </div>
            <div>
                <strong>Keywords:</strong> {keywords_html if keywords_html else "None detected"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Show active detections
    if detected_behaviours:
        st.markdown("<p class='section-header'>🚨 &nbsp;ACTIVE DETECTIONS</p>", unsafe_allow_html=True)
        for det in detected_behaviours:
            if det["confidence"] == "HIGH":
                st.markdown(f"""
                <div class='detection-alert'>
                    <strong>CMAI #{det['cmai_item']}: {det['behaviour']}</strong><br>
                    <span style='font-size:0.85rem;'>{det['evidence']}</span>
                </div>
                """, unsafe_allow_html=True)
            elif det["confidence"] == "MEDIUM":
                st.markdown(f"""
                <div class='detection-alert-warning'>
                    <strong>CMAI #{det['cmai_item']}: {det['behaviour']}</strong><br>
                    <span style='font-size:0.85rem;'>{det['evidence']}</span>
                </div>
                """, unsafe_allow_html=True)

    # Intervention banner
    if st.session_state.patient_state == "Agitated":
        st.markdown("""
        <div class='intervention-banner'>
            🎵 &nbsp; <b>Intervention Active</b> — Playing calming music…  &nbsp;
            🧘 Guided breathing pattern initiated
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ═══════════════════════════════════════════════════════════
    #  ROW 2 — MAIN CHARTS (Motion | Audio)
    # ═══════════════════════════════════════════════════════════
    st.markdown("<p class='section-header'>📈 &nbsp;LIVE SIGNALS</p>", unsafe_allow_html=True)

    chart_left, chart_right = st.columns(2)

    # MOTION CHART
    with chart_left:
        st.markdown("##### Motion & Physiology")
        if not sensor_df.empty:
            fig_motion = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.08,
                row_heights=[0.55, 0.45],
            )
            # Use accelMag_smooth if available, otherwise use accelMag
            accel_col = "accelMag_smooth" if "accelMag_smooth" in sensor_df.columns else ("accelMag" if "accelMag" in sensor_df.columns else None)
            if accel_col:
                fig_motion.add_trace(
                    go.Scatter(x=sensor_df["timestamp"], y=sensor_df[accel_col],
                              name="Movement", line=dict(color=ACCENT[0], width=2)),
                    row=1, col=1,
                )
            if "heartRate" in sensor_df.columns:
                fig_motion.add_trace(
                    go.Scatter(x=sensor_df["timestamp"], y=sensor_df["heartRate"],
                              name="Heart Rate", line=dict(color=ACCENT[1], width=2)),
                    row=2, col=1,
                )
            if accel_col or "heartRate" in sensor_df.columns:
                style_fig(fig_motion, height=350)
                st.plotly_chart(fig_motion, width='stretch')
            else:
                st.info("No motion or heart rate data available")
        else:
            st.info("Waiting for sensor data…")

    # AUDIO CHART
    with chart_right:
        st.markdown("##### Audio Features")
        if not audio_df.empty:
            # Check which audio features are available
            audio_features = []
            for col in ["audio_energy", "pitch", "zcr", "spectral_centroid"]:
                if col in audio_df.columns:
                    audio_features.append(col)

            if audio_features:
                fig_audio = make_subplots(
                    rows=len(audio_features), cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.06,
                    subplot_titles=[f.replace("_", " ").title() for f in audio_features],
                )
                for idx, feat in enumerate(audio_features):
                    fig_audio.add_trace(
                        go.Scatter(
                            x=audio_df["timestamp"],
                            y=audio_df[feat],
                            name=feat,
                            line=dict(color=ACCENT[idx % len(ACCENT)], width=2),
                            fill="tozeroy",
                            fillcolor=f"rgba({','.join(str(int(ACCENT[idx % len(ACCENT)][i:i+2], 16)) for i in (1, 3, 5))},.1)",
                        ),
                        row=idx + 1, col=1,
                    )
                style_fig(fig_audio, height=350)
                fig_audio.update_annotations(font=dict(size=11, color=FONT_C))
                st.plotly_chart(fig_audio, width='stretch')
            else:
                st.info("No audio features available")
        else:
            st.info("Waiting for audio data…")

    # ═══════════════════════════════════════════════════════════
    #  ROW 3 — SUPPLEMENTARY
    # ═══════════════════════════════════════════════════════════
    st.markdown("<p class='section-header'>🔎 &nbsp;SUPPLEMENTARY</p>", unsafe_allow_html=True)

    bot1, bot2 = st.columns(2)

    with bot1:
        st.markdown("###### 💡 Ambient Light")
        if not sensor_df.empty and "light" in sensor_df.columns:
            fig_light = go.Figure(go.Scatter(
                x=sensor_df["timestamp"], y=sensor_df["light"],
                line=dict(color=ACCENT[4], width=2),
                fill="tozeroy", fillcolor="rgba(251,191,36,.08)",
            ))
            style_fig(fig_light, height=180)
            st.plotly_chart(fig_light, width='stretch')
        else:
            st.caption("No light data")

    with bot2:
        st.markdown("###### 📊 New Audio Features")
        # Show new spectral features if available
        new_features = ["zcr", "spectral_centroid", "spectral_bandwidth", "spectral_flux"]
        available_new = [f for f in new_features if f in audio_df.columns]
        if available_new and not audio_df.empty:
            latest = {f: safe_get_val(audio_df, f) for f in available_new}
            for f, v in latest.items():
                if v is not None:
                    st.metric(f.replace("_", " ").title(), f"{v:.2f}")
        else:
            st.caption("New audio features not yet available")


# ════════════════════════════════════════════════════════════════
#  TAB 2: CMAI DETECTION
# ════════════════════════════════════════════════════════════════
with tab_cmai:
    st.markdown("## 🧠 CMAI Behaviour Detection")

    st.markdown("""
    <div class='research-note'>
        <strong>What is CMAI?</strong> Cohen-Mansfield Agitation Inventory - a clinical tool to assess
        agitation in dementia patients. Each item corresponds to a specific behavioural pattern.
        <br><br>
        <strong>How it works:</strong> The watch records 5 seconds of audio every 15 seconds, transcribes speech,
        detects keywords (like "help", "pain"), and combines with movement data to calculate an agitation score.
    </div>
    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # RECENT CMAI ALERTS (from cmai_detections collection)
    # ════════════════════════════════════════════════════════════════
    st.markdown("### 🚨 Recent Speech-Based Alerts")

    if not cmai_df.empty:
        for _, row in cmai_df.head(5).iterrows():
            conf = row.get("confidence_level", "MEDIUM")
            conf_color = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#6b7280"}.get(conf, "#6b7280")
            cmai_item = row.get("cmai_item", "?")
            behaviour = row.get("behaviour", "Unknown")
            transcription = row.get("transcription", "")
            keywords = row.get("detected_keywords", [])
            timestamp = row.get("timestamp", "")
            time_str = timestamp.strftime("%H:%M:%S") if hasattr(timestamp, "strftime") else str(timestamp)

            # Get contributing scores
            scores = row.get("contributing_scores", {})
            speech_score = scores.get("speech", 0) if isinstance(scores, dict) else 0
            acoustic_score = scores.get("acoustic", 0) if isinstance(scores, dict) else 0
            motion_score = scores.get("motion", 0) if isinstance(scores, dict) else 0

            keywords_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)

            st.markdown(f"""
            <div style='background: rgba(30,30,47,0.9); border-left: 4px solid {conf_color};
                        padding: 14px 18px; border-radius: 0 10px 10px 0; margin: 10px 0;'>
                <div style='display: flex; justify-content: space-between;'>
                    <strong style='color: {conf_color}; font-size: 1.1rem;'>CMAI #{cmai_item}: {behaviour}</strong>
                    <span style='color: #64748b;'>{time_str}</span>
                </div>
                <div style='margin: 10px 0; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 6px;'>
                    <span style='color: #94a3b8;'>Patient said:</span>
                    <span style='color: #fff; font-style: italic;'> "{transcription or 'No speech'}"</span>
                </div>
                <div style='margin-top: 8px;'>
                    <span style='color: #a78bfa;'>Keywords: </span>
                    <span style='color: #e2e8f0;'>{keywords_str or "None"}</span>
                </div>
                <div style='margin-top: 8px; display: flex; gap: 16px; font-size: 0.85rem;'>
                    <span style='color: #38bdf8;'>Speech: {speech_score:.0%}</span>
                    <span style='color: #f472b6;'>Acoustic: {acoustic_score:.0%}</span>
                    <span style='color: #34d399;'>Motion: {motion_score:.0%}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🎤 No keyword alerts detected. Alerts appear when PAIN, HELP, or similar words are spoken with agitation.")


    st.markdown("---")

    # Current rule-based detections
    st.markdown("### 📊 Current Rule-Based Detections")

    if detected_behaviours:
        for det in detected_behaviours:
            conf_color = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#6b7280"}[det["confidence"]]
            st.markdown(f"""
            <div style='background: rgba(30,30,47,0.8); border-left: 4px solid {conf_color};
                        padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 8px 0;'>
                <strong style='color: {conf_color};'>CMAI #{det['cmai_item']}: {det['behaviour']}</strong>
                <span style='float: right; background: {conf_color}22; color: {conf_color};
                             padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;'>{det['confidence']}</span>
                <br><span style='color: #94a3b8; font-size: 0.85rem;'>{det['evidence']}</span>
                <br><span style='color: #64748b; font-size: 0.75rem;'>Category: {det['category']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No agitation behaviours currently detected")

    st.markdown("---")

    # Detection rules reference
    st.markdown("### 📋 Detection Rules Reference")

    rules_data = [
        {"CMAI": 22, "Behaviour": "Screaming/Loud Vocalization", "Signal Thresholds": "Energy > 1500 + (Energy > 2500 OR SC > 2500 OR Pitch > 150)", "Basis": "Must have significant sound"},
        {"CMAI": 26, "Behaviour": "Strange noises/Clapping", "Signal Thresholds": "Energy > 500 + (ZCR > 0.2 OR Flux > 1000) + 3+ indicators", "Basis": "Non-speech, requires sound"},
        {"CMAI": 24, "Behaviour": "Verbal agitation", "Signal Thresholds": "Energy > 1000 + Speech > 0.5 + (Pitch > 140 OR SC > 2000)", "Basis": "Elevated speech"},
        {"CMAI": 25, "Behaviour": "Continuous vocalization", "Signal Thresholds": "Energy > 500 + Speech ratio > 0.6", "Basis": "Sustained speech activity"},
        {"CMAI": 12, "Behaviour": "Pacing/wandering", "Signal Thresholds": "Sustained movement > 12 AND σ < 3", "Basis": "Regular motion patterns"},
        {"CMAI": 20, "Behaviour": "Repetitive mannerisms", "Signal Thresholds": "GyroX sign changes >= 4", "Basis": "Hand oscillation detection"},
        {"CMAI": 21, "Behaviour": "General restlessness", "Signal Thresholds": "Movement > 15 AND σ > 5 AND HR > 90", "Basis": "Combined arousal indicators"},
    ]

    st.dataframe(pd.DataFrame(rules_data), hide_index=True, width='stretch')

    st.markdown("---")

    # Available signals
    st.markdown("### 📡 Available Signals")

    sig_col1, sig_col2, sig_col3 = st.columns(3)

    with sig_col1:
        st.markdown("""
        <div class='cmai-section-box'>
            <div class='cmai-category-header' style='color: #38bdf8;'>🏃 Motion Signals</div>
            <span class='signal-tag'>accelMag_smooth</span>
            <span class='signal-tag'>gyroX</span>
            <span class='signal-tag'>gyroY</span>
            <span class='signal-tag'>gyroZ</span>
        </div>
        """, unsafe_allow_html=True)

    with sig_col2:
        st.markdown("""
        <div class='cmai-section-box'>
            <div class='cmai-category-header' style='color: #f472b6;'>🗣️ Audio Signals</div>
            <span class='signal-tag'>audio_energy</span>
            <span class='signal-tag'>speech_ratio</span>
            <span class='signal-tag'>pitch</span>
            <span class='signal-tag-new'>zcr</span>
            <span class='signal-tag-new'>spectral_centroid</span>
            <span class='signal-tag-new'>spectral_bandwidth</span>
            <span class='signal-tag-new'>spectral_flux</span>
        </div>
        """, unsafe_allow_html=True)

    with sig_col3:
        st.markdown("""
        <div class='cmai-section-box'>
            <div class='cmai-category-header' style='color: #34d399;'>❤️ Physiological</div>
            <span class='signal-tag'>heartRate</span>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TAB 3: AUDIO ANALYSIS
# ════════════════════════════════════════════════════════════════
with tab_audio:
    st.markdown("## 🎵 Audio Feature Analysis")

    st.markdown("""
    <div class='research-note'>
        <strong>Mathematically Provable Features</strong>: All audio features are derived from
        well-defined signal processing algorithms (FFT, autocorrelation, mel filterbank)
        without any machine learning components.
    </div>
    """, unsafe_allow_html=True)

    if not audio_df.empty:
        # Feature definitions
        st.markdown("### 📖 Feature Definitions")

        feature_defs = {
            "audio_energy": ("RMS Energy", "sqrt(1/N × Σx[n]²)", "Loudness/intensity of sound"),
            "zcr": ("Zero-Crossing Rate", "(1/2N) × Σ|sign(x[n]) - sign(x[n-1])|", "High ZCR = noise/unvoiced, Low ZCR = voiced speech"),
            "spectral_centroid": ("Spectral Centroid", "Σ(f[k] × |X[k]|) / Σ|X[k]|", "Brightness - high = harsh/screaming, low = calm"),
            "spectral_bandwidth": ("Spectral Bandwidth", "sqrt(Σ((f[k] - SC)² × |X[k]|) / Σ|X[k]|)", "Frequency spread - wide = screams/noise"),
            "spectral_flux": ("Spectral Flux", "Σ(|X_t[k]| - |X_{t-1}[k]|)²", "Sudden changes - high = onset detection"),
            "pitch": ("Pitch (F0)", "Autocorrelation-based", "Fundamental frequency - high pitch = distress"),
            "speech_ratio": ("Speech Ratio", "VAD: Energy + ZCR + Centroid", "Proportion of audio containing speech"),
        }

        cols = st.columns(3)
        for idx, (key, (name, formula, desc)) in enumerate(feature_defs.items()):
            with cols[idx % 3]:
                val = safe_get_val(audio_df, key)
                val_str = f"{val:.2f}" if val is not None else "N/A"
                available = "✅" if key in audio_df.columns else "❌"
                st.markdown(f"""
                <div style='background: rgba(30,30,47,0.6); padding: 12px; border-radius: 8px; margin: 4px 0;'>
                    <strong>{available} {name}</strong><br>
                    <code style='font-size: 0.7rem; color: #64748b;'>{formula}</code><br>
                    <span style='color: #94a3b8; font-size: 0.8rem;'>{desc}</span><br>
                    <span style='color: #38bdf8; font-weight: 600;'>Current: {val_str}</span>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # Time series of all audio features
        st.markdown("### 📈 Audio Feature Timeline")

        all_audio_cols = [c for c in audio_df.columns if c not in ["timestamp", "mfcc"]]
        selected_features = st.multiselect(
            "Select features to display:",
            all_audio_cols,
            default=["audio_energy", "pitch", "zcr", "spectral_centroid"] if "zcr" in audio_df.columns else ["audio_energy", "pitch"]
        )

        if selected_features:
            fig = make_subplots(rows=len(selected_features), cols=1, shared_xaxes=True, vertical_spacing=0.05)
            for i, feat in enumerate(selected_features):
                if feat in audio_df.columns:
                    fig.add_trace(
                        go.Scatter(x=audio_df["timestamp"], y=audio_df[feat], name=feat,
                                  line=dict(color=ACCENT[i % len(ACCENT)], width=2)),
                        row=i+1, col=1
                    )
            style_fig(fig, height=100*len(selected_features))
            st.plotly_chart(fig, width='stretch')

        st.markdown("---")

        # MFCC visualization
        st.markdown("### 🎙️ MFCC Analysis")
        if "mfcc" in audio_df.columns:
            try:
                sample = audio_df["mfcc"].dropna().iloc[-1] if not audio_df["mfcc"].dropna().empty else None
                if sample is not None and isinstance(sample, (list, np.ndarray)):
                    mfcc_vec = np.array(sample, dtype=float)
                    fig_mfcc = go.Figure(go.Bar(
                        x=[f"MFCC_{i}" for i in range(len(mfcc_vec))],
                        y=mfcc_vec,
                        marker_color=ACCENT[2],
                    ))
                    style_fig(fig_mfcc, height=250)
                    fig_mfcc.update_layout(title="Latest MFCC Coefficients")
                    st.plotly_chart(fig_mfcc, width='stretch')
            except Exception as e:
                st.warning(f"Could not parse MFCC data: {e}")
        else:
            st.caption("MFCC data not available")
    else:
        st.info("Waiting for audio data…")

# ════════════════════════════════════════════════════════════════
#  FOOTER
# ════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    f"<p style='text-align:center; color:#475569; font-size:.75rem;'>"
    f"WearOS Behavioural Monitor | Data points: Sensor={len(sensor_df)}, Audio={len(audio_df)} | "
    f"Last fetch: {st.session_state.last_fetch_time.strftime('%H:%M:%S') if st.session_state.last_fetch_time else 'N/A'}"
    f"</p>",
    unsafe_allow_html=True,
)
