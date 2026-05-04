# Wear OS Behavioural Monitor (Dashboard)

A modular, robust visual analytics dashboard built with Streamlit. This application reads physiological, acoustic, and motion data from a connected Wear OS 4+ smartwatch via Firebase Firestore. It processes the raw incoming streams using a highly tuned, heuristic **Cohen-Mansfield Agitation Inventory (CMAI)** rule engine to detect signs of clinical distress and agitation in real-time.

## Features

- **Live Sensor Syncing**: Pulls high-frequency accelerometer, gyroscope, heart rate, and ambient light events.
- **SpO2 Diagnostics**: Intercepts diagnostic data and precise oxygen saturation metrics reported by the Samsung Health Sensor SDK.
- **Acoustic Profiling**: Visual metrics for Spectral Centroid, Audio Energy, Pitch, and Zero-Crossing Rate calculated from watch-recorded raw audio.
- **CMAI Rule Engine**: A comprehensive rule-based inference system customized for Wear OS micro-movements (filters out typing/noise) to detect behavioral patterns indicative of distress and agitation.
- **Quota-Friendly Firebase Implementation**: Utilizes modern `FieldFilter` and Streamlit caching (`@st.cache_data`) to prevent Firestore quota exhaustion during rapid live-refresh cycles.

## Modular Architecture

The dashboard has been heavily refactored into clean, independent modules:

- `app.py`: The Main View Layer. Manages Streamlit layout, routing, session states, and rendering logic.
- `utils/data_loader.py`: The Data Protocol Layer. Handles Firebase credentials, optimized Firestore querying (time-bound), and dataframe construction. 
- `utils/cmai_engine.py`: The Clinical Business Logic. Extracts math calculations (variance, angular velocity deadzones) and the exhaustive rule-based distress dictionary.
- `utils/ui_helpers.py`: The Aesthetics Engine. Handles customized Glassmorphism CSS injection and Plotly dark-theme abstractions.

## Prerequisites & Samsung SDK Setup

This dashboard requires a paired Wear OS application uploading strictly to Firebase. 

**Samsung Health Platform Requirements:**
- The Watch app requires the proprietary `samsung-health-sensor-api-1.4.1.aar`. 
- **Developer Mode** must be turned on in the watch's *Health Platform* for SpO2 measurements to bypass `SDK_POLICY_ERROR` on unreleased apps:
    1. Go to watch **Settings** > **Apps** > **Health Platform**.
    2. Tap rapidly on the "Health Platform" version text 10 times until `[Dev Mode]` appears.

## Setup Instructions

1. Retrieve your Firebase `serviceAccountKey.json` and place it in the root of this folder (auto-ignored by Git).
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install dependencies:
    ```bash
    pip install streamlit streamlit-autorefresh firebase-admin pandas numpy plotly pytz
    ```
4. Run the dashboard locally:
    ```bash
    streamlit run app.py
    ```

*(Security Note: Ensure `.env`, `venv/`, and `serviceAccountKey.json` remain outside of version control).*
