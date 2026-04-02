# MultiSense Project Pipeline & Technical Documentation

## Project Overview

**Project Name:** MultiSense
**Purpose:** Real-time behavioral monitoring system for dementia care using wearable sensors
**Type:** Web-based dashboard application with Firebase backend
**Primary Use Case:** Healthcare monitoring of CMAI (Cohen-Mansfield Agitation Inventory) behaviors

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              WEARABLE DATA COLLECTION LAYER                     │
│  (Samsung Galaxy Watch 4 / WearOS Application)                  │
│                                                                 │
│  • 5-second audio samples captured every 15 seconds            │
│  • Accelerometer & Gyroscope (IMU data)                        │
│  • Heart rate monitoring (BPM)                                 │
│  • Ambient light sensor                                        │
│  • On-device audio feature extraction                          │
└────────────────────────┬────────────────────────────────────────┘
                         │ Upload via WiFi/Cellular
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              CLOUD DATA STORAGE LAYER                           │
│  (Google Firebase Cloud Firestore - NoSQL Database)            │
│                                                                 │
│  Collections:                                                   │
│  1. audio_samples                                              │
│     - Audio features (energy, pitch, ZCR, spectral analysis)   │
│     - Speech transcription                                     │
│     - Keyword detection results                                │
│     - Combined agitation scores                                │
│                                                                 │
│  2. sensor_samples                                             │
│     - Motion data (accel magnitude, gyro XYZ)                  │
│     - Heart rate readings                                      │
│     - Light sensor data                                        │
│     - Timestamp indexing                                       │
│                                                                 │
│  3. cmai_detections                                            │
│     - Detected behaviors (CMAI items)                          │
│     - Confidence levels (HIGH/MEDIUM/LOW)                      │
│     - Evidence and signal metadata                             │
└────────────────────────┬────────────────────────────────────────┘
                         │ Firestore SDK queries
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              WEB APPLICATION LAYER                              │
│  (Python Streamlit Application - app.py)                       │
│                                                                 │
│  Components:                                                    │
│  • Data fetching & caching (Firebase SDK)                      │
│  • Rule-based CMAI detection engine                            │
│  • Signal processing & feature analysis                        │
│  • Patient state management (Calm/Agitated)                    │
│  • Real-time data visualization (Plotly)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP Server
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              USER INTERFACE LAYER                               │
│  (Browser-based Web Dashboard)                                  │
│                                                                 │
│  Three Main Tabs:                                              │
│  1. Live Dashboard (📊)                                         │
│  2. CMAI Detection Analysis (🧠)                                │
│  3. Audio Feature Visualization (🎵)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Frontend Technologies

#### **Streamlit Framework**
- **Purpose:** Web application framework for interactive dashboards
- **Version:** Latest (requires Python 3.7+)
- **Why:** Rapid prototyping, reactive programming model, built-in UI components
- **Features Used:**
  - Page configuration & layout
  - Session state management
  - Tabs and columns for layout
  - Metrics, charts, and markdown rendering
  - Interactive buttons and toggles

#### **Streamlit-autorefresh**
- **Purpose:** Auto-refresh component for live data updates
- **Implementation:** 30-second refresh interval in live mode
- **Configuration:** Conditional refresh based on live_mode toggle

#### **Plotly**
- **Purpose:** Interactive data visualization library
- **Components Used:**
  - Plotly Express: High-level chart creation
  - Plotly Graph Objects: Custom chart building
  - Subplots: Multi-panel visualizations
- **Chart Types:**
  - Time series line charts (motion, audio features)
  - Scatter plots with trend lines
  - Multi-trace overlays (accel + heart rate)
  - MFCC heatmaps

### Backend Technologies

#### **Python 3.x**
- **Core Language:** Application logic and data processing
- **Standard Libraries:**
  - `datetime` & `pytz`: Timezone handling (US/Eastern)
  - `json`: Data serialization
  - `os`: Environment variable access

#### **Firebase Admin SDK**
- **Purpose:** Cloud database integration
- **Authentication:** Service account key (JSON file)
- **Features Used:**
  - Firestore client initialization
  - Query operations (where, order_by, limit)
  - Document stream processing
  - Real-time data fetching

#### **Data Processing Libraries**

**Pandas**
- DataFrame operations for time-series data
- Merging audio and sensor dataframes on timestamp
- Data filtering and aggregation
- Missing value handling

**NumPy**
- Numerical computations
- Array operations for signal processing
- Statistical calculations (mean, std, percentiles)

### Cloud Infrastructure

#### **Google Firebase Cloud Firestore**
- **Database Type:** NoSQL document database
- **Indexing:** Timestamp-based (descending order)
- **Query Optimization:**
  - TTL caching (30s live, 300s offline)
  - Limited document retrieval (50-100 docs)
  - Fallback queries for empty results
- **Collections Schema:**

```
audio_samples/
  {document_id}/
    - timestamp: DateTime
    - audio_energy: float (RMS)
    - pitch: float (Hz)
    - zero_crossing_rate: float
    - spectral_centroid: float (Hz)
    - spectral_bandwidth: float
    - spectral_flux: float
    - speech_ratio: float (0-1)
    - transcription: string
    - top_keywords: array
    - combined_agitation_score: object
      - speech_score: float
      - acoustic_score: float
      - motion_score: float

sensor_samples/
  {document_id}/
    - timestamp: DateTime
    - accelMag: float (m/s²)
    - gyroX, gyroY, gyroZ: float (rad/s)
    - heartRate: int (BPM)
    - light: float (lux)

cmai_detections/
  {document_id}/
    - timestamp: DateTime
    - cmai_item: string (e.g., "CMAI #22")
    - behaviour: string
    - confidence_level: string (HIGH/MEDIUM/LOW)
    - indicators: array
    - keywords: array
    - evidence: string
```

---

## Data Flow Pipeline

### Phase 1: Data Collection (Wearable Device)

**Device:** Samsung Galaxy Watch 4
**OS:** WearOS
**Sensors:**
- Microphone (continuous audio sampling)
- 6-axis IMU (accelerometer + gyroscope)
- Optical heart rate sensor
- Ambient light sensor

**Sampling Strategy:**
- Audio: 5-second samples every 15 seconds (20% duty cycle)
- IMU: Continuous or high-frequency sampling (e.g., 50Hz)
- Heart rate: Per-minute updates
- Light: Per-minute or event-triggered

**On-Device Processing:**
1. Audio feature extraction (FFT-based):
   - RMS energy calculation
   - Zero-crossing rate
   - Spectral centroid, bandwidth, flux
   - Pitch estimation (autocorrelation method)
   - Speech ratio (Voice Activity Detection)
2. Speech transcription (cloud API or on-device model)
3. Keyword detection (pain, hurt, help, distress, etc.)
4. Composite agitation score calculation
5. Motion magnitude and variance calculations

**Data Upload:**
- WiFi or cellular connection to Firebase
- Batched uploads to reduce network overhead
- Timestamp synchronization (UTC conversion)

### Phase 2: Cloud Storage (Firebase)

**Write Operations:**
- Wearable app writes to `audio_samples` and `sensor_samples` collections
- Document ID: Auto-generated or timestamp-based
- Indexed fields: `timestamp` (for efficient range queries)

**Data Retention:**
- No explicit retention policy defined in app
- Firestore default: Unlimited storage (until manually deleted)
- Cost optimization: Query only recent data (today or last 50-100 docs)

### Phase 3: Data Processing (Streamlit App)

#### **Data Fetching**

**Function:** `load_data_from_firestore()`

**Logic:**
1. Check session cache (TTL-based)
2. Query Firebase for today's data:
   ```python
   audio_query = audio_ref.where('timestamp', '>=', today_start)\
                          .where('timestamp', '<=', today_end)\
                          .order_by('timestamp', direction='DESCENDING')\
                          .limit(50)
   ```
3. Fallback: If no data, fetch last 50 documents without date filter
4. Convert Firestore documents to Pandas DataFrame
5. Handle missing values and type conversions
6. Merge audio and sensor data on timestamp (outer join)

**Caching Strategy:**
- `@st.cache_data(ttl=30 if live_mode else 300)`
- In-memory caching via `st.session_state`
- Invalidation on manual refresh or state change

#### **CMAI Detection Engine**

**Function:** `detect_cmai_behaviours_realtime(df)`

**Approach:** Rule-based detection (no machine learning)

**Detection Rules:**

1. **CMAI #22 - Screaming/Loud Vocalization**
   - Conditions:
     - Audio energy > 2500
     - Spectral centroid > 2500 Hz
     - Pitch > 150 Hz
     - Speech ratio > 0.4
     - Spectral flux > 1000
   - Threshold: ≥5 indicators → HIGH confidence

2. **CMAI #26 - Strange Noises/Impact Sounds**
   - Conditions:
     - ZCR > 0.2 (high zero-crossing)
     - Speech ratio < 0.3 (non-speech)
     - Keywords: "clapping", "banging"
     - Spectral flux > 1000 (sudden onset)
   - Threshold: ≥3 indicators → HIGH confidence

3. **CMAI #24 - Verbal Agitation**
   - Conditions:
     - Speech ratio > 0.5
     - Pitch > 140 Hz
     - Spectral centroid > 2000 Hz
     - Keywords: "stressed", "angry"
   - Threshold: ≥4 indicators → HIGH confidence

4. **CMAI #25 - Continuous Vocalization**
   - Condition: Speech ratio > 0.6 for ≥30 seconds
   - Threshold: Single condition → MEDIUM confidence

5. **CMAI #12 - Pacing/Wandering + Fidgeting**
   - Pacing: Sustained moderate movement (accel 1.5-3.0 m/s²) + low variance
   - Fidgeting: High movement variance + rapid oscillations
   - Threshold: Either condition → MEDIUM confidence

6. **CMAI #20 - Repetitive Mannerisms**
   - Condition: Oscillatory gyroX (≥4 sign changes in 10-second window)
   - Threshold: Single condition → MEDIUM confidence

7. **CMAI #21 - General Restlessness**
   - Conditions:
     - Accel magnitude > 1.8 m/s²
     - High motion variance
     - Heart rate > 90 BPM
   - Threshold: ≥2 indicators → MEDIUM confidence

**Output:**
- List of detected behaviors with:
  - CMAI item number
  - Behavior description
  - Confidence level
  - Indicators triggered
  - Keywords (if applicable)
  - Evidence string

#### **Patient State Management**

**State Variable:** `st.session_state.patient_state`

**States:**
- `"Calm"`: Default state
- `"Agitated"`: Triggered when HIGH or ≥2 MEDIUM confidence detections

**State Transitions:**
- Calm → Agitated: Any detection meeting threshold
- Agitated → Calm: Manual reset button only (no auto-reset)

**Persistence:**
- Stored in Streamlit session state (in-memory)
- Resets on page reload or browser close

### Phase 4: Visualization & UI

#### **Tab 1: Live Dashboard (📊)**

**Components:**

1. **Live Mode Toggle**
   - Enables 30-second auto-refresh
   - st_autorefresh component

2. **Patient Status Card**
   - Badge: Calm (green) or Agitated (red with pulse animation)
   - Last update timestamp

3. **Key Metrics (4 columns)**
   - Heart Rate (BPM) - color-coded by zone
   - Movement (m/s²) - latest accelMag
   - Speech Ratio (%) - voice activity percentage
   - Combined Score - agitation composite

4. **Combined Agitation Score Breakdown**
   - Progress bars for:
     - Speech score (0-100)
     - Acoustic score (0-100)
     - Motion score (0-100)

5. **Active Detections Panel**
   - HIGH confidence: Red alert boxes
   - MEDIUM confidence: Orange warning boxes
   - Shows: Behavior, evidence, timestamp

6. **Live Signal Charts**
   - Motion & Heart Rate (dual-axis time series)
   - Audio Energy trend line
   - Pitch variation over time
   - ZCR signal
   - Spectral Centroid
   - Ambient Light levels
   - New Audio Features (spectral bandwidth, flux)

7. **Intervention Banner**
   - Displayed when patient_state == "Agitated"
   - Shows: Calming music, breathing patterns status

8. **Speech Detection Section**
   - Latest transcription
   - Agitation score badges (High/Medium/Low)
   - Detected keywords with categories

9. **Manual Controls**
   - "Trigger Agitation" button (testing/simulation)
   - "Reset to Calm" button

#### **Tab 2: CMAI Detection Analysis (🧠)**

**Components:**

1. **Detection Summary**
   - Total detections count
   - Breakdown by confidence level (HIGH/MEDIUM/LOW)
   - Pie chart of behavior distribution

2. **Detection Timeline**
   - Chronological list of all detections
   - Expandable details:
     - CMAI item number
     - Behavior description
     - Confidence level
     - Indicators triggered
     - Keywords
     - Evidence

3. **Category Sections**
   - Aggressive Behaviors (CMAI #22, #26)
   - Verbal Behaviors (CMAI #24, #25)
   - Physical Non-Aggressive (CMAI #12, #20, #21)

4. **Signal Thresholds Reference**
   - Interactive threshold explanations
   - Example signal ranges
   - Calibration notes

5. **Research Notes**
   - CMAI methodology
   - Threshold calibration details
   - Sensitivity/specificity notes

#### **Tab 3: Audio Feature Visualization (🎵)**

**Components:**

1. **Feature Definitions**
   - Audio Energy (RMS): Loudness indicator
   - Zero-Crossing Rate: Noise vs. speech distinction
   - Spectral Centroid: Sound brightness
   - Spectral Bandwidth: Frequency spread
   - Spectral Flux: Onset detection
   - Pitch (F0): Fundamental frequency
   - Speech Ratio: VAD output

2. **Time Series Charts**
   - Individual plots for each audio feature
   - Color-coded by threshold zones
   - Annotations for significant events

3. **MFCC Visualization**
   - Heatmap of Mel-Frequency Cepstral Coefficients
   - Time on X-axis, MFCC bin on Y-axis
   - Color intensity = coefficient magnitude

4. **Correlation Matrix**
   - Feature interdependencies
   - Heatmap visualization

5. **Distribution Histograms**
   - Frequency distributions for each feature
   - Normal/outlier detection

---

## Workflow Summary

### End-to-End User Journey

1. **Setup & Configuration**
   - Deploy Streamlit app to server (e.g., Streamlit Cloud, AWS, GCP)
   - Configure Firebase credentials (serviceAccountKey.json)
   - Set environment variables (if any)
   - Start Streamlit server: `streamlit run app.py`

2. **Data Collection**
   - Patient wears Samsung Galaxy Watch 4
   - Watch app continuously samples sensors
   - Audio processed on-device (privacy-preserving)
   - Data uploaded to Firebase every 15-30 seconds

3. **Monitoring**
   - Healthcare worker opens web dashboard
   - Enables live mode for real-time updates
   - Monitors patient status badge (Calm/Agitated)
   - Reviews active detection alerts

4. **Intervention**
   - Agitation detected → Alert displayed
   - Worker initiates calming intervention:
     - Play soothing music
     - Guide breathing exercises
     - Check for physical needs (pain, discomfort)
   - Intervention status shown in dashboard

5. **Analysis**
   - Review CMAI detection timeline
   - Identify behavior patterns (time-of-day trends)
   - Analyze audio/motion feature correlations
   - Export data for clinical review (future feature)

6. **Reset**
   - After successful intervention, worker clicks "Reset to Calm"
   - Dashboard returns to monitoring mode

---

## Key Implementation Details

### Firebase Optimization

**Challenge:** Firestore charges per document read
**Solution:**
- TTL-based caching (30s/300s)
- Query limits (50-100 docs)
- Date-range filtering (today only)
- Session state caching

**Cost Estimate:**
- Live mode: ~2 queries/minute × 60 minutes × 2 collections = 240 reads/hour
- Daily usage (12-hour shift): ~2,880 reads/day
- Firestore free tier: 50,000 reads/day (sufficient)

### Signal Processing

**Audio Features:**
- **FFT:** Fast Fourier Transform for frequency analysis
- **Autocorrelation:** Pitch estimation (fundamental frequency detection)
- **Mel-Filterbank:** MFCC computation (speech recognition)
- **Energy:** RMS (Root Mean Square) amplitude
- **ZCR:** Sign changes in waveform (texture measure)

**Motion Features:**
- **Acceleration Magnitude:** √(x² + y² + z²)
- **Variance:** Movement variability
- **Gyroscope Sign Changes:** Oscillation detection

### Threshold Calibration

**Device-Specific:** Samsung Galaxy Watch 4 microphone
**Calibration Method:** Empirical testing with known agitation samples
**Validation:** Clinical observation correlation (not ML-trained)

**Threshold Values:**
- Audio energy: 2500 (screaming threshold)
- Spectral centroid: 2500 Hz (harsh sound)
- Pitch: 150 Hz (elevated vocalization)
- ZCR: 0.2 (noisy/percussive)
- Accel magnitude: 1.8 m/s² (moderate movement)
- Heart rate: 90 BPM (elevated)

### State Persistence

**Current Implementation:**
- In-memory only (st.session_state)
- No database writes for state changes
- No audit log

**Limitation:** State lost on page reload

**Future Enhancement:**
- Write state changes to Firebase
- Create `patient_state_log` collection
- Track intervention history

---

## System Requirements

### Development Environment

- **Python:** 3.7 or higher
- **OS:** Linux, macOS, Windows (cross-platform)
- **RAM:** 2GB minimum (4GB recommended)
- **Storage:** 500MB (dependencies + cache)

### Dependencies

See `requirements.txt` (to be created):
```
streamlit>=1.28.0
streamlit-autorefresh>=0.0.1
firebase-admin>=6.0.0
pandas>=1.5.0
numpy>=1.23.0
plotly>=5.14.0
pytz>=2023.3
```

### Firebase Setup

1. Create Firebase project at https://console.firebase.google.com
2. Enable Firestore Database
3. Create service account:
   - Project Settings → Service Accounts
   - Generate new private key (JSON)
   - Save as `serviceAccountKey.json`
4. Create collections: `audio_samples`, `sensor_samples`, `cmai_detections`
5. Set security rules (allow read/write for authenticated users)

### Deployment Options

**Local Development:**
```bash
streamlit run app.py
```

**Streamlit Cloud:**
1. Push code to GitHub
2. Connect repo to Streamlit Cloud
3. Add secrets (Firebase credentials) in dashboard
4. Deploy

**Docker:**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Cloud Platforms:**
- AWS: EC2 + ALB or ECS
- GCP: Cloud Run or Compute Engine
- Azure: App Service or Container Instances

---

## Limitations & Future Enhancements

### Current Limitations

1. **No Authentication:** Single-user deployment only
2. **No Data Export:** Cannot download reports or raw data
3. **Manual State Reset:** No automatic calm detection
4. **Device-Specific Calibration:** Thresholds tuned for Galaxy Watch 4 only
5. **No Historical Trends:** No long-term pattern analysis
6. **Limited Intervention Tracking:** No structured intervention logging
7. **No Multi-Patient Support:** One dashboard per patient

### Planned Enhancements

1. **User Authentication:** Role-based access control (admin, caregiver, viewer)
2. **Export Features:** CSV/PDF report generation
3. **Automatic State Recovery:** Detect when agitation subsides
4. **Adaptive Thresholds:** Per-patient calibration and ML-based tuning
5. **Historical Analytics:** Week/month trend charts, pattern recognition
6. **Intervention Logging:** Structured form for intervention details + outcomes
7. **Multi-Patient Dashboard:** Support multiple patients with switcher
8. **Mobile Optimization:** Responsive design for tablet/phone viewing
9. **Notification System:** SMS/email alerts for critical detections
10. **Integration:** HL7/FHIR export for EHR systems

---

## Security & Privacy

### Data Protection

- **Audio Data:** Processed on-device, only features transmitted (not raw audio)
- **Credentials:** Firebase key excluded from git (.gitignore)
- **HIPAA Compliance:** NOT currently compliant (requires:
  - BAA with Firebase
  - Encrypted storage
  - Audit logging
  - Access controls
  - Data retention policies)

### Recommended Practices

1. Deploy behind VPN or private network
2. Enable Firestore security rules (authenticated access only)
3. Use environment variables for credentials (not hardcoded)
4. Enable Firebase audit logging
5. Regular security reviews and dependency updates
6. Encrypt data at rest (Firestore default) and in transit (HTTPS)

---

## Testing & Validation

### Recommended Test Cases

1. **Data Fetching:**
   - Empty database → fallback query
   - Network failure → error handling
   - Malformed documents → validation

2. **Detection Logic:**
   - Known agitation samples → HIGH confidence expected
   - Calm baseline samples → no detections expected
   - Edge cases (missing features) → graceful degradation

3. **UI Interaction:**
   - Toggle live mode → auto-refresh starts/stops
   - Manual triggers → state changes correctly
   - Tab switching → data persists

4. **Performance:**
   - Load 100+ documents → renders within 5 seconds
   - Live mode for 1 hour → no memory leaks
   - Concurrent users (if applicable) → no conflicts

### Validation Strategy

- **Clinical Validation:** Compare detections with caregiver observations
- **Sensitivity Analysis:** Calculate true positive rate for known agitation events
- **Specificity Analysis:** Calculate false positive rate during calm periods
- **User Testing:** Gather feedback from healthcare workers on usability

---

## Contact & Support

**Project Repository:** https://github.com/utk1college/MultiSense
**Current Branch:** `copilot/vscode-mnhip6vp-v35l`
**Last Updated:** 2026-04-02

For technical issues, refer to:
- Streamlit documentation: https://docs.streamlit.io
- Firebase documentation: https://firebase.google.com/docs
- Plotly documentation: https://plotly.com/python/
