import streamlit as st
from streamlit_autorefresh import st_autorefresh
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import plotly.express as px
import pytz

# ---------------- PAGE ----------------
st.set_page_config(layout="wide")
st.title("WearOS Behaviour Monitoring")

live_mode = st.toggle("Live Dashboard Mode", value=False)
if live_mode:
    st_autorefresh(interval=20000, key="refresh")

# ---------------- FIREBASE ----------------
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- BASELINE STORAGE ----------------
@st.cache_data(ttl=3600)
def load_baseline_from_firestore():
    doc = db.collection("baseline_profile").document("user_baseline").get()
    if doc.exists:
        return pd.Series(doc.to_dict()["values"])
    return None

def save_baseline_to_firestore(series):
    db.collection("baseline_profile").document("user_baseline").set(
        {"values": series.to_dict()}
    )

saved_baseline = load_baseline_from_firestore()

# ---------------- SHOW SAVED BASELINE ----------------
if saved_baseline is not None:
    st.subheader("Saved Personal Baseline")

    baseline_df = pd.DataFrame(saved_baseline, columns=["Baseline Value"])
    st.dataframe(baseline_df)

    st.success("Baseline loaded from Firebase — monitoring mode active")
else:
    st.warning("No baseline saved yet — system will learn one.")


# ---------------- LOAD TODAY DATA (LOW READS) ----------------
@st.cache_data(ttl=60)
def load_sensor_data():
    ist = pytz.timezone("Asia/Kolkata")
    start = pd.Timestamp.now(tz=ist).normalize().tz_convert("UTC")
    docs = (
        db.collection("sensor_samples")
        .where("timestamp", ">=", int(start.timestamp()*1000))
        .limit(1200)                 # 🔥 read cap
        .stream()
    )
    df = pd.DataFrame([d.to_dict() for d in docs])
    if df.empty: return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(ist)
    df = df.sort_values("timestamp")
    df["accelMag_smooth"] = df["accelMag"].rolling(5,min_periods=1).mean()
    return df

@st.cache_data(ttl=60)
def load_audio_data():
    ist = pytz.timezone("Asia/Kolkata")
    start = pd.Timestamp.now(tz=ist).normalize().tz_convert("UTC")
    docs = (
        db.collection("audio_samples")
        .where("timestamp", ">=", int(start.timestamp()*1000))
        .limit(600)                  # 🔥 read cap
        .stream()
    )
    df = pd.DataFrame([d.to_dict() for d in docs])
    if df.empty: return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(ist)
    return df.sort_values("timestamp")

sensor_df = load_sensor_data()
audio_df = load_audio_data()

# ---------------- VISUALISE SENSORS ----------------
st.subheader("Motion + Physiology")

if not sensor_df.empty:
    st.plotly_chart(px.line(sensor_df,x="timestamp",y="accelMag_smooth"))
    if {"gyroX","gyroY","gyroZ"}.issubset(sensor_df.columns):
        st.plotly_chart(px.line(sensor_df,x="timestamp",y=["gyroX","gyroY","gyroZ"]))
    st.plotly_chart(px.line(sensor_df,x="timestamp",y="heartRate"))
    st.plotly_chart(px.line(sensor_df,x="timestamp",y="light"))

# ---------------- VISUALISE AUDIO ----------------
st.subheader("Audio Behaviour")

audio_cols=["audio_energy","audio_silence_ratio","audio_zcr",
            "speech_ratio","energy_variance","high_freq_ratio"]

if not audio_df.empty:
    for col in audio_cols:
        if col in audio_df.columns:
            st.plotly_chart(px.line(audio_df,x="timestamp",y=col))

# ---------------- MERGE STREAMS ----------------
merged=None
if not sensor_df.empty:
    merged=sensor_df.copy()
    if not audio_df.empty:
        merged=pd.merge_asof(audio_df.sort_values("timestamp"),
                             sensor_df.sort_values("timestamp"),
                             on="timestamp",direction="nearest",
                             tolerance=pd.Timedelta("10s"))

# ---------------- BEHAVIOUR WINDOWS ----------------
def compute_windows(df):
    if df is None or df.empty: return pd.DataFrame()
    df=df.set_index("timestamp")
    win=pd.DataFrame()
    win["movement_mean"]=df["accelMag_smooth"].resample("5min").mean()
    win["movement_std"]=df["accelMag_smooth"].resample("5min").std()
    win["movement_burst"]=df["accelMag_smooth"].resample("5min").apply(
        lambda s:(s>s.mean()+2*s.std()).sum() if len(s)>1 else 0)
    win["hr_mean"]=df["heartRate"].resample("5min").mean()
    if "audio_energy" in df: win["audio_energy"]=df["audio_energy"].resample("5min").mean()
    if "speech_ratio" in df: win["speech_ratio"]=df["speech_ratio"].resample("5min").mean()
    if "energy_variance" in df: win["audio_var"]=df["energy_variance"].resample("5min").mean()
    if "light" in df: win["light_mean"]=df["light"].resample("5min").mean()
    return win.ffill().bfill().reset_index()

behavior_df=compute_windows(merged)

# ---------------- BASELINE + ALS ----------------
if saved_baseline is None and len(behavior_df)>=3:
    st.info("Learning baseline...")
    baseline=behavior_df.median(numeric_only=True)
    save_baseline_to_firestore(baseline)
    st.success("Baseline saved!")
else:
    baseline=saved_baseline

def rel(a,b): return max(0,(a-b)/b) if b else 0

def compute_als(row):

    def safe_rel(a, b):
        if pd.isna(a) or pd.isna(b) or b == 0:
            return 0
        return max(0, (a - b) / b)

    # ----- MOTOR -----
    motor = min(1,
        0.35 * safe_rel(row.get("movement_mean", 0), baseline.get("movement_mean", 0)) +
        0.35 * safe_rel(row.get("movement_std", 0), baseline.get("movement_std", 0)) +
        0.30 * safe_rel(row.get("movement_burst", 0), baseline.get("movement_burst", 0))
    )

    # ----- HEART -----
    heart = min(1, max(0,
        (row.get("hr_mean", 0) - baseline.get("hr_mean", 0)) / 15
    ))

    # ----- AUDIO (SAFE) -----
    audio = 0
    if all(k in row for k in ["speech_ratio", "audio_energy", "audio_var"]) and \
       all(k in baseline for k in ["speech_ratio", "audio_energy", "audio_var"]):

        audio = min(1,
            0.40 * safe_rel(row["speech_ratio"], baseline["speech_ratio"]) +
            0.30 * safe_rel(row["audio_energy"], baseline["audio_energy"]) +
            0.30 * safe_rel(row["audio_var"], baseline["audio_var"])
        )

    # ----- CONTEXT -----
    context = min(1,
        safe_rel(row.get("light_mean", 0), baseline.get("light_mean", 0))
    )

    return 0.35*motor + 0.30*audio + 0.25*heart + 0.10*context

# ---------------- ALS COMPUTATION & DISPLAY ----------------
if saved_baseline is not None and behavior_df is not None and len(behavior_df) > 0:

    # compute ALS
    behavior_df["ALS"] = behavior_df.apply(compute_als, axis=1)

    # smoothing
    behavior_df["ALS"] = behavior_df["ALS"].rolling(3, min_periods=1).mean()

    # state label
    def agitation_state(score):
        if score < 0.2:
            return "Calm"
        elif score < 0.4:
            return "Elevated"
        elif score < 0.7:
            return "Agitated"
        else:
            return "High Agitation"

    behavior_df["State"] = behavior_df["ALS"].apply(agitation_state)

    # ---- VISUALS ----
    st.subheader("Agitation Timeline")
    st.line_chart(behavior_df.set_index("timestamp")["ALS"])

    latest = behavior_df.iloc[-1]

    c1, c2 = st.columns(2)
    c1.metric("Current ALS", f"{latest['ALS']:.2f}")
    c2.metric("State", latest["State"])