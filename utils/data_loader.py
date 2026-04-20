import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import FieldFilter
import pandas as pd
import pytz

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
@st.cache_data(ttl=30)
def load_sensor_data(_live_mode):
    """Load sensor/motion data from audio_samples (motion data) + sensor_samples (gyro data)."""
    ist = pytz.timezone("Asia/Kolkata")
    start = pd.Timestamp.now(tz=ist).normalize().tz_convert("UTC")

    limit = 200 if _live_mode else 100

    # Load motion data from audio_samples
    docs = (
        db.collection("audio_samples")
        .where(filter=FieldFilter("timestamp", ">=", int(start.timestamp() * 1000)))
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
        .where(filter=FieldFilter("timestamp", ">=", int(start.timestamp() * 1000)))
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

        if "spO2" in gyro_df.columns and "spo2" not in gyro_df.columns:
            gyro_df["spo2"] = gyro_df["spO2"]
        if "bloodOxygen" in gyro_df.columns and "spo2" not in gyro_df.columns:
            gyro_df["spo2"] = gyro_df["bloodOxygen"]
        if "oxygenSaturation" in gyro_df.columns and "spo2" not in gyro_df.columns:
            gyro_df["spo2"] = gyro_df["oxygenSaturation"]

        # Keep sensor_samples data (already correctly named: gyroX, gyroY, gyroZ, heartRate, accelMag)
        sensor_cols = ["timestamp", "gyroX", "gyroY", "gyroZ", "heartRate", "accelMag", 
                       "light", "spo2", "spo2_sdk_available", "spo2_connected", 
                       "spo2_status", "spo2_supported"]
        sensor_cols = [c for c in sensor_cols if c in gyro_df.columns]  # Only keep columns that exist

        # Merge on timestamp. Use gyro_df (sensor_samples) as primary because it's denser 
        # and has SpO2. We don't want to drop SpO2 just because an audio cycle didn't trigger.
        if not df.empty:
            df = pd.merge_asof(
                gyro_df[sensor_cols].sort_values("timestamp"),
                df.sort_values("timestamp").drop(columns=["spo2", "light", "gyroX", "gyroY", "gyroZ"], errors="ignore"),
                on="timestamp",
                direction="nearest",
                tolerance=pd.Timedelta("15s"),
                suffixes=("_sensor", "_audio")
            )
            # Prefer sensor_samples data, but fall back to audio_samples summary values
            # when the timestamp merge misses and the sensor-side fields are null.
            if "heartRate" in df.columns and "heart_rate" in df.columns:
                df["heartRate"] = df["heartRate"].combine_first(df["heart_rate"])
            elif "heart_rate" in df.columns:
                df["heartRate"] = df["heart_rate"]

            if "accelMag_sensor" in df.columns and "accelMag_audio" in df.columns:
                df["accelMag"] = df["accelMag_sensor"].combine_first(df["accelMag_audio"])
                df = df.drop(columns=["accelMag_sensor", "accelMag_audio"])
            elif "accelMag_sensor" in df.columns:
                df["accelMag"] = df["accelMag_sensor"]
                df = df.drop(columns=["accelMag_sensor"])

            df = df.drop(columns=[c for c in ["heart_rate", "accel_magnitude"] if c in df.columns])
        else:
            # If no audio data, use sensor data as the base
            df = gyro_df[sensor_cols].copy()

    # Smooth acceleration (after merge to use sensor data)
    if not df.empty and "accelMag" in df.columns:
        df["accelMag_smooth"] = df["accelMag"].rolling(5, min_periods=1).mean()

    return df.sort_values("timestamp") if not df.empty else df

@st.cache_data(ttl=30)
def load_audio_data(_live_mode):
    """Load audio data with Firebase quota optimization."""
    ist = pytz.timezone("Asia/Kolkata")
    start = pd.Timestamp.now(tz=ist).normalize().tz_convert("UTC")

    limit = 100 if _live_mode else 50

    docs = (
        db.collection("audio_samples")
        .where(filter=FieldFilter("timestamp", ">=", int(start.timestamp() * 1000)))
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

@st.cache_data(ttl=30)
def load_camera_data(_live_mode):
    """Load camera/vision data from camera_samples."""
    ist = pytz.timezone("Asia/Kolkata")
    start = pd.Timestamp.now(tz=ist).normalize().tz_convert("UTC")

    limit = 100 if _live_mode else 50

    docs = (
        db.collection("camera_samples")
        .where(filter=FieldFilter("timestamp", ">=", int(start.timestamp() * 1000)))
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    df = pd.DataFrame([d.to_dict() for d in docs])

    if df.empty:
        docs_fb = (
            db.collection("camera_samples")
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
        .where(filter=FieldFilter("timestamp", ">=", int(start.timestamp() * 1000)))
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
