# MultiSense - Behavioral Monitoring Dashboard

**Real-time behavioral monitoring system for dementia care using wearable sensors and Firebase Cloud.**

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-latest-FF4B4B.svg)](https://streamlit.io/)
[![Firebase](https://img.shields.io/badge/firebase-firestore-orange.svg)](https://firebase.google.com/)

---

## Overview

MultiSense is a web-based dashboard application that provides real-time monitoring of behavioral indicators for dementia patients using data from wearable sensors (Samsung Galaxy Watch 4). The system implements rule-based detection of CMAI (Cohen-Mansfield Agitation Inventory) behaviors through audio and motion signal processing.

### Key Features

- **Real-Time Monitoring:** Live dashboard with 30-second auto-refresh
- **CMAI Behavior Detection:** 7 behavioral indicators (screaming, verbal agitation, pacing, restlessness, etc.)
- **Multi-Modal Sensing:** Audio features, motion data, heart rate, ambient light
- **Interactive Visualization:** Plotly-powered charts with time-series analysis
- **Patient State Management:** Automated agitation detection with manual override controls
- **Firebase Integration:** Cloud-based data storage with optimized queries

---

## Quick Start

### Prerequisites

- Python 3.7 or higher
- Firebase project with Firestore enabled
- Firebase service account credentials (JSON file)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/utk1college/MultiSense.git
   cd MultiSense
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Firebase:**
   - Create a Firebase project at https://console.firebase.google.com
   - Enable Cloud Firestore
   - Generate service account key:
     - Go to Project Settings → Service Accounts
     - Click "Generate new private key"
     - Save as `serviceAccountKey.json` in project root
   - Create collections: `audio_samples`, `sensor_samples`, `cmai_detections`

4. **Run the application:**
   ```bash
   streamlit run app.py
   ```

5. **Open your browser:**
   - Navigate to http://localhost:8501
   - Toggle "Live Mode" for real-time updates

---

## Project Structure

```
MultiSense/
├── app.py                    # Main Streamlit application (1,354 lines)
├── requirements.txt          # Python dependencies
├── PROJECT_PIPELINE.md       # Comprehensive technical documentation
├── README.md                 # This file
├── .gitignore               # Git ignore rules
└── serviceAccountKey.json   # Firebase credentials (NOT in git)
```

---

## Firebase Setup

### Required Collections

**1. audio_samples**
```javascript
{
  timestamp: DateTime,
  audio_energy: float,           // RMS amplitude
  pitch: float,                  // Fundamental frequency (Hz)
  zero_crossing_rate: float,     // Texture measure
  spectral_centroid: float,      // Sound brightness (Hz)
  spectral_bandwidth: float,     // Frequency spread
  spectral_flux: float,          // Onset detection
  speech_ratio: float,           // Voice activity (0-1)
  transcription: string,         // Speech-to-text
  top_keywords: array,           // Detected keywords
  combined_agitation_score: {
    speech_score: float,
    acoustic_score: float,
    motion_score: float
  }
}
```

**2. sensor_samples**
```javascript
{
  timestamp: DateTime,
  accelMag: float,              // Acceleration magnitude (m/s²)
  gyroX, gyroY, gyroZ: float,   // Angular velocity (rad/s)
  heartRate: int,                // BPM
  light: float                   // Ambient light (lux)
}
```

**3. cmai_detections**
```javascript
{
  timestamp: DateTime,
  cmai_item: string,            // e.g., "CMAI #22"
  behaviour: string,            // Behavior description
  confidence_level: string,     // HIGH/MEDIUM/LOW
  indicators: array,            // Triggered conditions
  keywords: array,              // Detected keywords
  evidence: string              // Summary
}
```

### Security Rules (Firestore)

For development (open access):
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if true;
    }
  }
}
```

For production (authenticated users only):
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

---

## Usage Guide

### Dashboard Tabs

#### 1. Live Dashboard (📊)
- **Patient Status:** Current state (Calm/Agitated)
- **Key Metrics:** Heart rate, movement, speech ratio, agitation score
- **Active Alerts:** HIGH/MEDIUM confidence detections
- **Live Charts:** Real-time signal visualization
- **Speech Detection:** Transcription and keyword analysis
- **Manual Controls:** Trigger agitation or reset to calm

#### 2. CMAI Detection Analysis (🧠)
- **Detection Timeline:** Chronological list of all behaviors
- **Behavior Categories:**
  - Aggressive: Screaming, strange noises
  - Verbal: Verbal agitation, continuous vocalization
  - Physical: Pacing, fidgeting, restlessness
- **Signal Thresholds:** Interactive reference guide

#### 3. Audio Feature Visualization (🎵)
- **Time Series:** Individual plots for all audio features
- **MFCC Heatmap:** Mel-frequency cepstral coefficients
- **Distributions:** Feature histograms and correlations

### Detected Behaviors (CMAI Items)

| CMAI # | Behavior | Detection Criteria |
|--------|----------|-------------------|
| #22 | Screaming/Loud Vocalization | High energy + High spectral centroid + Elevated pitch |
| #26 | Strange Noises/Impact Sounds | High ZCR + Non-speech + Sudden onsets |
| #24 | Verbal Agitation | High speech ratio + Elevated pitch + Tense voice |
| #25 | Continuous Vocalization | Sustained speech ratio > 0.6 |
| #12 | Pacing/Wandering + Fidgeting | Sustained movement or oscillatory motion |
| #20 | Repetitive Mannerisms | Oscillatory gyroscope patterns |
| #21 | General Restlessness | High movement + Variable motion + Elevated heart rate |

---

## Configuration

### Environment Variables (Optional)

Create a `.env` file in project root:
```bash
# Firebase configuration
FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json

# Timezone
TIMEZONE=US/Eastern

# Auto-refresh interval (seconds)
LIVE_REFRESH_INTERVAL=30
```

### Streamlit Configuration

Create `.streamlit/config.toml`:
```toml
[server]
port = 8501
address = "0.0.0.0"

[theme]
primaryColor = "#38bdf8"
backgroundColor = "#1e1e2f"
secondaryBackgroundColor = "#2a2a40"
textColor = "#e2e8f0"
font = "sans serif"

[browser]
gatherUsageStats = false
```

---

## Deployment

### Local Development
```bash
streamlit run app.py
```

### Streamlit Cloud
1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Connect repository
4. Add secrets (Firebase credentials) in dashboard settings
5. Deploy

### Docker
```bash
# Build image
docker build -t multisense .

# Run container
docker run -p 8501:8501 \
  -v $(pwd)/serviceAccountKey.json:/app/serviceAccountKey.json \
  multisense
```

### AWS/GCP/Azure
See detailed deployment instructions in `PROJECT_PIPELINE.md`

---

## Development

### Code Style

- Python 3.7+ syntax
- PEP 8 compliance (flexible)
- Type hints encouraged
- Comments for complex logic

### Testing

Currently no automated tests. Recommended test areas:
- Firebase data fetching
- CMAI detection logic
- UI state management
- Chart rendering

### Contributing

This is a research prototype. For contributions:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/your-feature`)
3. Commit changes (`git commit -am 'Add feature'`)
4. Push to branch (`git push origin feature/your-feature`)
5. Open Pull Request

---

## Technical Documentation

For comprehensive technical details, see:
- **[PROJECT_PIPELINE.md](PROJECT_PIPELINE.md)** - Full architecture, data flow, and implementation details

Topics covered:
- System architecture diagrams
- Complete technology stack breakdown
- Data flow pipeline (end-to-end)
- Firebase schema and optimization
- Signal processing algorithms
- CMAI detection rules and thresholds
- UI component descriptions
- Security and privacy considerations
- Testing and validation strategies
- Future enhancements roadmap

---

## Troubleshooting

### Common Issues

**1. Firebase Authentication Error**
```
Error: Could not automatically determine credentials
```
**Solution:** Ensure `serviceAccountKey.json` is in project root with correct permissions.

**2. Missing Dependencies**
```
ModuleNotFoundError: No module named 'streamlit'
```
**Solution:** Run `pip install -r requirements.txt`

**3. No Data Displayed**
```
"No data available"
```
**Solution:**
- Check Firebase collections exist and have data
- Verify timestamp format is datetime object
- Check Firestore security rules allow read access

**4. Slow Performance**
```
Dashboard takes >10 seconds to load
```
**Solution:**
- Enable caching (already implemented)
- Reduce query limit (change `limit(50)` to `limit(20)` in app.py:~line 200)
- Use live mode only when needed

---

## System Requirements

### Minimum
- Python 3.7+
- 2GB RAM
- Internet connection (Firebase access)

### Recommended
- Python 3.9+
- 4GB RAM
- Stable broadband (for live mode)

### Browser Compatibility
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## License

This is a research prototype. License details to be determined.

---

## Acknowledgments

- **CMAI Framework:** Cohen-Mansfield Agitation Inventory
- **Wearable Platform:** Samsung Galaxy Watch 4 (WearOS)
- **Cloud Infrastructure:** Google Firebase
- **Visualization:** Plotly Community

---

## Support

For technical issues or questions:
- Create an issue on GitHub: https://github.com/utk1college/MultiSense/issues
- Check `PROJECT_PIPELINE.md` for detailed documentation

---

## Disclaimer

**This is a research prototype and NOT intended for clinical use without proper validation.**

- No HIPAA compliance (currently)
- No FDA approval
- No clinical validation studies
- Thresholds calibrated for specific device only (Galaxy Watch 4)
- Manual clinical oversight required

Use at your own risk. Consult healthcare professionals for patient care decisions.
