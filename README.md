# MultiSense Dashboard

Streamlit dashboard for viewing behavioral monitoring data stored in Firebase Firestore.

## What It Is

This branch contains the dashboard only.

It reads data produced by a separate Wear OS app and shows:

- live and offline monitoring views
- heart rate, movement, speech ratio, and agitation score cards
- motion and audio feature charts
- CMAI-inspired rule-based detections
- keyword-based speech alerts from uploaded Firestore data

## What This Repo Currently Contains

- `app.py` - main Streamlit dashboard
- `README.md` - this file
- `.gitignore` - repo ignore rules

Local-only files such as `serviceAccountKey.json` and `venv/` are intentionally not tracked.

## Data Source

The dashboard reads from these Firestore collections:

- `audio_samples`
- `sensor_samples`

## Run Locally

Install the required packages:

```bash
pip install streamlit streamlit-autorefresh firebase-admin pandas numpy plotly pytz
```

Start the app:

```bash
streamlit run app.py
```

## Development

This repository uses Claude Code for AI-assisted development. For information about Claude Code's capabilities, GitHub integration, and development workflow, see [API.md](API.md).

## Notes

- This is a research prototype, not a clinically validated tool.
- The dashboard logic is heuristic and CMAI-inspired.
- This branch does not currently include the Wear OS codebase.
