import pandas as pd

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
    if isinstance(raw_categories, list):
        for item in raw_categories:
            if isinstance(item, dict) and item.get("category"):
                try:
                    context["categories"][str(item["category"])] = float(item.get("confidence", 0) or 0)
                except (TypeError, ValueError):
                    context["categories"][str(item["category"])] = 0.0

    raw_keywords = latest_row.get("top_keywords", [])
    if isinstance(raw_keywords, list):
        for item in raw_keywords[:5]:
            if isinstance(item, dict) and item.get("keyword"):
                context["keywords"].append({
                    "keyword": str(item.get("keyword", "")),
                    "category": str(item.get("category", "")),
                    "confidence": float(item.get("confidence", 0) or 0),
                })

    context["has_repetition"] = bool(latest_row.get("has_repetition", False))
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
    hr = safe_get_val(sensor_df, "heartRate")
    if hr is None:
        hr = safe_get_val(sensor_df, "heart_rate")
    gyro_mag = safe_get_val(sensor_df, "gyroMag")
    spo2 = safe_get_val(sensor_df, "spo2")

    keyword_context = extract_keyword_context(audio_df)
    keyword_categories = keyword_context["categories"]
    keyword_list = keyword_context["keywords"]
    has_repetition = keyword_context["has_repetition"]


    # ═══════════════════════════════════════════════════════════
    # COMPUTE BASELINE STATISTICS FOR RELATIVE DETECTION
    # ═══════════════════════════════════════════════════════════
    energy_stats = safe_get_stats(audio_df, "audio_energy", window=10)
    pitch_stats = safe_get_stats(audio_df, "pitch", window=10)
    sc_stats = safe_get_stats(audio_df, "spectral_centroid", window=10)
    recent_speech = safe_get_recent(audio_df, "speech_ratio", window=4)
    recent_energy = safe_get_recent(audio_df, "audio_energy", window=4)

    help_score = max(keyword_categories.get("HELP_DISTRESS", 0), keyword_categories.get("CALLING_FOR_HELP", 0))
    pain_score = keyword_categories.get("PAIN_DISCOMFORT", 0)
    anxiety_score = keyword_categories.get("ANXIETY_DISTRESS", 0)
    aggression_score = keyword_categories.get("VERBAL_AGGRESSION", 0)
    refusal_score = keyword_categories.get("NEGATIVE_STATES", 0)

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

    # CMAI Item 27: Calling out / calling for help
    if help_score >= 0.75 and speech_ratio is not None and energy is not None:
        if speech_ratio > 0.25 and energy > 700:
            help_keywords = [kw["keyword"] for kw in keyword_list if kw["category"] in {"HELP_DISTRESS", "CALLING_FOR_HELP"}]
            detections.append({
                "cmai_item": 27,
                "behaviour": "Calling Out / Calling for Help",
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
                "behaviour": "Pain / Discomfort Vocalization",
                "confidence": "HIGH" if pain_score >= 0.9 and energy > 1000 else "MEDIUM",
                "evidence": f"Keywords={', '.join(pain_keywords[:3]) or 'pain/discomfort'}, Speech={speech_ratio:.0%}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # CMAI Item 24: Keyword-confirmed verbal aggression or distress
    if max(anxiety_score, aggression_score) >= 0.75 and speech_ratio is not None and energy is not None:
        if speech_ratio > 0.3 and energy > 800:
            detections.append({
                "cmai_item": 24,
                "behaviour": "Verbal Aggression" if aggression_score >= anxiety_score else "Anxious / Distressed Speech",
                "confidence": "HIGH" if aggression_score >= 0.8 and energy > 1100 else "MEDIUM",
                "evidence": f"KeywordScore={max(anxiety_score, aggression_score):.2f}, Speech={speech_ratio:.0%}, Energy={energy:.0f}",
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

    # CMAI Item 25: Repetitive vocalization from repeated words/phrases
    if has_repetition and speech_ratio is not None and energy is not None:
        sustained_speech = (recent_speech > 0.35).sum() >= 2 if not recent_speech.empty else False
        sustained_energy = (recent_energy > 700).sum() >= 2 if not recent_energy.empty else False
        if speech_ratio > 0.35 and energy > 500 and (sustained_speech or sustained_energy):
            detections.append({
                "cmai_item": 25,
                "behaviour": "Repetitive Vocalization",
                "confidence": "HIGH" if speech_ratio > 0.55 else "MEDIUM",
                "evidence": f"Repeated words detected, Speech={speech_ratio:.0%}, Energy={energy:.0f}",
                "category": "verbal"
            })

    # CMAI Item 26: Negativism / refusal speech
    if refusal_score >= 0.75 and speech_ratio is not None and energy is not None:
        if speech_ratio > 0.25 and energy > 700:
            detections.append({
                "cmai_item": 26,
                "behaviour": "Negativism / Refusal",
                "confidence": "HIGH" if refusal_score >= 0.9 else "MEDIUM",
                "evidence": f"KeywordScore={refusal_score:.2f}, Speech={speech_ratio:.0%}, Energy={energy:.0f}",
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
    # STRICTER: Requires BOTH high oscillation AND elevated acceleration
    if "gyroX" in sensor_df.columns:
        recent_gyroX = sensor_df["gyroX"].dropna().tail(30)
        if len(recent_gyroX) >= 10:
            # Count sign changes directly in gyroX values (not deltas)
            # Ignore micro-movements like typing by requiring at least 0.5 rad/s
            sign_changes = 0
            prev_sign = None
            for val in recent_gyroX:
                if val is not None and abs(val) > 0.5:
                    current_sign = 1 if val > 0 else -1
                    if prev_sign is not None and current_sign != prev_sign:
                        sign_changes += 1
                    prev_sign = current_sign

            # STRICTER: Require BOTH oscillation AND elevated movement variance
            accel_stats = safe_get_stats(sensor_df, "accelMag_smooth", window=30)
            # accelMag includes gravity (~9.8), so mean > 8 is always true. We check standard deviation instead.
            has_elevated_movement = accel_stats["available"] and accel_stats["std"] > 1.0

            # Many sign changes = oscillatory motion (hand up/down)
            # HIGH confidence: 20+ sign changes (very rapid) AND elevated movement
            if sign_changes >= 20 and has_elevated_movement:
                detections.append({
                    "cmai_item": 20,
                    "behaviour": "Repetitive Mannerisms (Hand Oscillation)",
                    "confidence": "HIGH",
                    "evidence": f"Gyro oscillations={sign_changes}/30, σ_Move={accel_stats['std']:.2f}",
                    "category": "physical"
                })
            # MEDIUM confidence: 16-19 sign changes AND elevated movement
            elif sign_changes >= 16 and has_elevated_movement:
                detections.append({
                    "cmai_item": 20,
                    "behaviour": "Repetitive Mannerisms (Hand Oscillation)",
                    "confidence": "MEDIUM",
                    "evidence": f"Gyro oscillations={sign_changes}/30, σ_Move={accel_stats['std']:.2f}",
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
    if spo2 is not None and spo2 < 92:
        arousal_indicators += 1

    if arousal_indicators >= 3:
        detections.append({
            "cmai_item": 0,
            "behaviour": "High arousal state",
            "confidence": "HIGH",
            "evidence": f"{arousal_indicators}/5 indicators elevated",
            "category": "composite"
        })

    return detections

