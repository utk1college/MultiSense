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

from utils.data_loader import load_sensor_data, load_audio_data, load_camera_data, load_cmai_detections
from utils.cmai_engine import detect_cmai_behaviours, safe_get_val, safe_get_recent, describe_spo2, latest_val
from utils.ui_helpers import inject_custom_css, style_fig, ACCENT, FONT_C

# ════════════════════════════════════════════════════════════════
#  PAGE CONFIG & CUSTOM CSS
# ════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Behavioural Monitor — Prototype",
    page_icon="⌚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_custom_css()

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


# Load data
sensor_df = load_sensor_data(live_mode)
audio_df = load_audio_data(live_mode)
camera_df = load_camera_data(live_mode)
cmai_df = load_cmai_detections(live_mode)

# Update cache
st.session_state.cached_sensor_df = sensor_df
st.session_state.cached_audio_df = audio_df
st.session_state.last_fetch_time = datetime.now()


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
tab_dashboard, tab_unified, tab_cmai, tab_audio = st.tabs(["📊 Live Dashboard", "🔄 Unified Data", "🧠 CMAI Detection", "🎵 Audio Analysis"])

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
        spo2_display = latest_val(sensor_df, "spo2", ".0f")
        if spo2_display != "—":
            st.metric("SpO2", f"{spo2_display}%")
        else:
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

    bot1, bot2, bot3 = st.columns(3)

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

    with bot3:
        st.markdown("###### 🩸 SpO2 Analysis")
        latest_spo2 = safe_get_val(sensor_df, "spo2")
        if latest_spo2 is not None:
            spo2_label, spo2_color = describe_spo2(latest_spo2)
            st.metric("SpO2", f"{latest_spo2:.0f}%")
            st.markdown(
                f"<div style='padding:10px 12px; border-radius:8px; background: rgba(30,30,47,0.6); "
                f"border-left: 4px solid {spo2_color}; margin-bottom: 10px;'>{spo2_label}</div>",
                unsafe_allow_html=True,
            )
            spo2_recent = safe_get_recent(sensor_df, "spo2", window=30)
            if not spo2_recent.empty and len(spo2_recent) > 1:
                spo2_ts = sensor_df.loc[spo2_recent.index, "timestamp"]
                fig_spo2 = go.Figure()
                fig_spo2.add_trace(go.Scatter(
                    x=spo2_ts,
                    y=spo2_recent,
                    name="SpO2",
                    line=dict(color=ACCENT[3], width=2),
                    mode="lines+markers",
                ))
                fig_spo2.add_hline(y=94, line_dash="dot", line_color="#f59e0b")
                fig_spo2.add_hline(y=90, line_dash="dot", line_color="#ef4444")
                fig_spo2.update_yaxes(range=[min(85, spo2_recent.min() - 1), max(100, spo2_recent.max() + 1)])
                style_fig(fig_spo2, height=180)
                st.plotly_chart(fig_spo2, width='stretch')
            else:
                st.caption("Waiting for more SpO2 samples")
        else:
            # Show diagnostics if the watch is uploading status fields
            sdk_avail = safe_get_val(sensor_df, "spo2_sdk_available")
            connected = safe_get_val(sensor_df, "spo2_connected")
            supported = safe_get_val(sensor_df, "spo2_supported")
            status = safe_get_val(sensor_df, "spo2_status")

            if sdk_avail is not None:
                st.info(
                    f"SpO2 not measured yet. Diagnostics: "
                    f"sdk_available={sdk_avail}, connected={connected}, supported={supported}, status={status}"
                )
                if not bool(sdk_avail):
                    st.caption("To enable SpO2 on Galaxy Watch, add Samsung Health Sensor SDK .aar into the watch app's app/libs/ folder and rebuild.")
                elif connected is False:
                    st.caption("Samsung Health sensor service not connected yet. Ensure Samsung Health is installed/available on the watch and reopen the app.")
                elif supported is False:
                    st.caption("This watch does not report SPO2_ON_DEMAND via Samsung SDK (model/firmware dependent).")
                else:
                    st.caption("SpO2 measurement requested; waiting for completion.")
            else:
                st.caption("No SpO2 data from watch yet")


# ════════════════════════════════════════════════════════════════
#  TAB 2: UNIFIED DATA (Multi-source integration)
# ════════════════════════════════════════════════════════════════
with tab_unified:
    st.markdown("## 🔄 Unified Multi-Source Data")

    # Extract patient ID (should be same across all sources)
    patient_id = "—"
    if not sensor_df.empty and "patient_id" in sensor_df.columns:
        pid_vals = sensor_df["patient_id"].dropna().unique()
        if len(pid_vals) > 0:
            patient_id = pid_vals[0]
    elif not audio_df.empty and "patient_id" in audio_df.columns:
        pid_vals = audio_df["patient_id"].dropna().unique()
        if len(pid_vals) > 0:
            patient_id = pid_vals[0]
    elif not camera_df.empty and "patient_id" in camera_df.columns:
        pid_vals = camera_df["patient_id"].dropna().unique()
        if len(pid_vals) > 0:
            patient_id = pid_vals[0]

    # Display patient ID prominently
    st.markdown(f"**Patient ID:** `{patient_id}`", help="Unique patient identifier across all data sources")

    st.markdown("""
    <div class='research-note'>
        <strong>Multi-Source Integration</strong>: View synchronized data from sensor, camera, and audio sources grouped by recording cycle.
        All timestamps and cycle IDs are aligned for cross-modal analysis.
    </div>
    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # UNIFIED SUMMARY BY CYCLE
    # ════════════════════════════════════════════════════════════════
    st.markdown("<p class='section-header'>📋 &nbsp;CYCLE SUMMARY</p>", unsafe_allow_html=True)

    # Collect all cycle_ids from all three sources
    all_cycles = set()
    if not sensor_df.empty and "cycle_id" in sensor_df.columns:
        all_cycles.update(sensor_df["cycle_id"].dropna().unique())
    if not audio_df.empty and "cycle_id" in audio_df.columns:
        all_cycles.update(audio_df["cycle_id"].dropna().unique())
    if not camera_df.empty and "cycle_id" in camera_df.columns:
        all_cycles.update(camera_df["cycle_id"].dropna().unique())

    if all_cycles:
        # Sort cycles descending (newest first)
        sorted_cycles = sorted(all_cycles, reverse=True)

        # Display cycle summary table
        cycle_summary = []
        for cycle_id in sorted_cycles[:10]:  # Show last 10 cycles
            sensor_count = len(sensor_df[sensor_df["cycle_id"] == cycle_id]) if not sensor_df.empty else 0
            audio_count = len(audio_df[audio_df["cycle_id"] == cycle_id]) if not audio_df.empty else 0
            camera_count = len(camera_df[camera_df["cycle_id"] == cycle_id]) if not camera_df.empty else 0

            # Get latest data from each source for this cycle
            sensor_ts = sensor_df[sensor_df["cycle_id"] == cycle_id]["timestamp"].max() if sensor_count > 0 else None
            audio_ts = audio_df[audio_df["cycle_id"] == cycle_id]["timestamp"].max() if audio_count > 0 else None
            camera_ts = camera_df[camera_df["cycle_id"] == cycle_id]["timestamp"].max() if camera_count > 0 else None

            latest_hr = None
            if sensor_count > 0 and "heartRate" in sensor_df.columns:
                hr_vals = sensor_df[sensor_df["cycle_id"] == cycle_id]["heartRate"].dropna()
                if not hr_vals.empty:
                    latest_hr = f"{hr_vals.iloc[-1]:.0f}"

            latest_posture = None
            if camera_count > 0 and "posture" in camera_df.columns:
                posture_vals = camera_df[camera_df["cycle_id"] == cycle_id]["posture"].dropna()
                if not posture_vals.empty:
                    latest_posture = posture_vals.iloc[-1]

            latest_agitation = None
            if audio_count > 0 and "combined_agitation_score" in audio_df.columns:
                agit_vals = audio_df[audio_df["cycle_id"] == cycle_id]["combined_agitation_score"].dropna()
                if not agit_vals.empty:
                    latest_agitation = f"{agit_vals.iloc[-1]:.2f}"

            cycle_summary.append({
                "Cycle ID": int(cycle_id),
                "Sensor Samples": sensor_count,
                "Audio Samples": audio_count,
                "Camera Samples": camera_count,
                "Latest HR": latest_hr or "—",
                "Posture": latest_posture or "—",
                "Agitation": latest_agitation or "—"
            })

        if cycle_summary:
            st.dataframe(pd.DataFrame(cycle_summary), hide_index=True, width='stretch')
    else:
        st.info("No data from any source yet. Waiting for recordings…")

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════
    # DETAILED PER-CYCLE BREAKDOWN
    # ════════════════════════════════════════════════════════════════
    st.markdown("<p class='section-header'>🔬 &nbsp;DETAILED CYCLE BREAKDOWN</p>", unsafe_allow_html=True)

    if all_cycles:
        sorted_cycles = sorted(all_cycles, reverse=True)

        for cycle_id in sorted_cycles[:5]:  # Show detailed view for top 5 cycles
            sensor_data = sensor_df[sensor_df["cycle_id"] == cycle_id] if not sensor_df.empty else pd.DataFrame()
            audio_data = audio_df[audio_df["cycle_id"] == cycle_id] if not audio_df.empty else pd.DataFrame()
            camera_data = camera_df[camera_df["cycle_id"] == cycle_id] if not camera_df.empty else pd.DataFrame()

            sensor_count = len(sensor_data)
            audio_count = len(audio_data)
            camera_count = len(camera_data)

            # Expander for each cycle
            with st.expander(f"📊 Cycle {int(cycle_id)} — Sensor:{sensor_count} | Audio:{audio_count} | Camera:{camera_count}"):

                # === SENSOR DATA ===
                if sensor_count > 0:
                    st.markdown("##### 📈 Sensor Data")

                    # Statistics
                    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                    with col_s1:
                        if "heartRate" in sensor_data.columns:
                            hr_vals = sensor_data["heartRate"].dropna()
                            if not hr_vals.empty:
                                st.metric("HR (avg)", f"{hr_vals.mean():.0f}")
                        else:
                            st.caption("—")
                    with col_s2:
                        if "accelMag" in sensor_data.columns:
                            accel_vals = sensor_data["accelMag"].dropna()
                            if not accel_vals.empty:
                                st.metric("Accel (avg)", f"{accel_vals.mean():.2f}")
                        else:
                            st.caption("—")
                    with col_s3:
                        if "light" in sensor_data.columns:
                            light_vals = sensor_data["light"].dropna()
                            if not light_vals.empty:
                                st.metric("Light (avg)", f"{light_vals.mean():.0f}")
                        else:
                            st.caption("—")
                    with col_s4:
                        if "spo2" in sensor_data.columns:
                            spo2_vals = sensor_data["spo2"].dropna()
                            if not spo2_vals.empty:
                                st.metric("SpO2 (avg)", f"{spo2_vals.mean():.1f}%")
                        else:
                            st.caption("—")

                    # Detailed table
                    with st.expander("View all sensor samples"):
                        cols_to_show = ["timestamp", "heartRate", "accelMag", "gyroX", "light", "spo2"]
                        cols_available = [c for c in cols_to_show if c in sensor_data.columns]
                        st.dataframe(sensor_data[cols_available], width='stretch')
                else:
                    st.caption("ℹ️ No sensor data in this cycle")

                st.markdown("---")

                # === AUDIO DATA ===
                if audio_count > 0:
                    st.markdown("##### 🎤 Audio Data")

                    # Statistics
                    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                    with col_a1:
                        if "audio_energy" in audio_data.columns:
                            energy_vals = audio_data["audio_energy"].dropna()
                            if not energy_vals.empty:
                                st.metric("Energy (avg)", f"{energy_vals.mean():.0f}")
                        else:
                            st.caption("—")
                    with col_a2:
                        if "combined_agitation_score" in audio_data.columns:
                            agit_vals = audio_data["combined_agitation_score"].dropna()
                            if not agit_vals.empty:
                                st.metric("Agitation (avg)", f"{agit_vals.mean():.2f}")
                        else:
                            st.caption("—")
                    with col_a3:
                        if "speech_ratio" in audio_data.columns:
                            speech_vals = audio_data["speech_ratio"].dropna()
                            if not speech_vals.empty:
                                st.metric("Speech Ratio (avg)", f"{speech_vals.mean():.2%}")
                        else:
                            st.caption("—")
                    with col_a4:
                        if "pitch" in audio_data.columns:
                            pitch_vals = audio_data["pitch"].dropna()
                            if not pitch_vals.empty:
                                st.metric("Pitch (avg)", f"{pitch_vals.mean():.0f}Hz")
                        else:
                            st.caption("—")

                    # Detailed table
                    with st.expander("View all audio samples"):
                        cols_to_show = ["timestamp", "audio_energy", "combined_agitation_score", "speech_ratio", "pitch", "transcription"]
                        cols_available = [c for c in cols_to_show if c in audio_data.columns]
                        st.dataframe(audio_data[cols_available], width='stretch')
                else:
                    st.caption("ℹ️ No audio data in this cycle")

                st.markdown("---")

                # === CAMERA DATA ===
                if camera_count > 0:
                    st.markdown("##### 🎥 Camera Data")

                    # Statistics
                    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                    with col_c1:
                        if "posture" in camera_data.columns:
                            posture_counts = camera_data["posture"].value_counts()
                            top_posture = posture_counts.index[0] if len(posture_counts) > 0 else "—"
                            st.metric("Posture (most)", top_posture)
                        else:
                            st.caption("—")
                    with col_c2:
                        if "leg_angle" in camera_data.columns:
                            leg_vals = camera_data["leg_angle"].dropna()
                            if not leg_vals.empty:
                                st.metric("Leg Angle (avg)", f"{leg_vals.mean():.1f}°")
                        else:
                            st.caption("—")
                    with col_c3:
                        if "elbow_speed" in camera_data.columns:
                            elbow_vals = camera_data["elbow_speed"].dropna()
                            if not elbow_vals.empty:
                                st.metric("Elbow Speed (avg)", f"{elbow_vals.mean():.2f}")
                        else:
                            st.caption("—")
                    with col_c4:
                        if "hand_state" in camera_data.columns:
                            hand_counts = camera_data["hand_state"].value_counts()
                            top_hand = hand_counts.index[0] if len(hand_counts) > 0 else "—"
                            st.metric("Hand State (most)", top_hand)
                        else:
                            st.caption("—")

                    # Detailed table
                    with st.expander("View all camera samples"):
                        cols_to_show = ["timestamp", "posture", "hand_state", "leg_angle", "elbow_speed", "hitting/throwing"]
                        cols_available = [c for c in cols_to_show if c in camera_data.columns]
                        st.dataframe(camera_data[cols_available], width='stretch')
                else:
                    st.caption("ℹ️ No camera data in this cycle")

    # ════════════════════════════════════════════════════════════════
    # DETAILED UNIFIED VIEW
    # ════════════════════════════════════════════════════════════════
    st.markdown("<p class='section-header'>🔍 &nbsp;DETAILED CROSS-MODAL VIEW</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("##### 📊 Sensor Metrics")
        if not sensor_df.empty:
            latest_sensor = sensor_df.iloc[-1]
            if "heartRate" in latest_sensor and latest_sensor["heartRate"] is not None:
                st.metric("Latest HR", f"{latest_sensor['heartRate']:.0f}")
            else:
                st.metric("Latest HR", "—")

            accel_smooth = latest_sensor.get('accelMag_smooth') if 'accelMag_smooth' in latest_sensor else None
            accel = latest_sensor.get('accelMag') if 'accelMag' in latest_sensor else None
            accel_val = accel_smooth if accel_smooth is not None else accel
            if accel_val is not None:
                st.metric("Movement", f"{accel_val:.2f}")
            else:
                st.metric("Movement", "—")

            if "light" in latest_sensor and latest_sensor["light"] is not None:
                st.metric("Light Level", f"{latest_sensor['light']:.0f}")
            else:
                st.metric("Light Level", "—")

            if "gyroX" in latest_sensor and latest_sensor['gyroX'] is not None:
                st.caption(f"GyroX: {latest_sensor['gyroX']:.4f}")
        else:
            st.caption("No sensor data")

    with col2:
        st.markdown("##### 🎥 Camera Metrics")
        if not camera_df.empty:
            latest_camera = camera_df.iloc[-1]
            posture = latest_camera.get("posture", "—") if "posture" in latest_camera else "—"
            st.metric("Posture", posture)

            hand_state = latest_camera.get("hand_state", "—") if "hand_state" in latest_camera else "—"
            st.metric("Hand State", hand_state)

            if "leg_angle" in latest_camera and latest_camera.get("leg_angle") is not None:
                st.metric("Leg Angle", f"{latest_camera['leg_angle']:.1f}°")

            if "elbow_speed" in latest_camera and latest_camera.get("elbow_speed") is not None:
                st.caption(f"Elbow Speed: {latest_camera['elbow_speed']:.2f}")
        else:
            st.caption("No camera data")

    with col3:
        st.markdown("##### 🎤 Audio Metrics")
        if not audio_df.empty:
            latest_audio = audio_df.iloc[-1]
            agit_score = latest_audio.get("combined_agitation_score") if "combined_agitation_score" in latest_audio else None
            if agit_score is not None:
                agit_color = "#ef4444" if agit_score > 0.7 else "#f59e0b" if agit_score > 0.4 else "#22c55e"
                st.markdown(f"<div style='font-size:1.5rem; font-weight:700; color:{agit_color};'>{agit_score:.2f}</div><div style='font-size:0.8rem; color:#94a3b8;'>Agitation Score</div>", unsafe_allow_html=True)

            if "audio_energy" in latest_audio and latest_audio["audio_energy"] is not None:
                st.metric("Audio Energy", f"{latest_audio['audio_energy']:.0f}")
            else:
                st.metric("Audio Energy", "—")

            if "dominant_contributor" in latest_audio:
                st.caption(f"Dominant: {latest_audio['dominant_contributor']}")
        else:
            st.caption("No audio data")

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════
    # SOURCE COMPARISON TIMELINE
    # ════════════════════════════════════════════════════════════════
    st.markdown("<p class='section-header'>⏱️ &nbsp;MULTI-SOURCE TIMELINE</p>", unsafe_allow_html=True)

    timeline_data = []

    # Add sensor data points
    if not sensor_df.empty:
        for _, row in sensor_df.tail(20).iterrows():
            hr = row.get('heartRate')
            if hr is not None:
                metric_str = f"HR: {hr:.0f}"
            else:
                metric_str = "Accel data"
            timeline_data.append({
                "timestamp": row.get("timestamp"),
                "source": "Sensor",
                "cycle_id": row.get("cycle_id"),
                "metric": metric_str,
                "value": hr or row.get('accelMag')
            })

    # Add camera data points
    if not camera_df.empty:
        for _, row in camera_df.tail(20).iterrows():
            timeline_data.append({
                "timestamp": row.get("timestamp"),
                "source": "Camera",
                "cycle_id": row.get("cycle_id"),
                "metric": f"Posture: {row.get('posture', 'N/A')}",
                "value": None
            })

    # Add audio data points
    if not audio_df.empty:
        for _, row in audio_df.tail(20).iterrows():
            agit_val = row.get('combined_agitation_score')
            agit_str = f"{agit_val:.2f}" if agit_val is not None else 'N/A'
            timeline_data.append({
                "timestamp": row.get("timestamp"),
                "source": "Audio",
                "cycle_id": row.get("cycle_id"),
                "metric": f"Agitation: {agit_str}",
                "value": agit_val
            })

    if timeline_data:
        timeline_df = pd.DataFrame(timeline_data)
        timeline_df = timeline_df.sort_values("timestamp", ascending=False)

        # Display as formatted list
        for _, row in timeline_df.head(30).iterrows():
            ts_str = row["timestamp"].strftime("%H:%M:%S") if hasattr(row["timestamp"], "strftime") else str(row["timestamp"])
            color_map = {"Sensor": "#38bdf8", "Camera": "#34d399", "Audio": "#f472b6"}
            source_color = color_map.get(row["source"], "#94a3b8")

            cycle_val = row.get("cycle_id")
            cycle_str = f"{int(cycle_val)}" if pd.notna(cycle_val) and cycle_val != "" else "—"

            st.markdown(f"""
            <div style='background: rgba(30,30,47,0.6); padding: 10px 14px; border-radius: 8px; margin: 4px 0;'>
                <span style='color: {source_color}; font-weight: 600;'>● {row["source"]}</span>
                <span style='color: #64748b; margin: 0 10px;'>{ts_str}</span>
                <span style='color: #94a3b8;'>{row["metric"]}</span>
                <span style='color: #475569; float: right;'>Cycle: {cycle_str}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No unified data to display")


# ════════════════════════════════════════════════════════════════
#  TAB 3: CMAI DETECTION
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
        {"CMAI": 22, "Behaviour": "Screaming/Loud Vocalization", "Signal Thresholds": "Energy > 1500 + multi-indicator acoustic spike", "Basis": "Harsh, loud vocal output"},
        {"CMAI": 22, "Behaviour": "Pain/Discomfort vocalization", "Signal Thresholds": "Pain keywords + speech > 20% + energy > 650", "Basis": "Keyword-confirmed distress"},
        {"CMAI": 24, "Behaviour": "Verbal agitation/aggression", "Signal Thresholds": "Elevated speech OR keyword-confirmed distress/aggression", "Basis": "Speech tone + semantic cues"},
        {"CMAI": 25, "Behaviour": "Continuous/repetitive vocalization", "Signal Thresholds": "Speech ratio > 0.6 OR repeated words over recent windows", "Basis": "Sustained or repetitive speech"},
        {"CMAI": 26, "Behaviour": "Strange noises/negativism", "Signal Thresholds": "Non-speech impact acoustics OR refusal keywords", "Basis": "Acoustic anomaly + refusal language"},
        {"CMAI": 27, "Behaviour": "Calling out for help", "Signal Thresholds": "Help/caregiver keywords + speech + energy gate", "Basis": "Direct verbal help-seeking"},
        {"CMAI": 12, "Behaviour": "Pacing/fidgeting", "Signal Thresholds": "Sustained movement OR oscillatory accel changes", "Basis": "Regular or restless motion"},
        {"CMAI": 20, "Behaviour": "Repetitive mannerisms", "Signal Thresholds": "GyroX sign changes >= 4", "Basis": "Hand oscillation detection"},
        {"CMAI": 21, "Behaviour": "General restlessness", "Signal Thresholds": "Movement > 15 AND σ > 5 AND HR high/rising", "Basis": "Combined arousal indicators"},
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
            <span class='signal-tag-new'>spo2</span>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TAB 4: AUDIO ANALYSIS
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
