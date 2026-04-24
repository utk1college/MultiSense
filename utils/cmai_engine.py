import pandas as pd

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  HELPER FUNCTIONS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def latest_val(df, col, fmt=".1f"):
    if df.empty or col not in df.columns:
        return "N/A"
    v = df[col].dropna()
    if v.empty:
        return "N/A"
    return f"{v.iloc[-1]:{fmt}}"

def _safe_float(value, default=0.0):
    """Convert to float safely."""
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
    """Parse detected_categories from list/dict form or compact watch-uploaded string form."""
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
    """Parse top_keywords from list/dict form or compact watch-uploaded string form."""
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

def safe_get_recent(df, col, window=5):
    """Safely get the latest non-null values from a column."""
    if df.empty or col not in df.columns:
        return pd.Series(dtype=float)
    return df[col].dropna().tail(window)

def extract_keyword_context(audio_df):
    """Extract keyword/category context from the latest audio sample."""
    context = {"categories": {}, "keywords": [], "has_repetition": False}
    if audio_df.empty or "timestamp" not in audio_df.columns:
        return context

    latest_row = audio_df.dropna(subset=["timestamp"]).sort_values("timestamp").iloc[-1]

    raw_categories = latest_row.get("detected_categories", [])
    for item in _parse_detected_categories(raw_categories):
        category_name = str(item.get("category", "")).strip()
        if category_name:
            context["categories"][category_name] = _safe_float(item.get("confidence", 0), 0.0)

    raw_keywords = latest_row.get("top_keywords", [])
    for item in _parse_top_keywords(raw_keywords)[:5]:
        keyword_text = str(item.get("keyword", "")).strip()
        if keyword_text:
            context["keywords"].append({
                "keyword": keyword_text,
                "category": str(item.get("category", "")).strip(),
                "confidence": _safe_float(item.get("confidence", 0), 0.0),
            })

    context["has_repetition"] = _coerce_bool(latest_row.get("has_repetition", False))
    return context

def describe_spo2(spo2_value):
    """Return a lightweight dashboard interpretation for SpO2."""
    if spo2_value is None:
        return None, None
    if spo2_value < 90:
        return "Low oxygen saturation", "#ef4444"
    if spo2_value < 94:
        return "Borderline oxygen saturation", "#f59e0b"
    return "Stable oxygen saturation", "#22c55e"

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

def safe_numeric(series):
    """Convert a series to numeric safely and drop invalid values."""
    return pd.to_numeric(series, errors="coerce").dropna()

def extract_camera_context(camera_df):
    """Extract robust camera context using only features that improve CMAI relevance."""
    context = {
        "available": False,
        "latest_hit_throw": None,
        "latest_kick": None,
        "latest_posture": None,
        "latest_wrist_speed": None,
        "latest_elbow_speed": None,
        "wrist_fast_threshold": 180.0,
        "elbow_fast_threshold": 110.0,
        "recent_transition_count": 0,
        "recent_shove_count": 0,
    }
    if camera_df.empty:
        return context

    cam = camera_df.copy()
    if "timestamp" in cam.columns:
        cam = cam.dropna(subset=["timestamp"]).sort_values("timestamp")
    if cam.empty:
        return context

    context["available"] = True
    latest_row = cam.iloc[-1]
    context["latest_hit_throw"] = str(latest_row.get("hitting/throwing", "")).strip().upper() or None
    context["latest_kick"] = str(latest_row.get("kick_detected", "")).strip().lower() or None
    context["latest_posture"] = str(latest_row.get("posture", "")).strip().upper() or None
    context["latest_wrist_speed"] = latest_row.get("wrist_speed")
    context["latest_elbow_speed"] = latest_row.get("elbow_speed")

    if "wrist_speed" in cam.columns:
        wrist_vals = safe_numeric(cam["wrist_speed"])
        if len(wrist_vals) >= 10:
            # Cap threshold floor to avoid over-sensitivity.
            context["wrist_fast_threshold"] = max(float(wrist_vals.quantile(0.90)), 150.0)

    if "elbow_speed" in cam.columns:
        elbow_vals = safe_numeric(cam["elbow_speed"])
        if len(elbow_vals) >= 10:
            context["elbow_fast_threshold"] = max(float(elbow_vals.quantile(0.90)), 90.0)

    recent = cam.tail(20)
    if "posture" in recent.columns:
        posture = recent["posture"].fillna("").astype(str).str.upper()
        context["recent_transition_count"] = int((posture == "TRANSITION").sum())
    if "pushing" in recent.columns:
        pushing = recent["pushing"].fillna("").astype(str).str.upper()
        context["recent_shove_count"] = int((pushing == "SHOVE").sum())

    return context

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  CMAI DETECTION RULES (Rule-based, no ML)
#  CALIBRATED FOR SAMSUNG GALAXY WATCH 4 MICROPHONE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def detect_cmai_behaviours(sensor_df, audio_df, camera_df=None):
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
    hr = safe_get_val(sensor_df, "heartRate")
    if hr is None:
        hr = safe_get_val(sensor_df, "heart_rate")
    gyro_mag = safe_get_val(sensor_df, "gyroMag")
    spo2 = safe_get_val(sensor_df, "spo2")

    keyword_context = extract_keyword_context(audio_df)
    keyword_categories = keyword_context["categories"]
    keyword_list = keyword_context["keywords"]
    has_repetition = keyword_context["has_repetition"]
    if camera_df is None:
        camera_df = pd.DataFrame()
    camera_context = extract_camera_context(camera_df)

    cam_hit_throw = camera_context["latest_hit_throw"]
    cam_kick = camera_context["latest_kick"] or ""
    cam_posture = camera_context["latest_posture"]
    cam_wrist = camera_context["latest_wrist_speed"]
    cam_elbow = camera_context["latest_elbow_speed"]
    cam_wrist_thresh = camera_context["wrist_fast_threshold"]
    cam_elbow_thresh = camera_context["elbow_fast_threshold"]


    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # COMPUTE BASELINE STATISTICS FOR RELATIVE DETECTION
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    energy_stats = safe_get_stats(audio_df, "audio_energy", window=10)
    pitch_stats = safe_get_stats(audio_df, "pitch", window=10)
    sc_stats = safe_get_stats(audio_df, "spectral_centroid", window=10)
    recent_speech = safe_get_recent(audio_df, "speech_ratio", window=4)
    recent_energy = safe_get_recent(audio_df, "audio_energy", window=4)
    recent_zcr = safe_get_recent(audio_df, "zcr", window=4)
    recent_flux = safe_get_recent(audio_df, "spectral_flux", window=4)
    recent_bandwidth = safe_get_recent(audio_df, "spectral_bandwidth", window=4)

    help_score = max(keyword_categories.get("HELP_DISTRESS", 0), keyword_categories.get("CALLING_FOR_HELP", 0))
    pain_score = keyword_categories.get("PAIN_DISCOMFORT", 0)
    anxiety_score = keyword_categories.get("ANXIETY_DISTRESS", 0)
    aggression_score = keyword_categories.get("VERBAL_AGGRESSION", 0)
    refusal_score = keyword_categories.get("NEGATIVE_STATES", 0)
    distress_keyword_support = max(help_score, pain_score, anxiety_score)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # AUDIO-BASED DETECTIONS (CMAI Verbal Behaviours)
    # THRESHOLDS CALIBRATED FOR WATCH MICROPHONE
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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
                "behaviour": "Screaming",
                "confidence": "HIGH",
                "evidence": f"Energy={energy:.0f}, SC={spectral_centroid:.0f}Hz, Pitch={pitch:.0f}Hz" if pitch else f"Energy={energy:.0f}, SC={spectral_centroid:.0f}Hz",
                "category": "verbal"
            })
        elif scream_indicators >= 3:
            detections.append({
                "cmai_item": 22,
                "behaviour": "Screaming",
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

        persistent_acoustic_pattern = False
        if not recent_energy.empty:
            persistent_acoustic_pattern = (recent_energy > 1000).sum() >= 2
        if not recent_zcr.empty:
            persistent_acoustic_pattern = persistent_acoustic_pattern or (recent_zcr > 0.2).sum() >= 2
        if not recent_bandwidth.empty:
            persistent_acoustic_pattern = persistent_acoustic_pattern or (recent_bandwidth > 2000).sum() >= 2

        if strange_indicators >= 4:
            # Conservative confidence policy:
            # High confidence only when acoustic anomaly is sustained and semantically supported.
            confidence = "MEDIUM"
            if distress_keyword_support >= 0.75 and persistent_acoustic_pattern and speech_ratio is not None and speech_ratio > 0.2:
                confidence = "HIGH"
            detections.append({
                "cmai_item": 26,
                "behaviour": "Strange noises (weird laughter or crying)",
                "confidence": confidence,
                "evidence": (
                    f"ZCR={zcr:.3f}, Energy={energy:.0f}, Persistent={persistent_acoustic_pattern}, "
                    f"KeywordSupport={distress_keyword_support:.2f}"
                ),
                "category": "verbal"
            })
        elif strange_indicators >= 3:  # Conservative: keep as low confidence acoustic anomaly.
            detections.append({
                "cmai_item": 26,
                "behaviour": "Strange noises (weird laughter or crying)",
                "confidence": "LOW",
                "evidence": f"Acoustic anomaly only: ZCR={zcr:.3f}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # CMAI Item 24: Verbal aggression / Agitated speech
    # IMPORTANT: REQUIRE actual aggression keywords (aggression_score > 0)
    # Don't trigger on speech+energy alone - that's just normal talking
    if aggression_score > 0 and all(v is not None for v in [energy, speech_ratio]) and energy > 1000:
        verbal_indicators = 0

        # Keyword support for aggression is the PRIMARY indicator
        if aggression_score > 0.7:
            verbal_indicators += 3  # Strong indicator
        elif aggression_score > 0.5:
            verbal_indicators += 1

        # Secondary acoustic indicators (only matter if keywords present)
        if speech_ratio > 0.5:
            verbal_indicators += 1
        if speech_ratio > 0.7:
            verbal_indicators += 1

        # Elevated energy while speaking
        if energy > 2500:
            verbal_indicators += 1
        if energy > 3500:
            verbal_indicators += 1

        # Elevated pitch
        if pitch is not None and pitch > 160:
            verbal_indicators += 1

        # High spectral centroid (tense voice)
        if spectral_centroid is not None and spectral_centroid > 2500:
            verbal_indicators += 1

        if verbal_indicators >= 4:
            detections.append({
                "cmai_item": 24,
                "behaviour": "Cursing or verbal aggression",
                "confidence": "HIGH",
                "evidence": f"Aggression={aggression_score:.2f}, Speech={speech_ratio:.0%}, Energy={energy:.0f}" + (f", Pitch={pitch:.0f}Hz" if pitch else ""),
                "category": "verbal"
            })
        elif verbal_indicators >= 3:
            detections.append({
                "cmai_item": 24,
                "behaviour": "Cursing or verbal aggression",
                "confidence": "MEDIUM",
                "evidence": f"Aggression={aggression_score:.2f}, Speech={speech_ratio:.0%}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # CMAI Item 29: Constant unwarranted request for attention or help
    if help_score >= 0.75 and speech_ratio is not None and energy is not None:
        if speech_ratio > 0.25 and energy > 700:
            help_keywords = [kw["keyword"] for kw in keyword_list if kw["category"] in {"HELP_DISTRESS", "CALLING_FOR_HELP"}]
            detections.append({
                "cmai_item": 29,
                "behaviour": "Constant unwarranted request for attention or help",
                "confidence": "HIGH",
                "evidence": f"Help score={help_score:.2f}, Speech ratio={speech_ratio:.2f}, Keywords: {', '.join(help_keywords)}",
                "category": "verbal"
            })
            detections.append({
                "cmai_item": 29,
                "behaviour": "Constant unwarranted request for attention or help",
                "confidence": "HIGH" if help_score >= 0.95 or (speech_ratio > 0.45 and energy > 1200) else "MEDIUM",
                "evidence": f"Keywords={', '.join(help_keywords[:3]) or 'help/distress'}, Speech={speech_ratio:.0%}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # CMAI Item 22: Pain/discomfort vocalization
    if pain_score >= 0.75 and speech_ratio is not None and energy is not None:
        if speech_ratio > 0.2 and energy > 650:
            pain_keywords = [kw["keyword"] for kw in keyword_list if kw["category"] == "PAIN_DISCOMFORT"]
            detections.append({
                "cmai_item": 22,
                "behaviour": "Screaming",
                "confidence": "HIGH" if pain_score >= 0.9 and energy > 1000 else "MEDIUM",
                "evidence": f"Keywords={', '.join(pain_keywords[:3]) or 'pain/discomfort'}, Speech={speech_ratio:.0%}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # CMAI Item 24: Keyword-confirmed verbal aggression or distress
    if max(anxiety_score, aggression_score) >= 0.75 and speech_ratio is not None and energy is not None:
        if speech_ratio > 0.3 and energy > 800:
            detections.append({
                "cmai_item": 24,
                "behaviour": "Cursing or verbal aggression",
                "confidence": "HIGH" if aggression_score >= 0.8 and energy > 1100 else "MEDIUM",
                "evidence": f"KeywordScore={max(anxiety_score, aggression_score):.2f}, Speech={speech_ratio:.0%}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # CMAI Item 25: Constant vocalization
    # NOTE: Removed the first detection that only checked speech_ratio
    # because arm motion creates false "speech ratio" from accelerometer noise.
    # Only detect if there's ACTUAL REPETITIVE SPEECH CONTENT (handled below)

    # CMAI Item 25: Repetitive vocalization from repeated words/phrases
    if has_repetition and speech_ratio is not None and energy is not None:
        sustained_speech = (recent_speech > 0.35).sum() >= 2 if not recent_speech.empty else False
        sustained_energy = (recent_energy > 700).sum() >= 2 if not recent_energy.empty else False
        if speech_ratio > 0.35 and energy > 500 and (sustained_speech or sustained_energy):
            detections.append({
                "cmai_item": 25,
                "behaviour": "Repetitive sentences or questions",
                "confidence": "HIGH" if speech_ratio > 0.55 else "MEDIUM",
                "evidence": f"Repeated words detected, Speech={speech_ratio:.0%}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # CMAI Item 28: Negativism
    if refusal_score >= 0.75 and speech_ratio is not None and energy is not None:
        if speech_ratio > 0.25 and energy > 700:
            detections.append({
                "cmai_item": 28,
                "behaviour": "Negativism",
                "confidence": "HIGH" if refusal_score >= 0.9 else "MEDIUM",
                "evidence": f"KeywordScore={refusal_score:.2f}, Speech={speech_ratio:.0%}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # SUDDEN SOUND DETECTION (Clapping, Banging, etc.)
    # Only detect if energy is significant (not ambient noise)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    if spectral_flux is not None and energy is not None:
        if spectral_flux > 1000 and energy > 2500:
            sustained_flux = (recent_flux > 1000).sum() >= 2 if not recent_flux.empty else False
            if sustained_flux and distress_keyword_support >= 0.75:
                flux_confidence = "MEDIUM"
            else:
                flux_confidence = "LOW"
            detections.append({
                "cmai_item": 26,
                "behaviour": "Strange noises (weird laughter or crying)",
                "confidence": flux_confidence,
                "evidence": (
                    f"Sudden acoustic onset: Flux={spectral_flux:.0f}, Energy={energy:.0f}, "
                    f"SustainedFlux={sustained_flux}, KeywordSupport={distress_keyword_support:.2f}"
                ),
                "category": "verbal"
            })

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # MOTION-BASED DETECTIONS (CMAI Physical Behaviours)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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
                    "behaviour": "Paces, aimless wandering",
                    "confidence": "MEDIUM",
                    "evidence": f"Sustained movement={accel_stats['mean']:.1f}, Ïƒ={accel_stats['std']:.2f}",
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
                            "behaviour": "Paces, aimless wandering",
                            "confidence": "MEDIUM",
                            "evidence": f"Mean={accel_stats['mean']:.1f}, Ïƒ={accel_stats['std']:.2f}, Rapid changes={high_variance_count}",
                            "category": "physical"
                        })

    # CMAI Item 20: Repetitive mannerisms (oscillatory movements - hand up/down)
    # Detection: Use gyroX to detect hand up-down oscillations
    # Get last 30 samples of gyroX and count sign changes
    # MORE SENSITIVE: Lower threshold to catch gentle hand swinging
    if "gyroX" in sensor_df.columns:
        recent_gyroX = sensor_df["gyroX"].dropna().tail(30)
        if len(recent_gyroX) >= 10:
            # RECENCY CHECK: Oscillations must be RECENT (in last 10 samples = last ~0.3 seconds)
            # If only old oscillations exist, don't trigger
            recent_10_gyroX = recent_gyroX.tail(10)
            sign_changes_recent = 0
            prev_sign = None
            for val in recent_10_gyroX:
                if val is not None and val != 0:
                    current_sign = 1 if val > 0 else -1
                    if prev_sign is not None and current_sign != prev_sign:
                        sign_changes_recent += 1
                    prev_sign = current_sign

            # Also count in all 30 to ensure sustained oscillation
            sign_changes = 0
            prev_sign = None
            for val in recent_gyroX:
                if val is not None and val != 0:
                    current_sign = 1 if val > 0 else -1
                    if prev_sign is not None and current_sign != prev_sign:
                        sign_changes += 1
                    prev_sign = current_sign

            # Movement variance check - even gentle motion should create variance
            accel_stats = safe_get_stats(sensor_df, "accelMag_smooth", window=30)
            # Require SIGNIFICANT movement variance - normal sitting/breathing won't trigger
            # std > 2.0 = obvious active motion (swinging, hitting, etc)
            has_significant_movement = accel_stats["available"] and accel_stats["std"] > 2.0

            # CRITICAL: Require RECENT oscillations (last 10 samples) + sustained pattern (all 30 samples)
            # This prevents stale detections from hanging around
            # Many sign changes = oscillatory motion (hand up/down)
            # MEDIUM confidence: 5+ recent changes (needs CLEAR recency), 8+ total changes with STRONG movement
            if sign_changes_recent >= 5 and sign_changes >= 8 and has_significant_movement:
                detections.append({
                    "cmai_item": 20,
                    "behaviour": "Performing repetitious mannerisms",
                    "confidence": "MEDIUM",
                    "evidence": f"Gyro oscillations={sign_changes}/30 (recent={sign_changes_recent}), σ_Move={accel_stats['std']:.2f}",
                    "category": "physical"
                })
            # HIGH confidence: 7+ recent changes (very active now), 12+ total changes with STRONG movement
            elif sign_changes_recent >= 7 and sign_changes >= 12 and has_significant_movement:
                detections.append({
                    "cmai_item": 20,
                    "behaviour": "Performing repetitious mannerisms",
                    "confidence": "HIGH",
                    "evidence": f"Gyro oscillations={sign_changes}/30 (recent={sign_changes_recent}), σ_Move={accel_stats['std']:.2f}",
                    "category": "physical"
                })

    # CMAI Item 21: General restlessness
    # Research basis: High movement + elevated HR + high variance
    if all(v is not None for v in [accel, hr]):
        accel_stats = safe_get_stats(sensor_df, "accelMag_smooth", window=20)
        hr_stats = safe_get_stats(sensor_df, "heartRate", window=20)
        if not hr_stats["available"]:
            hr_stats = safe_get_stats(sensor_df, "heart_rate", window=20)
        if accel_stats["available"] and hr_stats["available"]:
            hr_delta = hr_stats["current"] - hr_stats["mean"]
            if accel_stats["mean"] > 15 and accel_stats["std"] > 5 and (hr_stats["current"] > 90 or hr_delta > 8):
                detections.append({
                    "cmai_item": 21,
                    "behaviour": "General restlessness",
                    "confidence": "MEDIUM",
                    "evidence": f"Move={accel_stats['mean']:.1f}Â±{accel_stats['std']:.1f}, HR={hr_stats['current']:.0f}",
                    "category": "physical"
                })


    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # COMPOSITE DETECTIONS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    # Camera-assisted detections (fused with audio/sensor corroboration)
    if camera_context["available"]:
        accel_stats_cam = safe_get_stats(sensor_df, "accelMag_smooth", window=20)
        has_motion_variability = accel_stats_cam["available"] and accel_stats_cam["std"] > 1.5

        cam_fast_wrist = cam_wrist is not None and pd.notna(cam_wrist) and cam_wrist >= cam_wrist_thresh
        cam_fast_elbow = cam_elbow is not None and pd.notna(cam_elbow) and cam_elbow >= cam_elbow_thresh
        cam_impact_label = cam_hit_throw in {"HIT", "THROW"}
        cam_kick_flag = "kick" in cam_kick
        cam_shove_flag = camera_context["recent_shove_count"] > 0

        # Camera-derived physical behaviours mapped to exact CMAI form items.
        # IMPORTANT: Require actual camera detection OR very high motion corroboration
        if cam_impact_label or cam_kick_flag or cam_shove_flag:
            corroborators = 0
            if cam_fast_wrist:
                corroborators += 1
            if cam_fast_elbow:
                corroborators += 1
            if accel is not None and accel > 12.5:
                corroborators += 1
            if has_motion_variability and accel_stats_cam["std"] > 3.0:
                corroborators += 1
            if energy is not None and energy > 1500:
                corroborators += 1

            # STRICTER: If NO camera detection label, need VERY high motion + energy
            required_corroborators = 2 if cam_impact_label else 4
            if (cam_kick_flag and corroborators >= 2) or corroborators >= required_corroborators:
                wrist_str = f"{cam_wrist:.1f}" if cam_wrist is not None and pd.notna(cam_wrist) else "N/A"
                elbow_str = f"{cam_elbow:.1f}" if cam_elbow is not None and pd.notna(cam_elbow) else "N/A"
                if cam_kick_flag:
                    cam_item = 2
                    cam_behaviour = "Kicking"
                elif cam_shove_flag:
                    cam_item = 4
                    cam_behaviour = "Pushing"
                elif cam_hit_throw == "HIT":
                    cam_item = 1
                    cam_behaviour = "Hitting (including self)"
                else:
                    cam_item = 5
                    cam_behaviour = "Throwing things"
                detections.append({
                    "cmai_item": cam_item,
                    "behaviour": cam_behaviour,
                    "confidence": "HIGH" if corroborators >= 4 else "MEDIUM",
                    "evidence": (
                        f"Vision={cam_hit_throw or 'N/A'}/{cam_kick or 'N/A'}, "
                        f"Wrist={wrist_str}, Elbow={elbow_str}, corroborators={corroborators}"
                    ),
                    "category": "physical"
                })

        # CMAI 21: camera-confirmed restlessness/transitions
        transition_active = (cam_posture == "TRANSITION") or (camera_context["recent_transition_count"] >= 4)
        if transition_active:
            transition_support = 0
            if has_motion_variability:
                transition_support += 1
            if hr is not None and hr > 95:
                transition_support += 1
            if cam_fast_wrist or cam_fast_elbow:
                transition_support += 1
            if accel is not None and accel > 11.0:
                transition_support += 1

            if transition_support >= 3:
                detections.append({
                    "cmai_item": 21,
                    "behaviour": "General restlessness",
                    "confidence": "MEDIUM",
                    "evidence": (
                        f"Posture={cam_posture or 'N/A'}, transitions20={camera_context['recent_transition_count']}, "
                        f"support={transition_support}"
                    ),
                    "category": "physical"
                })

    # Combined agitation indicator (high arousal state)
    # STRICTER: Require actual distress signals, not just motion
    arousal_indicators = 0
    distress_keywords_present = (help_score > 0 or pain_score > 0 or anxiety_score > 0 or aggression_score > 0)
    
    # Only count audio/physiological if distress keywords are present
    if distress_keywords_present:
        if energy is not None and energy > 2500:
            arousal_indicators += 1
        if pitch is not None and pitch > 200:
            arousal_indicators += 1
    else:
        # Without keywords, require MUCH higher thresholds (genuine distress, not just movement)
        if energy is not None and energy > 3500:
            arousal_indicators += 1
        if pitch is not None and pitch > 300:
            arousal_indicators += 1
    
    if accel is not None and accel > 16:
        arousal_indicators += 1
    if hr is not None and hr > 110:  # Much higher threshold
        arousal_indicators += 1
    if spo2 is not None and spo2 < 90:  # More critical threshold
        arousal_indicators += 1
    if camera_context["available"]:
        cam_fast_wrist = cam_wrist is not None and pd.notna(cam_wrist) and cam_wrist >= cam_wrist_thresh
        cam_fast_elbow = cam_elbow is not None and pd.notna(cam_elbow) and cam_elbow >= cam_elbow_thresh
        # Only count if BOTH wrist and elbow are fast, not just one
        if (cam_fast_wrist and cam_fast_elbow) or (cam_posture == "TRANSITION" and distress_keywords_present):
            arousal_indicators += 1

    # STRICTER: Require at least 4 indicators AND either keywords or camera confirmation
    if arousal_indicators >= 4 and (distress_keywords_present or camera_context["available"]):
        detections.append({
            "cmai_item": 0,
            "behaviour": "High arousal state",
            "confidence": "HIGH",
            "evidence": f"{arousal_indicators}/6 indicators elevated",
            "category": "composite"
        })

    return detections


