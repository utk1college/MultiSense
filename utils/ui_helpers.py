import streamlit as st
import plotly.graph_objects as go

def inject_custom_css():
    # ---------- inject modern CSS ----------
    st.markdown("""
    <style>
    /* ---- global ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ---- remove default padding ---- */
    .block-container { padding-top: 2rem; padding-bottom: 0.5rem; }

    /* ---- metric card ---- */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e1e2f 0%, #2a2a40 100%);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,.25);
    }
    div[data-testid="stMetric"] label {
        color: #9ca3af !important;
        font-size: .82rem !important;
        letter-spacing: .03em;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-weight: 700 !important;
        font-size: 1.55rem !important;
        color: #e2e8f0 !important;
    }

    /* ---- section header ---- */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #cbd5e1;
        margin: 1.2rem 0 0.6rem 0;
        letter-spacing: .02em;
    }

    /* ---- calm / agitated badges ---- */
    .badge-calm {
        display: inline-block;
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: #fff;
        font-weight: 600;
        font-size: 1.35rem;
        padding: 16px 28px;
        border-radius: 14px;
    }
    .badge-agitated {
        display: inline-block;
        background: linear-gradient(135deg, #dc2626 0%, #f87171 100%);
        color: #fff;
        font-weight: 600;
        font-size: 1.35rem;
        padding: 16px 28px;
        border-radius: 14px;
        animation: pulse 1.5s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(248,113,113,.5); }
        50% { box-shadow: 0 0 0 12px rgba(248,113,113,0); }
    }

    /* ---- detection alert ---- */
    .detection-alert {
        background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
        color: #fff;
        padding: 12px 20px;
        border-radius: 10px;
        margin: 10px 0;
        font-weight: 500;
    }
    .detection-alert-warning {
        background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
        color: #fff;
        padding: 12px 20px;
        border-radius: 10px;
        margin: 10px 0;
        font-weight: 500;
    }

    /* ---- intervention banner ---- */
    .intervention-banner {
        background: linear-gradient(90deg, #1e3a5f 0%, #2d4a6f 100%);
        border-left: 4px solid #38bdf8;
        color: #e0f2fe;
        padding: 14px 20px;
        border-radius: 0 10px 10px 0;
        margin: 12px 0;
    }

    /* ---- research notes ---- */
    .research-note {
        background: rgba(59, 130, 246, 0.08);
        border-left: 3px solid #3b82f6;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        color: #94a3b8;
        font-size: 0.88rem;
        margin: 12px 0;
    }

    /* ---- CMAI section boxes ---- */
    .cmai-section-box {
        background: rgba(30, 30, 47, 0.6);
        border: 1px solid rgba(255,255,255,.06);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .cmai-category-header {
        font-weight: 600;
        font-size: 1.05rem;
        margin-bottom: 8px;
    }
    .signal-tag {
        display: inline-block;
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        font-size: 0.72rem;
        padding: 3px 8px;
        border-radius: 4px;
        margin: 2px;
        font-family: monospace;
    }
    .signal-tag-new {
        display: inline-block;
        background: rgba(52, 211, 153, 0.15);
        color: #34d399;
        font-size: 0.72rem;
        padding: 3px 8px;
        border-radius: 4px;
        margin: 2px;
        font-family: monospace;
    }
    .cmai-item-status {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 500;
    }
    .status-detectable { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .status-partial { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
    .status-not-detectable { background: rgba(100, 116, 139, 0.2); color: #94a3b8; }

    /* ---- mode indicator ---- */
    .mode-live { color: #ef4444; font-weight: 600; }
    .mode-offline { color: #22c55e; font-weight: 600; }

    /* ---- keyword alert popup ---- */
    .keyword-alert {
        background: linear-gradient(135deg, #7c3aed 0%, #4c1d95 100%);
        color: #fff;
        padding: 16px 20px;
        border-radius: 12px;
        margin: 12px 0;
        border: 2px solid #a78bfa;
        animation: glow 2s ease-in-out infinite;
    }
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 10px rgba(167, 139, 250, 0.5); }
        50% { box-shadow: 0 0 25px rgba(167, 139, 250, 0.8); }
    }
    .keyword-tag {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 4px 12px;
        border-radius: 20px;
        margin: 4px;
        font-weight: 600;
    }
    .score-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 1.1rem;
    }
    .score-high { background: #ef4444; color: white; }
    .score-medium { background: #f59e0b; color: white; }
    .score-low { background: #22c55e; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  PLOTLY THEME TOKENS
# ════════════════════════════════════════════════════════════════
BG      = "rgba(0,0,0,0)"
GRID    = "rgba(255,255,255,.06)"
FONT_C  = "#94a3b8"
ACCENT  = ["#38bdf8", "#f472b6", "#a78bfa", "#34d399", "#fbbf24", "#fb923c"]

def style_fig(fig, height=280):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(l=0, r=10, t=30, b=0),
        height=height,
        font=dict(family="Inter", color=FONT_C, size=12),
        legend=dict(orientation="h", yanchor="top", y=1.12, xanchor="left", x=0,
                    font=dict(size=11)),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=GRID, gridwidth=1),
        hovermode="x unified",
    )
    return fig

