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
.block-container { padding-top: 1.5rem; padding-bottom: 0.5rem; }

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
    color: #94a3b8;
    margin-bottom: 4px;
    letter-spacing: .04em;
}

/* ---- status badges ---- */
.badge-calm {
    display: inline-block;
    background: linear-gradient(135deg, #065f46, #047857);
    color: #d1fae5;
    padding: 6px 18px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 1.05rem;
}
.badge-agitated {
    display: inline-block;
    background: linear-gradient(135deg, #991b1b, #dc2626);
    color: #fee2e2;
    padding: 6px 18px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 1.05rem;
    animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: .7; }
}

/* ---- intervention banner ---- */
.intervention-banner {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    color: #dbeafe;
    padding: 14px 22px;
    border-radius: 12px;
    font-size: 1.05rem;
    font-weight: 500;
    text-align: center;
    margin-top: 6px;
    box-shadow: 0 4px 18px rgba(37,99,235,.35);
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  SESSION STATE — agitation control
# ════════════════════════════════════════════════════════════════
if "patient_state" not in st.session_state:
    st.session_state.patient_state = "Calm"

# ════════════════════════════════════════════════════════════════
#  HEADER BAR
# ════════════════════════════════════════════════════════════════
hdr1, hdr2, hdr3 = st.columns([5, 2, 2])
with hdr1:
    st.markdown("## ⌚ Behavioural Monitor  &nbsp;·&nbsp; <span style='color:#64748b;font-size:.9rem'>Prototype</span>", unsafe_allow_html=True)
with hdr2:
    live_mode = st.toggle("🔴  Live Mode", value=False)
    if live_mode:
        st_autorefresh(interval=20000, key="refresh")
with hdr3:
    st.caption(f"🕒 {pd.Timestamp.now(tz=pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S  •  %d %b %Y')}")

st.markdown("---")

# ════════════════════════════════════════════════════════════════
#  FIREBASE INIT  (unchanged)
# ════════════════════════════════════════════════════════════════
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ════════════════════════════════════════════════════════════════
#  DATA LOADING  (unchanged — Firebase logic preserved)
# ════════════════════════════════════════════════════════════════
@st.cache_data(ttl=60)
def load_sensor_data():
    ist = pytz.timezone("Asia/Kolkata")
    start = pd.Timestamp.now(tz=ist).normalize().tz_convert("UTC")
    docs = (
        db.collection("sensor_samples")
        .where("timestamp", ">=", int(start.timestamp() * 1000))
        .limit(1200)
        .stream()
    )
    df = pd.DataFrame([d.to_dict() for d in docs])
    # ── fallback: if no data today, grab most recent docs ──
    if df.empty:
        docs_fb = (
            db.collection("sensor_samples")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(200)
            .stream()
        )
        df = pd.DataFrame([d.to_dict() for d in docs_fb])
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(ist)
    df = df.sort_values("timestamp")
    df["accelMag_smooth"] = df["accelMag"].rolling(5, min_periods=1).mean()
    return df

@st.cache_data(ttl=60)
def load_audio_data():
    ist = pytz.timezone("Asia/Kolkata")
    start = pd.Timestamp.now(tz=ist).normalize().tz_convert("UTC")
    docs = (
        db.collection("audio_samples")
        .where("timestamp", ">=", int(start.timestamp() * 1000))
        .limit(600)
        .stream()
    )
    df = pd.DataFrame([d.to_dict() for d in docs])
    # ── fallback: if no data today, grab most recent docs ──
    if df.empty:
        docs_fb = (
            db.collection("audio_samples")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(100)
            .stream()
        )
        df = pd.DataFrame([d.to_dict() for d in docs_fb])
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(ist)
    return df.sort_values("timestamp")

sensor_df = load_sensor_data()
audio_df = load_audio_data()

# ════════════════════════════════════════════════════════════════
#  HELPER — latest safe value
# ════════════════════════════════════════════════════════════════
def latest_val(df, col, fmt=".1f"):
    if df.empty or col not in df.columns:
        return "—"
    v = df[col].dropna()
    if v.empty:
        return "—"
    return f"{v.iloc[-1]:{fmt}}"

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
#  █  ROW 1 — STATUS CARDS  +  MANUAL AGITATION CONTROL
# ════════════════════════════════════════════════════════════════
st.markdown("<p class='section-header'>📊 &nbsp;STATUS OVERVIEW</p>", unsafe_allow_html=True)

r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns([1.6, 1, 1, 1, 1.4])

# ---- current state badge ----
with r1c1:
    state = st.session_state.patient_state
    if state == "Calm":
        st.markdown("<span class='badge-calm'>😌 &nbsp;Calm</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge-agitated'>⚠️ &nbsp;Agitated</span>", unsafe_allow_html=True)

# ---- KPI metrics ----
with r1c2:
    st.metric("❤️ Heart Rate", latest_val(sensor_df, "heartRate", ".0f"))

with r1c3:
    st.metric("🏃 Movement", latest_val(sensor_df, "accelMag_smooth"))

with r1c4:
    st.metric("🗣️ Speech Ratio", latest_val(audio_df, "speech_ratio", ".2f"))

# ---- agitation buttons ----
with r1c5:
    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("⚡ Trigger Agitation", use_container_width=True, type="primary"):
            st.session_state.patient_state = "Agitated"
            st.rerun()
    with bc2:
        if st.button("🔄 Reset to Calm", use_container_width=True):
            st.session_state.patient_state = "Calm"
            st.rerun()

# ---- intervention banner ----
if st.session_state.patient_state == "Agitated":
    st.markdown("""
    <div class='intervention-banner'>
        🎵 &nbsp; <b>Intervention Active</b> — Playing calming music…  &nbsp;
        🧘 Guided breathing pattern initiated
    </div>
    """, unsafe_allow_html=True)

st.markdown("")  # spacer

# ════════════════════════════════════════════════════════════════
#  █  ROW 2 — MAIN CHARTS  (Motion | Audio)
# ════════════════════════════════════════════════════════════════
st.markdown("<p class='section-header'>📈 &nbsp;LIVE SIGNALS</p>", unsafe_allow_html=True)

chart_left, chart_right = st.columns(2)

# ────────── MOTION CHART ──────────
with chart_left:
    st.markdown("##### Motion & Physiology")
    if not sensor_df.empty:
        fig_motion = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.55, 0.45],
            subplot_titles=["Acceleration (smoothed) + Gyroscope", "Heart Rate"],
        )
        # accel
        fig_motion.add_trace(
            go.Scatter(x=sensor_df["timestamp"], y=sensor_df["accelMag_smooth"],
                       name="accelMag", line=dict(color=ACCENT[0], width=2)),
            row=1, col=1,
        )
        # gyro
        for i, g in enumerate(["gyroX", "gyroY", "gyroZ"]):
            if g in sensor_df.columns:
                fig_motion.add_trace(
                    go.Scatter(x=sensor_df["timestamp"], y=sensor_df[g],
                               name=g, line=dict(color=ACCENT[i + 1], width=1.3, dash="dot")),
                    row=1, col=1,
                )
        # heart rate
        fig_motion.add_trace(
            go.Scatter(x=sensor_df["timestamp"], y=sensor_df["heartRate"],
                       name="heartRate", line=dict(color="#f87171", width=2),
                       fill="tozeroy", fillcolor="rgba(248,113,113,.12)"),
            row=2, col=1,
        )
        style_fig(fig_motion, height=420)
        fig_motion.update_annotations(font=dict(size=12, color=FONT_C))
        st.plotly_chart(fig_motion, use_container_width=True)
    else:
        st.info("Waiting for motion data…")

# ────────── AUDIO CHART ──────────
with chart_right:
    st.markdown("##### Audio Behaviour")
    AUDIO_FEATURES = ["audio_energy", "speech_ratio", "energy_variance", "pitch"]
    if not audio_df.empty:
        available = [c for c in AUDIO_FEATURES if c in audio_df.columns]
        if available:
            fig_audio = make_subplots(
                rows=len(available), cols=1,
                shared_xaxes=True,
                vertical_spacing=0.06,
                subplot_titles=available,
            )
            for idx, col in enumerate(available):
                fig_audio.add_trace(
                    go.Scatter(
                        x=audio_df["timestamp"], y=audio_df[col],
                        name=col,
                        line=dict(color=ACCENT[idx % len(ACCENT)], width=2),
                        fill="tozeroy",
                        fillcolor=f"rgba({','.join(str(int(ACCENT[idx % len(ACCENT)].lstrip('#')[j:j+2], 16)) for j in (0,2,4))}, .10)",
                    ),
                    row=idx + 1, col=1,
                )
            style_fig(fig_audio, height=420)
            fig_audio.update_annotations(font=dict(size=12, color=FONT_C))
            st.plotly_chart(fig_audio, use_container_width=True)
        else:
            st.info("No recognised audio features yet.")
    else:
        st.info("Waiting for audio data…")

# ════════════════════════════════════════════════════════════════
#  █  ROW 3 — SUPPLEMENTARY COMPACT CHARTS
# ════════════════════════════════════════════════════════════════
st.markdown("<p class='section-header'>🔎 &nbsp;SUPPLEMENTARY</p>", unsafe_allow_html=True)

bot1, bot2, bot3 = st.columns(3)

# ---- Light level ----
with bot1:
    st.markdown("###### 💡 Ambient Light")
    if not sensor_df.empty and "light" in sensor_df.columns:
        fig_light = go.Figure(go.Scatter(
            x=sensor_df["timestamp"], y=sensor_df["light"],
            line=dict(color=ACCENT[4], width=2),
            fill="tozeroy", fillcolor="rgba(251,191,36,.08)",
        ))
        style_fig(fig_light, height=200)
        st.plotly_chart(fig_light, use_container_width=True)
    else:
        st.caption("No light data")

# ---- MFCC Summary ----
with bot2:
    st.markdown("###### 🎙️ Mean MFCC (summary)")
    if not audio_df.empty:
        mfcc_cols = [c for c in audio_df.columns if c.startswith("mfcc")]
        if mfcc_cols:
            # MFCC may be stored as lists — handle both scalar and vector formats
            try:
                sample = audio_df[mfcc_cols[0]].dropna().iloc[0]
                if isinstance(sample, (list, np.ndarray)):
                    # single column holds full MFCC vector per row
                    vectors = audio_df[mfcc_cols[0]].dropna().apply(
                        lambda v: np.array(v, dtype=float)
                    )
                    mean_vec = np.mean(np.stack(vectors.values), axis=0)
                    labels = [f"mfcc_{i}" for i in range(len(mean_vec))]
                else:
                    # multiple scalar columns (mfcc_0, mfcc_1, …)
                    numeric = audio_df[mfcc_cols].apply(pd.to_numeric, errors="coerce")
                    mean_vec = numeric.mean().values
                    labels = mfcc_cols
                fig_mfcc = go.Figure(go.Bar(
                    x=labels, y=mean_vec,
                    marker_color=ACCENT[2],
                ))
                style_fig(fig_mfcc, height=200)
                fig_mfcc.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_mfcc, use_container_width=True)
            except Exception:
                st.caption("Could not parse MFCC data")
        else:
            st.caption("No MFCC data")
    else:
        st.caption("No audio data")

# ---- Recent data table ----
with bot3:
    st.markdown("###### 📋 Recent Readings")
    if not sensor_df.empty:
        tail = sensor_df[["timestamp", "accelMag_smooth", "heartRate"]].tail(6).copy()
        tail["timestamp"] = tail["timestamp"].dt.strftime("%H:%M:%S")
        tail.columns = ["Time", "Accel", "HR"]
        st.dataframe(tail, hide_index=True, use_container_width=True)
    else:
        st.caption("No sensor data yet")

# ════════════════════════════════════════════════════════════════
#  FOOTER
# ════════════════════════════════════════════════════════════════
st.markdown("""
<div style='text-align:center; color:#475569; font-size:.78rem; margin-top:2rem;'>
    Behavioural Monitor Prototype &nbsp;·&nbsp; WearOS Pipeline &nbsp;·&nbsp; Firebase Firestore
</div>
""", unsafe_allow_html=True)