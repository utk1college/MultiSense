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

def _safe_float(value, default=0.0):
    """Convert a value to float safely."""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def _coerce_bool(value):
    """Normalize boolean-like values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)

def _parse_detected_categories(raw_categories):
    """Normalize detected_categories to a list of dicts."""
    parsed = []
    if raw_categories in (None, "", []):
        return parsed

    if isinstance(raw_categories, dict):
        for category, confidence in raw_categories.items():
            category_name = str(category).strip()
            if category_name:
                parsed.append({
                    "category": category_name,
                    "confidence": _safe_float(confidence, 0.0),
                })
        return parsed

    if isinstance(raw_categories, list):
        for item in raw_categories:
            if isinstance(item, dict) and item.get("category"):
                parsed.append({
                    "category": str(item.get("category", "")).strip(),
                    "confidence": _safe_float(item.get("confidence", 0), 0.0),
                })
            elif isinstance(item, str):
                parsed.extend(_parse_detected_categories(item))
        return parsed

    if isinstance(raw_categories, str):
        chunks = [chunk.strip() for chunk in raw_categories.replace("\n", "|").split("|")]
        for chunk in chunks:
            if not chunk:
                continue
            if ":" in chunk:
                category, confidence = chunk.rsplit(":", 1)
                category_name = category.strip()
                if category_name:
                    parsed.append({
                        "category": category_name,
                        "confidence": _safe_float(confidence, 0.0),
                    })
            else:
                parsed.append({"category": chunk.strip(), "confidence": 1.0})
    return parsed

def _parse_top_keywords(raw_keywords):
    """Normalize top_keywords to a list of dicts."""
    parsed = []
    if raw_keywords in (None, "", []):
        return parsed

    if isinstance(raw_keywords, list):
        for item in raw_keywords:
            if isinstance(item, dict) and item.get("keyword"):
                parsed.append({
                    "keyword": str(item.get("keyword", "")).strip(),
                    "category": str(item.get("category", "")).strip(),
                    "confidence": _safe_float(item.get("confidence", 0), 0.0),
                })
            elif isinstance(item, str):
                parsed.extend(_parse_top_keywords(item))
        return parsed

    if isinstance(raw_keywords, str):
        text = raw_keywords
        chunks = [text]
        for sep in ["|", ";", ","]:
            if sep in text:
                chunks = [chunk.strip() for chunk in text.split(sep)]
                break

        for chunk in chunks:
            if not chunk:
                continue
            parts = [part.strip() for part in chunk.split(":") if part.strip()]
            if len(parts) >= 3:
                parsed.append({
                    "keyword": ":".join(parts[:-2]).strip(),
                    "category": parts[-2],
                    "confidence": _safe_float(parts[-1], 0.0),
                })
            elif len(parts) == 2:
                parsed.append({
                    "keyword": parts[0],
                    "category": parts[1],
                    "confidence": 1.0,
                })
            elif len(parts) == 1:
                parsed.append({
                    "keyword": parts[0],
                    "category": "",
                    "confidence": 1.0,
                })
    return parsed

def _normalize_audio_fields(df):
    """Normalize keyword/category payloads from Firestore into dashboard-friendly lists."""
    if df.empty:
        return df
    if "detected_categories" in df.columns:
        df["detected_categories"] = df["detected_categories"].apply(_parse_detected_categories)
    if "top_keywords" in df.columns:
        df["top_keywords"] = df["top_keywords"].apply(_parse_top_keywords)
    if "has_repetition" in df.columns:
        df["has_repetition"] = df["has_repetition"].apply(_coerce_bool)
    return df

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
    df = _normalize_audio_fields(df)
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
        keywords = _parse_top_keywords(data.get("top_keywords", []))
        categories = _parse_detected_categories(data.get("detected_categories", []))
        category_scores = {
            item["category"]: _safe_float(item.get("confidence", 0), 0.0)
            for item in categories
            if item.get("category")
        }
        speech_ratio = _safe_float(data.get("speech_ratio"), 0.0)
        energy = _safe_float(data.get("audio_energy"), 0.0)
        has_repetition = _coerce_bool(data.get("has_repetition", False))

        mapping = [
            ("HELP_DISTRESS", 29, "Constant unwarranted request for attention or help"),
            ("CALLING_FOR_HELP", 29, "Constant unwarranted request for attention or help"),
            ("PAIN_DISCOMFORT", 22, "Screaming"),
            ("VERBAL_AGGRESSION", 24, "Cursing or verbal aggression"),
            ("ANXIETY_DISTRESS", 24, "Cursing or verbal aggression"),
            ("NEGATIVE_STATES", 28, "Negativism"),
            ("REPETITIVE_VOCALIZATION", 25, "Repetitive sentences or questions"),
        ]

        added_items = set()
        for category_name, cmai_item, behaviour in mapping:
            category_score = category_scores.get(category_name, 0.0)
            category_keywords = [
                kw.get("keyword", "").lower()
                for kw in keywords
                if kw.get("category") == category_name and kw.get("keyword")
            ]

            if category_name == "REPETITIVE_VOCALIZATION":
                qualifies = has_repetition or category_score >= 0.6
            else:
                qualifies = category_score >= 0.6

            if not qualifies or cmai_item in added_items:
                continue

            confidence = "HIGH" if category_score >= 0.9 or (speech_ratio > 0.45 and energy > 1200) else "MEDIUM"
            alerts.append({
                "timestamp": data.get("timestamp"),
                "cmai_item": cmai_item,
                "behaviour": behaviour,
                "confidence_level": confidence,
                "transcription": data.get("transcription", ""),
                "detected_keywords": category_keywords,
                "contributing_scores": {
                    "speech": data.get("speech_detection_score", 0),
                    "acoustic": data.get("acoustic_score", 0),
                    "motion": data.get("motion_score", 0)
                }
            })
            added_items.add(cmai_item)

    df = pd.DataFrame(alerts)
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(ist)
    return df.sort_values("timestamp", ascending=False)
