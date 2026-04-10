"""Nous — Reasoning Integrity Engine.

Launch: streamlit run app.py
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import html as html_lib
from nous import Nous

st.set_page_config(page_title="Nous", page_icon="◎", layout="wide", initial_sidebar_state="collapsed")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESIGN SYSTEM — Vaporwave / Neo-Classical
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;800;900&family=Inter:wght@300;400;500;600;700;800&family=VT323&display=swap');

:root {
    --bg:       #0a0a1a;
    --s1:       #11112a;
    --s2:       #1a1a3a;
    --s3:       #22224a;
    --brd:      #282860;
    --brd2:     #3a3a70;
    --t1:       #e8e8ff;
    --t2:       #a0a0c8;
    --t3:       #6868a0;
    --t4:       #404078;
    --pink:     #ff71ce;
    --cyan:     #01cdfe;
    --purple:   #b967ff;
    --green:    #05ffa1;
    --red:      #ff4466;
    --gold:     #ffcc00;
    --serif:    'Cinzel', Georgia, serif;
    --sans:     'Inter', -apple-system, system-ui, sans-serif;
    --retro:    'VT323', 'Courier New', monospace;
    --r:        10px;
    --r2:       14px;
}

/* ── RESET ── */
.stApp, .stApp > div, .main, .main .block-container,
[data-testid="stAppViewContainer"], [data-testid="stHeader"],
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebar"], .stApp [data-testid="stVerticalBlock"],
.stApp [data-testid="stHorizontalBlock"] {
    background: var(--bg) !important; color: var(--t1) !important;
}
#MainMenu, footer, header, .stDeployButton { visibility:hidden; display:none; }
.block-container { padding-top:0 !important; max-width:1320px; }
*, *::before, *::after { box-sizing:border-box; }

.stApp p, .stApp span, .stApp div, .stApp label, .stApp li,
.stMarkdown, .stMarkdown p, [data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p { color: var(--t1) !important; font-family: var(--sans); }
.stCaption, [data-testid="stCaptionContainer"] p { color: var(--t4) !important; }
h1,h2,h3,h4 { font-family:var(--serif)!important; font-weight:700!important; letter-spacing:0.02em!important; color:var(--t1)!important; }

/* ── BUTTONS ── */
.stButton > button {
    font-family:var(--sans)!important; font-weight:600!important; font-size:0.82rem!important;
    border-radius:var(--r)!important; border:1px solid var(--brd)!important;
    background:var(--s1)!important; color:var(--t1)!important; padding:0.5rem 1.2rem!important;
    transition:all 0.15s ease!important;
}
.stButton > button:hover { border-color:var(--pink)!important; background:var(--s2)!important; box-shadow:0 0 12px rgba(255,113,206,0.15)!important; }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
    background:linear-gradient(135deg, #b967ff, #ff71ce)!important; color:#fff!important; border:none!important; font-weight:700!important;
    text-shadow:0 1px 2px rgba(0,0,0,0.3)!important;
}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover {
    background:linear-gradient(135deg, #a050ee, #ff50be)!important; box-shadow:0 0 20px rgba(185,103,255,0.3)!important;
}

/* ── INPUTS ── */
.stTextArea textarea, .stTextInput input, [data-baseweb="textarea"], [data-baseweb="input"] {
    font-family:var(--sans)!important; background:var(--s1)!important;
    border:1px solid var(--brd)!important; border-radius:var(--r)!important;
    color:var(--t1)!important; font-size:0.86rem!important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color:var(--purple)!important; box-shadow:0 0 0 3px rgba(185,103,255,0.12)!important;
}
.stTextArea label, .stTextInput label { color:var(--t3)!important; font-size:0.76rem!important; }

/* ── SELECT ── */
.stSelectbox label { color:var(--t3)!important; font-size:0.76rem!important; }
.stSelectbox [data-baseweb="select"] > div {
    background:var(--s1)!important; border:1px solid var(--brd)!important; border-radius:var(--r)!important;
}
.stSelectbox [data-baseweb="select"] > div > div { color:var(--t1)!important; }
[data-baseweb="popover"], [data-baseweb="menu"],
[data-baseweb="popover"] li, [data-baseweb="menu"] li {
    background:var(--s1)!important; color:var(--t1)!important;
}
[data-baseweb="popover"] li:hover, [data-baseweb="menu"] li:hover { background:var(--s2)!important; }

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    gap:2px!important; background:var(--s1)!important; border-radius:var(--r)!important;
    padding:3px!important; border:1px solid var(--brd)!important;
}
.stTabs [data-baseweb="tab"] {
    font-size:0.72rem!important; font-weight:600!important; color:var(--t4)!important;
    border-radius:8px!important; padding:7px 13px!important; background:transparent!important;
    font-family:var(--sans)!important;
}
.stTabs [aria-selected="true"] { background:var(--s2)!important; color:var(--t1)!important; }
.stTabs [data-baseweb="tab-panel"] { background:transparent!important; padding-top:14px!important; }
.stTabs [data-baseweb="tab-border"], .stTabs [data-baseweb="tab-highlight"] { display:none!important; }

/* ── EXPANDER ── */
[data-testid="stExpander"] { border:1px solid var(--brd)!important; border-radius:var(--r)!important; background:transparent!important; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary span,
.streamlit-expanderHeader, .streamlit-expanderHeader span {
    color:var(--t3)!important; font-size:0.78rem!important; font-weight:600!important; background:transparent!important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] { background:var(--s1)!important; }

/* ── FILE UPLOAD ── */
[data-testid="stFileUploader"] section {
    background:var(--s1)!important; border:1px dashed var(--brd)!important; border-radius:var(--r)!important;
}
[data-testid="stFileUploader"], [data-testid="stFileUploader"] * { color:var(--t3)!important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-thumb { background:var(--brd); border-radius:3px; }
hr { border-color:var(--brd)!important; }
[data-testid="stAlert"] { border-radius:var(--r)!important; }


/* ═══════════════════════════════════════════════════
   VAPORWAVE COMPONENTS
   ═══════════════════════════════════════════════════ */

/* ── Hero ── */
.hero {
    position:relative; padding:72px 0 48px; overflow:hidden;
    display:flex; align-items:flex-start; justify-content:space-between;
    min-height:540px;
}
.hero-content { position:relative; z-index:3; max-width:560px; }

/* Ambient glow */
.hero-glow {
    position:absolute; top:-120px; right:-80px;
    width:750px; height:750px;
    background:
        radial-gradient(ellipse at 55% 40%, rgba(255,113,206,0.12) 0%, transparent 45%),
        radial-gradient(ellipse at 40% 60%, rgba(1,205,254,0.08) 0%, transparent 40%),
        radial-gradient(ellipse at 65% 25%, rgba(185,103,255,0.06) 0%, transparent 35%);
    filter:blur(60px);
    pointer-events:none; z-index:0;
}

/* Perspective grid floor */
.hero-grid {
    position:absolute; bottom:0; left:0; right:0; height:200px;
    background:
        linear-gradient(rgba(185,103,255,0.08) 1px, transparent 1px),
        linear-gradient(90deg, rgba(185,103,255,0.08) 1px, transparent 1px);
    background-size:40px 40px;
    mask-image:linear-gradient(to top, rgba(0,0,0,0.5) 0%, transparent 100%);
    -webkit-mask-image:linear-gradient(to top, rgba(0,0,0,0.5) 0%, transparent 100%);
    z-index:0; pointer-events:none;
}

/* Bust container */
.hero-statue {
    position:absolute; top:0; right:10px;
    width:440px; height:540px;
    z-index:1; pointer-events:none; overflow:hidden;
    border-radius:16px;
}

/* Bust image — heavy vaporwave duotone */
.hero-bust-img {
    position:absolute; inset:0;
    width:100%; height:100%;
    object-fit:cover; object-position:center 15%;
    filter:grayscale(1) brightness(0.5) contrast(1.3);
    opacity:0.7; z-index:1;
}

/* Pink/cyan duotone tint */
.hero-bust-tint {
    position:absolute; inset:0;
    background:linear-gradient(150deg,
        rgba(255,113,206,0.35) 0%,
        rgba(185,103,255,0.2) 40%,
        rgba(1,205,254,0.25) 80%,
        rgba(255,113,206,0.1) 100%);
    mix-blend-mode:color; z-index:2;
}

/* Animated scanlines */
.hero-bust-scan {
    position:absolute; inset:0;
    background:repeating-linear-gradient(
        0deg,
        transparent 0px, transparent 2px,
        rgba(255,113,206,0.04) 2px, rgba(255,113,206,0.04) 3px
    );
    z-index:3; pointer-events:none;
    animation:scan-drift 12s linear infinite;
}
@keyframes scan-drift {
    0% { transform:translateY(0); }
    100% { transform:translateY(30px); }
}

/* Chromatic aberration glow on bust edges */
.hero-bust-chroma {
    position:absolute; inset:0;
    box-shadow:
        inset 3px 0 20px rgba(255,113,206,0.15),
        inset -3px 0 20px rgba(1,205,254,0.15);
    z-index:4; pointer-events:none;
}

/* Fade edges into background */
.hero-statue::after {
    content:'';
    position:absolute; inset:0;
    background:
        linear-gradient(to right, var(--bg) 0%, transparent 20%, transparent 85%, var(--bg) 100%),
        linear-gradient(to bottom, var(--bg) 0%, transparent 12%, transparent 75%, var(--bg) 100%);
    z-index:5; pointer-events:none;
}

/* Nous title — chrome/metallic gradient */
.hero-name {
    font-family:var(--serif); font-size:5rem; font-weight:900;
    letter-spacing:0.06em; line-height:1;
    background:linear-gradient(
        180deg,
        #e8e8ff 0%, #fff 15%, #b0b0d0 30%,
        #fff 45%, #c0c0e0 55%, #e8e8ff 70%,
        #b0b0d0 85%, #e8e8ff 100%
    );
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    filter:drop-shadow(0 0 20px rgba(185,103,255,0.3)) drop-shadow(0 2px 4px rgba(0,0,0,0.5));
    margin-bottom:8px; position:relative;
}

/* Tagline in retro font */
.hero-tag {
    font-family:var(--retro); font-size:1.3rem; color:var(--cyan);
    letter-spacing:0.15em; text-transform:uppercase; margin-bottom:28px;
    text-shadow:0 0 8px rgba(1,205,254,0.4), 0 0 20px rgba(1,205,254,0.15);
}

.hero-desc {
    font-size:1rem; font-weight:400; color:var(--t2); line-height:1.7;
    max-width:520px; margin-bottom:12px;
}
.hero-sub {
    font-family:var(--retro); font-size:0.95rem; color:var(--t4);
    letter-spacing:0.06em; margin-bottom:32px;
}
.hero-badge {
    display:inline-block; font-family:var(--retro); font-size:0.85rem;
    color:var(--purple); letter-spacing:0.1em;
    padding:5px 16px; border:1px solid rgba(185,103,255,0.25); border-radius:100px;
    margin-top:14px;
    text-shadow:0 0 6px rgba(185,103,255,0.3);
}

/* Graph overlay on bust */
.hero-graph-overlay {
    position:absolute; inset:0; z-index:4; pointer-events:none;
}

/* ── Section ── */
.sec { padding:52px 0 0; }
.sec-h {
    font-family:var(--retro); font-size:0.9rem; color:var(--pink);
    text-transform:uppercase; letter-spacing:0.2em;
    margin-bottom:8px;
    text-shadow:0 0 6px rgba(255,113,206,0.3);
}
.sec-title {
    font-family:var(--serif); font-size:1.5rem; font-weight:700; color:var(--t1);
    letter-spacing:0.02em; margin-bottom:6px;
}
.sec-sub {
    font-size:0.88rem; color:var(--t3); max-width:620px;
    line-height:1.55; margin-bottom:28px;
}

/* ── Card ── */
.card {
    background:var(--s1); border:1px solid var(--brd);
    border-radius:var(--r2); padding:28px 24px;
    transition:all 0.2s; height:100%;
}
.card:hover { border-color:var(--brd2); box-shadow:0 0 20px rgba(185,103,255,0.06); }
.card-label {
    font-family:var(--retro); font-size:0.85rem; text-transform:uppercase;
    letter-spacing:0.12em; margin-bottom:10px;
}
.card-title {
    font-family:var(--serif); font-size:0.95rem; font-weight:700; color:var(--t1);
    margin-bottom:8px;
}
.card-body { font-size:0.8rem; color:var(--t3); line-height:1.6; }
.card-code {
    font-family:var(--retro); font-size:0.85rem; color:var(--cyan);
    margin-top:12px; display:inline-block;
    padding:4px 12px; background:rgba(1,205,254,0.06);
    border-radius:6px;
    text-shadow:0 0 4px rgba(1,205,254,0.2);
}

/* ── Philosopher card ── */
.phil {
    background:var(--s1); border:1px solid var(--brd);
    border-radius:var(--r2); padding:24px 22px; height:100%;
    transition:all 0.2s; position:relative; overflow:hidden;
}
.phil:hover { border-color:var(--brd2); }
.phil::before {
    content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background:linear-gradient(90deg, var(--pink), var(--purple), var(--cyan));
    opacity:0.5;
}
.phil-era {
    font-family:var(--retro); font-size:0.85rem; color:var(--pink);
    letter-spacing:0.08em; margin-bottom:4px;
    text-shadow:0 0 4px rgba(255,113,206,0.2);
}
.phil-name {
    font-family:var(--serif); font-size:1rem; font-weight:700;
    color:var(--t1); margin-bottom:4px;
}
.phil-concept {
    font-family:var(--retro); font-size:0.85rem; color:var(--cyan);
    margin-bottom:10px; text-shadow:0 0 4px rgba(1,205,254,0.2);
}
.phil-body { font-size:0.78rem; color:var(--t3); line-height:1.55; }
.phil-impl {
    font-size:0.72rem; color:var(--purple); margin-top:10px;
    padding:6px 10px; background:rgba(185,103,255,0.05);
    border-radius:6px; border-left:2px solid rgba(185,103,255,0.2);
}

/* ── Scenario card ── */
.sc {
    background:var(--s1); border:1px solid var(--brd);
    border-radius:var(--r2); padding:20px;
    transition:all 0.2s;
}
.sc:hover { border-color:var(--brd2); box-shadow:0 0 16px rgba(185,103,255,0.06); }
.sc-domain {
    font-family:var(--retro); font-size:0.85rem;
    letter-spacing:0.12em; color:var(--pink); margin-bottom:6px;
    text-shadow:0 0 4px rgba(255,113,206,0.2);
}
.sc-title { font-family:var(--serif); font-size:0.92rem; font-weight:700; color:var(--t1); margin-bottom:5px; }
.sc-desc { font-size:0.78rem; color:var(--t3); line-height:1.45; margin-bottom:10px; }
.sc-watch {
    font-size:0.72rem; color:var(--t4); line-height:1.45;
    padding:8px 10px; background:rgba(185,103,255,0.04); border-radius:8px;
    border-left:2px solid rgba(185,103,255,0.15);
}
.sc-watch b { color:var(--red); font-weight:600; }

/* ── Metrics strip ── */
.metrics {
    display:grid; grid-template-columns:repeat(5,1fr);
    gap:1px; background:var(--brd); border:1px solid var(--brd);
    border-radius:var(--r2); overflow:hidden; margin:0 0 20px;
}
.mc { background:var(--bg); padding:16px 8px; text-align:center; }
.mv {
    font-family:var(--retro); font-size:2rem; font-weight:400;
    letter-spacing:0.02em; line-height:1; color:var(--t1);
}
.mv.ok { color:var(--green); text-shadow:0 0 8px rgba(5,255,161,0.3); }
.mv.warn { color:var(--gold); text-shadow:0 0 8px rgba(255,204,0,0.3); }
.mv.bad { color:var(--red); text-shadow:0 0 8px rgba(255,68,102,0.3); }
.ml {
    font-family:var(--retro); font-size:0.8rem; color:var(--t4);
    letter-spacing:0.06em; margin-top:5px;
}

/* ── Step card ── */
.stp {
    border:1px solid var(--brd); border-radius:var(--r);
    padding:14px 18px; margin:6px 0; background:var(--s1);
    transition:all 0.15s;
}
.stp:hover { border-color:var(--brd2); }
.stp.v {
    background:rgba(255,68,102,0.04); border-color:rgba(255,68,102,0.2);
    animation:violation-enter 0.5s ease-out forwards;
}
.stp.p { border-style:dashed; opacity:0.4; }
.stp-h { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.stp-n {
    font-family:var(--retro); font-size:0.85rem;
    padding:2px 10px; border-radius:100px;
}
.stp-n.ok { color:var(--green); background:rgba(5,255,161,0.08); }
.stp-n.bad { color:var(--red); background:rgba(255,68,102,0.08); }
.stp-n.wait { color:var(--t4); background:rgba(64,64,120,0.1); }
.stp-b { font-size:0.86rem; color:var(--t2); line-height:1.5; }
.stp-a {
    font-family:var(--retro); font-size:0.9rem; color:var(--t4);
    margin-top:6px; padding:5px 10px; background:rgba(255,255,255,0.015);
    border-radius:6px; border:1px solid rgba(255,255,255,0.03);
}

/* ── Violation block ── */
@keyframes violation-enter {
    0% { opacity:0; transform:translateY(4px); box-shadow:none; }
    50% { box-shadow:0 0 30px rgba(255,68,102,0.15); }
    100% { opacity:1; transform:translateY(0); box-shadow:0 0 12px rgba(255,68,102,0.06); }
}
.vb { margin-top:10px; padding-top:10px; border-top:1px solid rgba(255,68,102,0.1); }
.vb-t { font-family:var(--retro); font-size:0.95rem; color:var(--red); text-shadow:0 0 6px rgba(255,68,102,0.3); }
.vb-c { font-size:0.8rem; color:#ff8899; margin-top:3px; line-height:1.4; }
.vb-x {
    margin-top:8px; padding:10px 12px;
    background:rgba(255,68,102,0.03); border:1px solid rgba(255,68,102,0.08);
    border-radius:8px;
}
.vb-axiom { font-family:var(--retro); font-size:0.8rem; color:var(--t4); letter-spacing:0.06em; margin-bottom:3px; }
.vb-form { font-family:var(--retro); font-size:0.9rem; color:var(--red); margin-bottom:2px; text-shadow:0 0 4px rgba(255,68,102,0.2); }
.vb-plain { font-size:0.78rem; color:var(--t2); line-height:1.4; }
.vb-lean { font-family:var(--retro); font-size:0.8rem; color:var(--t4); margin-top:3px; }

/* ── Section label ── */
.sl {
    font-family:var(--retro); font-size:0.85rem; color:var(--t4);
    letter-spacing:0.08em;
    margin:16px 0 10px; padding-bottom:6px;
    border-bottom:1px solid var(--brd);
}

/* ── Query item ── */
.qi {
    font-size:0.82rem; color:var(--t2); padding:8px 0;
    border-bottom:1px solid rgba(255,255,255,0.03); line-height:1.4;
}
.qi:last-child { border-bottom:none; }

/* ── Hypothetical box ── */
.hbox {
    padding:14px 16px; background:rgba(185,103,255,0.04);
    border:1px solid rgba(185,103,255,0.12); border-radius:var(--r);
    margin-top:8px;
}
.htag {
    font-family:var(--retro); font-size:0.85rem;
    padding:2px 10px; border-radius:100px; display:inline-block; margin:5px 0;
}
.htag.new { color:var(--purple); background:rgba(185,103,255,0.08); }
.htag.ok { color:var(--green); background:rgba(5,255,161,0.06); }
.htag.bad { color:var(--red); background:rgba(255,68,102,0.06); }

/* ── Dependencies ── */
.dep {
    font-size:0.8rem; color:var(--t2); padding:6px 12px; margin:3px 0;
    background:rgba(185,103,255,0.03); border-left:2px solid var(--brd);
    border-radius:0 8px 8px 0;
}
.weak {
    padding:12px 14px; background:rgba(255,204,0,0.05);
    border:1px solid rgba(255,204,0,0.12); border-radius:var(--r);
    color:var(--gold); font-size:0.82rem;
}

/* ── Strength bars ── */
.str-r { display:flex; align-items:center; gap:10px; margin:5px 0; }
.str-l { font-size:0.7rem; color:var(--t4); width:105px; text-align:right; }
.str-b { flex:1; height:4px; background:var(--s2); border-radius:2px; overflow:hidden; }
.str-f { height:100%; border-radius:2px; }
.str-p { font-family:var(--retro); font-size:0.85rem; color:var(--t3); width:40px; }

/* ── Diff ── */
.dfs { padding:5px 12px; margin:2px 0; background:rgba(5,255,161,0.04); border-left:3px solid var(--green); border-radius:0 8px 8px 0; font-size:0.8rem; color:#70ffb8; }
.dfl { padding:5px 12px; margin:2px 0; background:rgba(185,103,255,0.04); border-left:3px solid var(--purple); border-radius:0 8px 8px 0; font-size:0.8rem; color:#c8a0ff; }
.dfr { padding:5px 12px; margin:2px 0; background:rgba(255,204,0,0.04); border-left:3px solid var(--gold); border-radius:0 8px 8px 0; font-size:0.8rem; color:#ffe066; }

/* ── Pipeline cards ── */
.pipe {
    background:var(--s1); border:1px solid var(--brd); border-radius:var(--r2);
    padding:24px 20px; text-align:center; height:100%; position:relative;
}
.pipe-num {
    font-family:var(--retro); font-size:2.5rem; line-height:1;
    background:linear-gradient(135deg, var(--pink), var(--cyan));
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:10px;
}
.pipe-title { font-family:var(--serif); font-size:0.88rem; font-weight:700; color:var(--t1); margin-bottom:6px; }
.pipe-body { font-size:0.76rem; color:var(--t3); line-height:1.55; }
.pipe-arrow {
    position:absolute; top:50%; right:-18px;
    font-family:var(--retro); font-size:1.6rem;
    color:var(--pink); transform:translateY(-50%); z-index:2;
    text-shadow:0 0 6px rgba(255,113,206,0.3);
}

/* ── Audience ── */
.aud {
    background:var(--s1); border:1px solid var(--brd);
    border-radius:var(--r2); padding:24px; height:100%;
}
.aud-title { font-family:var(--serif); font-size:0.88rem; font-weight:700; color:var(--t1); margin-bottom:4px; }
.aud-body { font-size:0.78rem; color:var(--t3); line-height:1.5; }

/* ── Differentiator ── */
.diff-card {
    background:var(--s1); border:1px solid var(--brd); border-radius:var(--r2);
    padding:20px; height:100%; position:relative;
}
.diff-card.us { border-color:rgba(5,255,161,0.2); }
.diff-card.us::before {
    content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background:linear-gradient(90deg, var(--green), var(--cyan));
}
.diff-them { font-family:var(--retro); font-size:0.85rem; color:var(--t4); margin-bottom:4px; }
.diff-title { font-family:var(--serif); font-size:0.9rem; font-weight:700; color:var(--t1); margin-bottom:6px; }
.diff-body { font-size:0.76rem; color:var(--t3); line-height:1.5; }

/* ── Footer ── */
.foot {
    text-align:center; padding:48px 0 24px;
    border-top:1px solid var(--brd); margin-top:52px;
}
.foot-main {
    font-family:var(--serif); font-size:1rem; font-weight:700;
    color:var(--t2); letter-spacing:0.02em; margin-bottom:6px;
}
.foot-sub { font-family:var(--retro); font-size:0.9rem; color:var(--t4); }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VIOLATION EXPLAINERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VIOLATION_EXPLAINERS = {
    "ModusPonensViolation": {
        "formal": "K(P) ∧ K(P→Q) → K(Q)",
        "axiom": "Epistemic Closure · Kripke Axiom K",
        "plain": "The agent committed to P and P implies Q, but then acted as if Q were false.",
        "lean": "epistemic_closure in ClosureViolation.lean",
    },
    "BeliefRevisionFailure": {
        "formal": "AGM contraction postulate",
        "axiom": "AGM Belief Revision",
        "plain": "New evidence contradicted a prior belief, but the agent didn't revise.",
        "lean": "revision_failure_breaks_consistency",
    },
    "ModalScopeError": {
        "formal": "◇P ⊬ □P",
        "axiom": "Modal Logic · Kripke S5",
        "plain": "Something was only possible, but was treated as certain.",
        "lean": "modal_scope_error_detection",
    },
    "TemporalCoherenceViolation": {
        "formal": "K_t(P) ∧ update(¬P, t') → ¬K_{t'}(P)",
        "axiom": "Temporal Epistemic Logic",
        "plain": "A time-stamped fact was updated but the agent kept using the old version.",
        "lean": "temporal_coherence_check",
    },
    "ReferentialOpacityFailure": {
        "formal": "K(a=b) ∧ K(F(a)) ⊬ K(F(b))",
        "axiom": "Referential Opacity · Frege",
        "plain": "Two names refer to the same thing, but the agent didn't transfer knowledge between them.",
        "lean": "referential_opacity_detection",
    },
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

for key, val in [
    ("nous", None), ("steps", []), ("results", []), ("mode", "landing"),
    ("eq", []), ("ec", 0), ("ek", None), ("hyp", None), ("hl", None),
    ("dl", None), ("dr", None),
]:
    if key not in st.session_state:
        st.session_state[key] = Nous() if key == "nous" else val

n = st.session_state.nous

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXAMPLES — text must match backend fixtures exactly
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXAMPLES = {
    "catalyst": {
        "icon": "⚗️", "title": "Air-Sensitive Catalyst", "domain": "Chemistry",
        "desc": "A lab agent records that a palladium catalyst is oxygen-sensitive, transfers it under nitrogen, then opens the flask to air.",
        "watch": "Nous builds entailment from 'air-sensitive' to 'must avoid oxygen', then catches the ModusPonensViolation when the flask is opened.",
        "steps": [
            ("The palladium catalyst is air-sensitive and must be handled under inert atmosphere (N2 or Ar). Exposure to oxygen will deactivate it.", "Note catalyst handling requirements."),
            ("Weigh 50mg of catalyst in the glovebox and transfer to the Schlenk flask under nitrogen.", "Transfer catalyst to reaction vessel."),
            ("Add the substrate and solvent. To ensure complete mixing, briefly open the flask to air to add the reagent via syringe.", "Open flask to air to add reagent."),
        ],
    },
    "math": {
        "icon": "∫", "title": "Assumption Drift", "domain": "Mathematics",
        "desc": "A proof establishes continuity, then silently assumes differentiability without proof.",
        "watch": "Step 2 applies IVT from continuity. Step 3 jumps to differentiability — a stronger property never established. Nous flags the gap.",
        "steps": [
            ("Function f is continuous on the closed interval [a,b]. This follows from the composition of continuous functions.", "Establish continuity of f on [a,b]."),
            ("By the Intermediate Value Theorem, since f is continuous on [a,b] and f(a) < 0 < f(b), there exists c in (a,b) with f(c) = 0.", "Apply IVT to locate root."),
            ("To find extrema, I need to find critical points. Since f is differentiable everywhere on (a,b), I can compute f'(x) and set it to zero.", "Differentiate f on (a,b) to find critical points."),
        ],
    },
    "drug": {
        "icon": "🧬", "title": "Contradictory Recommendation", "domain": "Drug Discovery",
        "desc": "An agent derives that compound X impairs pathway Z, then recommends X to enhance Z.",
        "watch": "Steps 1-3 build a chain: X inhibits Y, Y required for Z, so X impairs Z. Step 4 directly contradicts the derived conclusion.",
        "steps": [
            ("Paper A (Chen et al. 2024) reports that compound X is a potent inhibitor of kinase Y, with IC50 = 12nM.", "Review literature on compound X."),
            ("Paper B (Zhang et al. 2025) shows that kinase Y is essential for activating pathway Z. Knockout of kinase Y abolishes pathway Z activity entirely.", "Record kinase Y role in pathway Z."),
            ("Synthesizing these findings: since X inhibits Y, and Y is required for Z, compound X would impair pathway Z signaling.", "Derive effect of X on pathway Z."),
            ("Based on the literature, we recommend compound X as a potential enhancer of pathway Z for therapeutic applications.", "Recommend X to enhance pathway Z."),
        ],
    },
    "code": {
        "icon": "⟨⟩", "title": "JSON Parsing Error", "domain": "Code Agent",
        "desc": "An agent reads that an API returns JSON, acknowledges it needs parsing, then splits the response by commas.",
        "watch": "The agent commits to 'response is JSON' and 'JSON needs parsing', then acts as if the response is plain text.",
        "steps": [
            ("The API documentation confirms the endpoint returns JSON.", "Send GET request to the endpoint."),
            ("JSON responses need to be parsed before accessing fields.", "Store the response body."),
            ("Let me extract the 'name' field from the response.", "Split response string by commas to find name."),
        ],
    },
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ACTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def start_example(key, step_by_step=False):
    """Load an example. By default runs all steps so user sees the full result."""
    st.session_state.nous = Nous()
    st.session_state.steps, st.session_state.results = [], []
    st.session_state.ek = key
    st.session_state.hyp, st.session_state.hl = None, None
    nn = st.session_state.nous
    all_steps = EXAMPLES[key]["steps"]
    if step_by_step:
        r, a = all_steps[0]
        res = nn.step(r, a, test_mode=True)
        st.session_state.steps.append((r, a))
        st.session_state.results.append(res)
        st.session_state.ec = 1
        st.session_state.eq = list(all_steps[1:])
    else:
        for r, a in all_steps:
            res = nn.step(r, a, test_mode=True)
            st.session_state.steps.append((r, a))
            st.session_state.results.append(res)
        st.session_state.ec = len(all_steps)
        st.session_state.eq = []
    st.session_state.mode = "analysis"

def advance():
    if not st.session_state.eq:
        return
    r, a = st.session_state.eq.pop(0)
    res = st.session_state.nous.step(r, a, test_mode=True)
    st.session_state.steps.append((r, a))
    st.session_state.results.append(res)
    st.session_state.ec += 1

def play_all():
    while st.session_state.eq:
        advance()

def replay_step_by_step():
    """Reset current example to step-by-step mode."""
    key = st.session_state.ek
    if key and key in EXAMPLES:
        start_example(key, step_by_step=True)

def go_home():
    st.session_state.nous = Nous()
    for k, v in [("steps", []), ("results", []), ("mode", "landing"), ("eq", []),
                 ("ec", 0), ("ek", None), ("hyp", None), ("hl", None),
                 ("dl", None), ("dr", None)]:
        st.session_state[k] = v

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GRAPH RENDERER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_graph(graph, highlight=None, height=400):
    njs, ejs, nm = [], [], {}
    cl = graph.get_closure()

    for i, (c, nd) in enumerate(graph.nodes.items()):
        nm[c] = i
        lb = (c[:40] + "...") if len(c) > 40 else c
        iv = any(v.violated_node.content == c for v in graph.violations)
        ih = highlight and c == highlight

        if ih:
            bg, bd, fc, sh, bw = "#1a1a00", "#ffcc00", "#ffe066", "rgba(255,204,0,0.3)", 2.5
        elif iv:
            bg, bd, fc, sh, bw = "#1a0010", "#ff4466", "#ff8899", "rgba(255,68,102,0.25)", 2
        elif nd.is_explicit:
            bg, bd, fc, sh, bw = "#0d0d2a", "#b967ff", "#c8a0ff", "rgba(185,103,255,0.12)", 1.5
        else:
            bg, bd, fc, sh, bw = "#0a0a18", "#282860", "#6868a0", "rgba(0,0,0,0)", 1

        tp = html_lib.escape(c) + " | Step " + str(nd.source_step) + " | " + ("Explicit" if nd.is_explicit else "Derived") + " | " + nd.modality + (" | In closure" if c in cl else "")
        njs.append({
            "id": i, "label": lb, "title": tp,
            "color": {"background": bg, "border": bd, "highlight": {"background": bg, "border": bd}},
            "font": {"color": fc, "face": "Inter,system-ui", "size": 11},
            "shape": "box", "borderWidth": bw, "borderWidthSelected": 3,
            "shapeProperties": {"borderRadius": 7},
            "margin": {"top": 10, "bottom": 10, "left": 14, "right": 14},
            "shadow": {"enabled": True, "color": sh, "size": 18 if (iv or ih) else 6, "x": 0, "y": 2},
        })

    for e in graph.edges:
        if e.premise.content in nm and e.consequence.content in nm:
            iv = any(v.violated_node.content == e.consequence.content for v in graph.violations)
            w = max(0.8, e.confidence * 3)
            op = 0.3 + e.confidence * 0.6
            ec = "#ff4466" if iv else "#3a3a70"
            tp = f"{e.rule} | {e.confidence:.0%}"
            ejs.append({
                "from": nm[e.premise.content], "to": nm[e.consequence.content],
                "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}},
                "color": {"color": ec, "highlight": ec, "opacity": op},
                "width": w, "smooth": {"type": "curvedCW", "roundness": 0.1},
                "dashes": (not iv and e.rule not in ("modus_ponens", "derived")),
                "title": tp,
            })

    components.html(f"""<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap" rel="stylesheet">
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
*{{margin:0;padding:0}}body{{background:#0a0a1a;overflow:hidden;font-family:Inter,sans-serif}}
#g{{width:100%;height:100vh}}
.vis-tooltip{{background:#11112a!important;color:#e8e8ff!important;border:1px solid #282860!important;
border-radius:8px!important;padding:8px 12px!important;font-size:11px!important;line-height:1.4!important;
box-shadow:0 4px 16px rgba(0,0,0,0.5)!important;max-width:280px!important;font-family:Inter,sans-serif!important}}
</style></head><body><div id="g"></div><script>
new vis.Network(document.getElementById('g'),
{{nodes:new vis.DataSet({json.dumps(njs)}),edges:new vis.DataSet({json.dumps(ejs)})}},
{{physics:{{solver:'forceAtlas2Based',forceAtlas2Based:{{gravitationalConstant:-40,centralGravity:0.005,springLength:150,springConstant:0.04,damping:0.5,avoidOverlap:0.85}},stabilization:{{iterations:180}},maxVelocity:18}},
interaction:{{hover:true,tooltipDelay:80,zoomView:true,dragView:true,dragNodes:true,zoomSpeed:0.25}},
layout:{{improvedLayout:true}}}});
</script></body></html>""", height=height)


def esc(s, lim=300):
    return html_lib.escape(s[:lim]) + ("..." if len(s) > lim else "")


# ██████████████████████████████████████████████████████████████████████
# LANDING PAGE
# ██████████████████████████████████████████████████████████████████████
if st.session_state.mode == "landing":

    # ── 1. HERO ──
    BUST_URL = "https://upload.wikimedia.org/wikipedia/commons/a/ae/Aristotle_Altemps_Inv8575.jpg"

    GRAPH_SVG = """<svg viewBox="0 0 400 500" class="hero-graph-overlay">
      <circle cx="85" cy="75" r="10" fill="none" stroke="#ff71ce" stroke-width="1.2" opacity="0.6"/>
      <text x="85" y="79" text-anchor="middle" font-family="VT323,monospace" font-size="11" fill="#ff71ce" opacity="0.7">P</text>
      <circle cx="315" cy="55" r="10" fill="none" stroke="#01cdfe" stroke-width="1" opacity="0.5"/>
      <text x="315" y="59" text-anchor="middle" font-family="VT323,monospace" font-size="10" fill="#01cdfe" opacity="0.6">P→Q</text>
      <circle cx="340" cy="200" r="10" fill="none" stroke="#b967ff" stroke-width="1" opacity="0.5"/>
      <text x="340" y="204" text-anchor="middle" font-family="VT323,monospace" font-size="11" fill="#b967ff" opacity="0.6">Q</text>
      <circle cx="55" cy="340" r="11" fill="none" stroke="#ff4466" stroke-width="1.5" opacity="0.55"/>
      <text x="55" y="344" text-anchor="middle" font-family="VT323,monospace" font-size="10" fill="#ff4466" opacity="0.65">¬Q</text>
      <circle cx="350" cy="380" r="8" fill="none" stroke="#ff71ce" stroke-width="0.8" opacity="0.3"/>
      <text x="350" y="383" text-anchor="middle" font-family="VT323,monospace" font-size="9" fill="#ff71ce" opacity="0.4">K(P)</text>
      <circle cx="160" cy="440" r="8" fill="none" stroke="#01cdfe" stroke-width="0.8" opacity="0.25"/>
      <text x="160" y="443" text-anchor="middle" font-family="VT323,monospace" font-size="9" fill="#01cdfe" opacity="0.35">◇R</text>
      <line x1="95" y1="75" x2="305" y2="57" stroke="#ff71ce" stroke-width="0.8" opacity="0.25" stroke-dasharray="4,5"/>
      <line x1="315" y1="65" x2="338" y2="190" stroke="#01cdfe" stroke-width="0.7" opacity="0.2" stroke-dasharray="4,5"/>
      <line x1="85" y1="85" x2="59" y2="329" stroke="#ff4466" stroke-width="0.9" opacity="0.2" stroke-dasharray="3,4"/>
      <path d="M85,75 Q200,25 315,55" fill="none" stroke="#b967ff" stroke-width="0.5" opacity="0.12" stroke-dasharray="6,8"/>
      <circle cx="55" cy="340" r="17" fill="none" stroke="#ff4466" stroke-width="0.5" opacity="0.18">
        <animate attributeName="r" values="17;23;17" dur="3s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.18;0.06;0.18" dur="3s" repeatCount="indefinite"/>
      </circle>
      <text x="30" y="370" font-family="VT323,monospace" font-size="9" fill="#ff4466" opacity="0.35" letter-spacing="1.5">VIOLATION</text>
    </svg>"""

    st.markdown(f"""
    <div class="hero">
        <div class="hero-glow"></div>
        <div class="hero-grid"></div>
        <div class="hero-statue">
            <img src="{BUST_URL}" alt="" class="hero-bust-img"/>
            <div class="hero-bust-tint"></div>
            <div class="hero-bust-scan"></div>
            <div class="hero-bust-chroma"></div>
            {GRAPH_SVG}
        </div>
        <div class="hero-content">
            <div class="hero-name">NOUS</div>
            <div class="hero-tag">Reasoning Integrity Engine</div>
            <div class="hero-desc">
                Databases made text queryable. Git made code branchable.
                <b style="color:var(--t1)">Nous makes reasoning inspectable.</b>
                <br><br>
                Feed it any reasoning trace and it builds a
                <b style="color:#c8a0ff">commitment graph</b> — what was asserted,
                what follows, and where the logic breaks.
            </div>
            <div class="hero-sub">Graph algorithms · Not generated explanations · Lean 4 verified</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Hero CTA — working Streamlit buttons
    hc1, hc2, hc3 = st.columns([1.5, 1.5, 3.5])
    with hc1:
        if st.button("Try the catalyst demo", type="primary", use_container_width=True, key="h_try"):
            start_example("catalyst")
            st.rerun()
    with hc2:
        if st.button("Pick a scenario", use_container_width=True, key="h_pick"):
            start_example("drug")
            st.rerun()

    st.markdown('<div class="hero-badge">GRAPH · KRIPKE · LEAN 4 · O(V+E)</div>', unsafe_allow_html=True)


    # ── 2. THE IDEA (simple explanation) ──
    st.markdown("""
    <div style="padding:40px 0 0; max-width:720px;">
        <div class="sec-h">The Idea</div>
        <div style="font-family:var(--serif);font-size:1.4rem;font-weight:700;color:var(--t1);line-height:1.5;margin-bottom:12px;">
            Every assertion carries invisible obligations.
        </div>
        <div style="font-size:0.92rem;color:var(--t2);line-height:1.75;">
            When an AI agent says "the catalyst is air-sensitive," it has <em>committed</em> itself —
            implicitly, logically — to "exposing the catalyst to air will damage it." Even if it never
            says so. These hidden obligations are called <b style="color:var(--t1)">inferential commitments</b>.
            <br><br>
            Nous tracks them. It builds a graph of everything an agent has asserted and everything
            that follows. When the agent acts against its own commitments — opening the flask to air,
            recommending a drug it just proved is harmful — the violation shows up as a
            <b style="color:var(--red)">path in the graph</b>. Not a heuristic. Not a guess. A formal proof
            that the reasoning broke.
        </div>
    </div>
    """, unsafe_allow_html=True)


    # ── 3. STANDING ON GIANTS (philosopher cards) ──
    st.markdown("""
    <div class="sec">
        <div class="sec-h">Standing on Giants</div>
        <div class="sec-title">2,300 years of philosophy, made computational</div>
        <div class="sec-sub">Every feature in Nous traces back to a formal result in epistemology or logic. This isn't decoration — it's the foundation.</div>
    </div>
    """, unsafe_allow_html=True)

    ph1, ph2, ph3 = st.columns(3)
    with ph1:
        st.markdown("""<div class="phil">
            <div class="phil-era">384 BC · ANCIENT GREECE</div>
            <div class="phil-name">Aristotle</div>
            <div class="phil-concept">Epistemic Closure</div>
            <div class="phil-body">
                If you know P, and P implies Q, then you're committed to Q — whether you
                realize it or not. This is the basic law of rational thought. An agent that
                asserts P and then acts as if Q is false is <em>incoherent</em>, not just
                "wrong."
            </div>
            <div class="phil-impl">Nous: Commitment closure via BFS. Every assertion's consequences are computed automatically.</div>
        </div>""", unsafe_allow_html=True)
    with ph2:
        st.markdown("""<div class="phil">
            <div class="phil-era">1959 · MODAL LOGIC</div>
            <div class="phil-name">Saul Kripke</div>
            <div class="phil-concept">Possible Worlds</div>
            <div class="phil-body">
                "What if this were true?" Kripke formalized hypothetical reasoning as
                exploring possible worlds — alternate realities branching from the current one.
                You can explore consequences without committing, then return to reality.
            </div>
            <div class="phil-impl">Nous: suppose() creates a branch, you explore it, consequences are computed, then auto-rollback.</div>
        </div>""", unsafe_allow_html=True)
    with ph3:
        st.markdown("""<div class="phil">
            <div class="phil-era">1994 · INFERENTIALISM</div>
            <div class="phil-name">Robert Brandom</div>
            <div class="phil-concept">Inferential Commitment</div>
            <div class="phil-body">
                The meaning of a claim IS its inferential role — what it commits you to
                and what it rules out. Saying "the server is down" commits you to "queries
                will fail." If you then query the server, you've contradicted yourself.
            </div>
            <div class="phil-impl">Nous: The commitment graph tracks exactly what each assertion commits you to and checks actions against it.</div>
        </div>""", unsafe_allow_html=True)


    # ── 4. WHAT MAKES THIS DIFFERENT ──
    st.markdown("""
    <div class="sec">
        <div class="sec-h">Why This Is Different</div>
        <div class="sec-title">Not another consistency checker</div>
        <div class="sec-sub">Existing tools ask "is this output consistent?" Nous asks a deeper question: "what is this agent committed to, and did it honor those commitments?"</div>
    </div>
    """, unsafe_allow_html=True)

    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown("""<div class="diff-card">
            <div class="diff-them">EXISTING TOOLS</div>
            <div class="diff-title">Sample and compare</div>
            <div class="diff-body">SelfCheckGPT, G-Eval, etc. generate multiple outputs and check agreement. Statistical. No formal guarantee. Can't explain WHY something is wrong.</div>
        </div>""", unsafe_allow_html=True)
    with d2:
        st.markdown("""<div class="diff-card">
            <div class="diff-them">EXISTING TOOLS</div>
            <div class="diff-title">Check surface text</div>
            <div class="diff-body">Look for contradictions in the literal text. Miss inferential commitments entirely. "Air-sensitive" and "open to air" don't share words — but they contradict.</div>
        </div>""", unsafe_allow_html=True)
    with d3:
        st.markdown("""<div class="diff-card us">
            <div class="diff-them" style="color:var(--green)">NOUS</div>
            <div class="diff-title">Build the graph, query it</div>
            <div class="diff-body">Reasoning becomes a data structure. Violations are paths in a graph. You can query foundations, trace dependencies, explore hypotheticals, diff two reasoning chains. Verified in Lean 4.</div>
        </div>""", unsafe_allow_html=True)


    # ── 5. HOW IT WORKS ──
    st.markdown("""
    <div class="sec">
        <div class="sec-h">How It Works</div>
        <div class="sec-title">Three operations. No magic.</div>
    </div>
    """, unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown("""<div class="pipe">
            <div class="pipe-num">1</div>
            <div class="pipe-title">Feed reasoning</div>
            <div class="pipe-body">From any source — AI agent, human proof, lab protocol, medical diagnosis. Natural language in, structured graph out.</div>
            <div class="pipe-arrow">→</div>
        </div>""", unsafe_allow_html=True)
    with p2:
        st.markdown("""<div class="pipe">
            <div class="pipe-num">2</div>
            <div class="pipe-title">Build the graph</div>
            <div class="pipe-body">Extract commitments, compute entailment edges, build the closure — everything you're logically bound to. Deterministic, O(V+E).</div>
            <div class="pipe-arrow">→</div>
        </div>""", unsafe_allow_html=True)
    with p3:
        st.markdown("""<div class="pipe">
            <div class="pipe-num">3</div>
            <div class="pipe-title">Surface violations</div>
            <div class="pipe-body">Violations emerge as graph properties — paths from assertion to contradiction. Each classified by formal axiom. Structure, not opinion.</div>
        </div>""", unsafe_allow_html=True)


    # ── 6. CAPABILITIES ──
    st.markdown("""
    <div class="sec">
        <div class="sec-h">Capabilities</div>
        <div class="sec-title">What you can do with this</div>
    </div>
    """, unsafe_allow_html=True)

    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        st.markdown("""<div class="card">
            <div class="card-label" style="color:var(--purple);">Inspect</div>
            <div class="card-title">See the reasoning structure</div>
            <div class="card-body">What did the agent commit to? What follows? What are foundations vs. derived conclusions? All computed by graph traversal, not by asking another LLM.</div>
            <div class="card-code">state.assumptions() · state.derived()</div>
        </div>""", unsafe_allow_html=True)
    with cc2:
        st.markdown("""<div class="card">
            <div class="card-label" style="color:var(--red);">Detect</div>
            <div class="card-title">Find where logic breaks</div>
            <div class="card-body">5 violation types grounded in formal epistemology: modus ponens failures, belief revision failures, modal scope errors, temporal incoherence, referential opacity.</div>
            <div class="card-code">5 types · classified by graph structure</div>
        </div>""", unsafe_allow_html=True)
    with cc3:
        st.markdown("""<div class="card">
            <div class="card-label" style="color:var(--green);">Explore</div>
            <div class="card-title">Ask "what if?" safely</div>
            <div class="card-body">Add hypothetical premises, see what new commitments arise, check for contradictions — then roll back. Kripke possible worlds, made interactive.</div>
            <div class="card-code">suppose() · auto-rollback</div>
        </div>""", unsafe_allow_html=True)


    # ── 7. SCENARIOS ──
    st.markdown("""
    <div class="sec">
        <div class="sec-h">Interactive</div>
        <div class="sec-title">Try a scenario</div>
        <div class="sec-sub">Step through reasoning one move at a time. Watch the commitment graph grow. You control the pace.</div>
    </div>
    """, unsafe_allow_html=True)

    sc1, sc2 = st.columns(2)
    ex_items = list(EXAMPLES.items())
    for idx, (key, ex) in enumerate(ex_items):
        col = sc1 if idx % 2 == 0 else sc2
        with col:
            st.markdown(f"""<div class="sc">
                <div class="sc-domain">{ex['domain']}</div>
                <div class="sc-title">{ex['icon']}  {ex['title']}</div>
                <div class="sc-desc">{ex['desc']}</div>
                <div class="sc-watch">{ex['watch']}</div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"Walk through {ex['title']} →", key=f"ex_{key}", use_container_width=True):
                start_example(key)
                st.rerun()
            st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)


    # ── 8. COMPARE ──
    st.markdown("""
    <div class="sec">
        <div class="sec-h">Structural Diff</div>
        <div class="sec-title">Compare two reasoning paths</div>
        <div class="sec-sub">Shared commitments, divergences, and which path is structurally stronger.</div>
    </div>
    """, unsafe_allow_html=True)

    xk = list(EXAMPLES.keys())
    dc1, dc2, dc3 = st.columns([2, 2, 1])
    with dc1:
        dl = st.selectbox("Path A", xk, index=0, key="dsl", format_func=lambda k: EXAMPLES[k]["title"])
    with dc2:
        dr = st.selectbox("Path B", xk, index=1, key="dsr", format_func=lambda k: EXAMPLES[k]["title"])
    with dc3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Compare →", use_container_width=True, key="dcmp"):
            st.session_state.dl, st.session_state.dr = dl, dr
            st.session_state.mode = "diff"
            st.rerun()


    # ── 9. IMPORT ──
    st.markdown("""
    <div class="sec">
        <div class="sec-h">Bring Your Own</div>
        <div class="sec-title">Analyze any trace</div>
    </div>
    """, unsafe_allow_html=True)

    ic1, ic2 = st.columns(2)
    with ic1:
        st.markdown('<div style="font-size:0.78rem;color:var(--t3);margin-bottom:10px;">Upload JSON: <code style="font-family:var(--retro);font-size:0.9rem;color:var(--cyan)">[{"text":"...","action":"..."}]</code></div>', unsafe_allow_html=True)
        up = st.file_uploader("JSON trace", type=["json"], label_visibility="collapsed")
        if up is not None:
            try:
                data = json.loads(up.read().decode("utf-8"))
                st.session_state.nous = Nous()
                st.session_state.steps, st.session_state.results = [], []
                nn = st.session_state.nous
                for item in data:
                    t = item.get("text", item.get("reasoning", ""))
                    a = item.get("action", "")
                    res = nn.step(t, a, test_mode=True)
                    st.session_state.steps.append((t, a))
                    st.session_state.results.append(res)
                st.session_state.mode = "analysis"
                st.session_state.eq, st.session_state.ec, st.session_state.ek = [], 0, None
                st.rerun()
            except Exception as e:
                st.error(f"Parse error: {e}")
    with ic2:
        st.markdown('<div style="font-size:0.78rem;color:var(--t3);margin-bottom:10px;">Or type a single reasoning step:</div>', unsafe_allow_html=True)
        ri = st.text_area("Reasoning", placeholder="What the agent said or thought...", height=60, label_visibility="collapsed", key="lr")
        ai = st.text_input("Action", placeholder="What it did...", label_visibility="collapsed", key="la")
        if st.button("Analyze →", type="primary", use_container_width=True, key="lgo"):
            if ri:
                res = n.step(ri, ai or "", test_mode=True)
                st.session_state.steps.append((ri, ai or ""))
                st.session_state.results.append(res)
                st.session_state.mode = "analysis"
                st.session_state.eq = []
                st.rerun()


    # ── 10. AUDIENCE ──
    st.markdown("""
    <div class="sec">
        <div class="sec-h">Audience</div>
        <div class="sec-title">Built for rigor and reach</div>
    </div>
    """, unsafe_allow_html=True)

    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        st.markdown("""<div class="aud">
            <div class="aud-title">Researchers</div>
            <div class="aud-body">Formal verification of reasoning integrity. Lean 4 proofs for every violation type. Structural queries, not heuristics. Publishable, reproducible, inspectable.</div>
        </div>""", unsafe_allow_html=True)
    with ac2:
        st.markdown("""<div class="aud">
            <div class="aud-title">AI teams</div>
            <div class="aud-body">Runtime monitoring for agent reasoning. Detect when an LLM contradicts its own commitments. Integrate into evals, red-teaming, and alignment pipelines.</div>
        </div>""", unsafe_allow_html=True)
    with ac3:
        st.markdown("""<div class="aud">
            <div class="aud-title">Everyone else</div>
            <div class="aud-body">See how reasoning actually works — not as text, but as structure. Understand what "the AI contradicted itself" really means, concretely and visually.</div>
        </div>""", unsafe_allow_html=True)


    # ── 11. FOOTER ──
    st.markdown("""
    <div class="foot">
        <div class="foot-main">Formal structure for reasoning you can actually inspect.</div>
        <div class="foot-sub">NOUS · GRAPH ALGORITHMS · MODAL STRUCTURE · LEAN-VERIFIED</div>
    </div>
    """, unsafe_allow_html=True)


# ██████████████████████████████████████████████████████████████████████
# DIFF VIEW
# ██████████████████████████████████████████████████████████████████████
elif st.session_state.mode == "diff":
    lk, rk = st.session_state.dl, st.session_state.dr

    st.markdown(f'<div style="font-family:var(--serif);font-size:1.2rem;font-weight:700;color:var(--t1);padding:16px 0 4px;">Structural Diff</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.8rem;color:var(--t3);margin-bottom:16px;">{EXAMPLES.get(lk, {}).get("title", "")} vs {EXAMPLES.get(rk, {}).get("title", "")}</div>', unsafe_allow_html=True)

    if st.button("← Back to Nous"):
        go_home()
        st.rerun()

    if lk and rk and lk in EXAMPLES and rk in EXAMPLES:
        nl, nr_o = Nous(), Nous()
        for r, a in EXAMPLES[lk]["steps"]:
            nl.step(r, a, test_mode=True)
        for r, a in EXAMPLES[rk]["steps"]:
            nr_o.step(r, a, test_mode=True)
        d = nl.diff(nr_o)
        ls, rs = nl.state(), nr_o.state()

        st.markdown(f"""<div class="metrics">
            <div class="mc"><div class="mv">{len(d.shared)}</div><div class="ml">Shared</div></div>
            <div class="mc"><div class="mv" style="color:var(--purple)">{len(d.only_in_left)}</div><div class="ml">Only A</div></div>
            <div class="mc"><div class="mv" style="color:var(--gold)">{len(d.only_in_right)}</div><div class="ml">Only B</div></div>
            <div class="mc"><div class="mv ok">{ls.strength():.0%}</div><div class="ml">A Strength</div></div>
            <div class="mc"><div class="mv ok">{rs.strength():.0%}</div><div class="ml">B Strength</div></div>
        </div>""", unsafe_allow_html=True)

        gl, gr = st.columns(2)
        with gl:
            st.markdown(f'<div class="sl">{EXAMPLES[lk]["icon"]} {EXAMPLES[lk]["title"]}</div>', unsafe_allow_html=True)
            if nl.graph.nodes:
                render_graph(nl.graph, height=300)
        with gr:
            st.markdown(f'<div class="sl">{EXAMPLES[rk]["icon"]} {EXAMPLES[rk]["title"]}</div>', unsafe_allow_html=True)
            if nr_o.graph.nodes:
                render_graph(nr_o.graph, height=300)

        if d.shared:
            st.markdown('<div class="sl">Shared commitments</div>', unsafe_allow_html=True)
            for s in d.shared:
                st.markdown(f'<div class="dfs">{esc(s)}</div>', unsafe_allow_html=True)
        dl_c, dr_c = st.columns(2)
        with dl_c:
            if d.only_in_left:
                st.markdown('<div class="sl">Only in A</div>', unsafe_allow_html=True)
                for x in d.only_in_left:
                    st.markdown(f'<div class="dfl">{esc(x)}</div>', unsafe_allow_html=True)
        with dr_c:
            if d.only_in_right:
                st.markdown('<div class="sl">Only in B</div>', unsafe_allow_html=True)
                for x in d.only_in_right:
                    st.markdown(f'<div class="dfr">{esc(x)}</div>', unsafe_allow_html=True)
        if d.structural_differences:
            st.markdown('<div class="sl">Structural differences</div>', unsafe_allow_html=True)
            for sd in d.structural_differences:
                st.markdown(f'<div class="qi">{esc(sd)}</div>', unsafe_allow_html=True)


# ██████████████████████████████████████████████████████████████████████
# ANALYSIS VIEW
# ██████████████████████████████████████████████████████████████████████
elif st.session_state.mode == "analysis":
    state = n.state()
    nv = len(n.violations)
    strength = state.strength()
    na = len(state.assumptions())
    nd_count = len(state.derived())
    has_q = len(st.session_state.eq) > 0

    # Title
    ex_label = ""
    if st.session_state.ek and st.session_state.ek in EXAMPLES:
        ex = EXAMPLES[st.session_state.ek]
        ex_label = f' — {ex["icon"]} {ex["title"]}'

    st.markdown(f'<div style="font-family:var(--serif);font-size:1.2rem;font-weight:700;color:var(--t1);padding:16px 0 4px;">Nous{html_lib.escape(ex_label)}</div>', unsafe_allow_html=True)

    # Controls
    if has_q:
        ctrl = st.columns([1, 2.5, 1.5, 1])
    elif st.session_state.ek:
        ctrl = st.columns([1, 3.5, 1.5])
    else:
        ctrl = st.columns([1, 6])
    with ctrl[0]:
        if st.button("← Back"):
            go_home()
            st.rerun()
    if has_q:
        rem = len(st.session_state.eq)
        with ctrl[2]:
            if st.button(f"Next Step → ({rem} left)", type="primary", use_container_width=True):
                advance()
                st.rerun()
        with ctrl[3]:
            if rem >= 2:
                if st.button("Play All", use_container_width=True):
                    play_all()
                    st.rerun()
    elif st.session_state.ek:
        with ctrl[2]:
            if st.button("Replay step by step", use_container_width=True):
                replay_step_by_step()
                st.rerun()

    # Metrics
    vc = " bad" if nv > 0 else ""
    sc = " ok" if strength > 0.8 else (" bad" if strength < 0.5 else " warn")
    st.markdown(f"""<div class="metrics">
        <div class="mc"><div class="mv">{len(st.session_state.steps)}</div><div class="ml">Steps</div></div>
        <div class="mc"><div class="mv">{na}</div><div class="ml">Foundations</div></div>
        <div class="mc"><div class="mv">{nd_count}</div><div class="ml">Derived</div></div>
        <div class="mc"><div class="mv{vc}">{nv}</div><div class="ml">Violations</div></div>
        <div class="mc"><div class="mv{sc}">{strength:.0%}</div><div class="ml">Strength</div></div>
    </div>""", unsafe_allow_html=True)

    # Strength breakdown
    with st.expander("How is strength calculated?"):
        tn = len(n.graph.nodes)
        cl = n.graph.get_closure()
        cov = len(cl) / tn if tn > 0 else 1.0
        mc = min((e.confidence for e in n.graph.edges), default=1.0)
        cyc = state.circular()
        cp = 1.0 if not cyc else max(0.0, 1.0 - 0.2 * len(cyc))
        vp = 1.0 if not n.graph.violations else max(0.0, 1.0 - 0.3 * len(n.graph.violations))
        for lb, v, c in [("Coverage", cov, "var(--purple)"), ("Min confidence", mc, "var(--green)"), ("Cycle penalty", cp, "var(--gold)"), ("Violation penalty", vp, "var(--red)")]:
            st.markdown(f'<div class="str-r"><div class="str-l">{lb}</div><div class="str-b"><div class="str-f" style="width:{v*100:.0f}%;background:{c}"></div></div><div class="str-p">{v:.0%}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-family:var(--retro);font-size:0.85rem;color:var(--t4);margin-top:4px;text-align:center">= {cov:.2f} × {mc:.2f} × {cp:.2f} × {vp:.2f} = {strength:.3f}</div>', unsafe_allow_html=True)

    # Layout
    left, right = st.columns([1, 1], gap="large")

    # ── LEFT: TRACE ──
    with left:
        st.markdown('<div class="sl">Reasoning Trace</div>', unsafe_allow_html=True)

        for i, ((reasoning, action), result) in enumerate(zip(st.session_state.steps, st.session_state.results)):
            if result.coherent:
                st.markdown(f"""<div class="stp">
                    <div class="stp-h"><span class="stp-n ok">STEP {i+1} · COHERENT</span></div>
                    <div class="stp-b">{esc(reasoning)}</div>
                    <div class="stp-a">→ {esc(action, 150)}</div>
                </div>""", unsafe_allow_html=True)
            else:
                v = result.violation or {}
                vt = str(v.get("type", "Unknown"))
                st.markdown(f"""<div class="stp v">
                    <div class="stp-h"><span class="stp-n bad">STEP {i+1} · VIOLATION</span></div>
                    <div class="stp-b">{esc(reasoning)}</div>
                    <div class="stp-a">→ {esc(action, 150)}</div>
                    <div class="vb">
                        <div class="vb-t">{html_lib.escape(vt)} · {v.get('confidence', 0):.0%}</div>
                        <div class="vb-c">Contradicts: {esc(str(v.get('violated', '?')), 200)}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

                if vt in VIOLATION_EXPLAINERS:
                    exp = VIOLATION_EXPLAINERS[vt]
                    st.markdown(f"""<div class="vb-x">
                        <div class="vb-axiom">{html_lib.escape(exp['axiom'])}</div>
                        <div class="vb-form">{html_lib.escape(exp['formal'])}</div>
                        <div class="vb-plain">{html_lib.escape(exp['plain'])}</div>
                        <div class="vb-lean">Lean 4: {html_lib.escape(exp['lean'])}</div>
                    </div>""", unsafe_allow_html=True)

                chain = v.get("chain", "")
                if chain:
                    with st.expander("Full violation chain"):
                        st.code(chain, language=None)

        if st.session_state.eq:
            st.markdown('<div class="sl" style="margin-top:14px">Coming next</div>', unsafe_allow_html=True)
            for j, (r, a) in enumerate(st.session_state.eq):
                sn = len(st.session_state.steps) + j + 1
                st.markdown(f'<div class="stp p"><div class="stp-h"><span class="stp-n wait">STEP {sn}</span></div><div class="stp-b" style="color:var(--t4)">{esc(r, 80)}</div></div>', unsafe_allow_html=True)

        with st.expander("Add a step manually"):
            mr = st.text_area("Reasoning", key="mr", height=55, label_visibility="collapsed", placeholder="What was said or thought...")
            ma = st.text_input("Action", key="ma", label_visibility="collapsed", placeholder="What was done...")
            if st.button("Add Step", type="primary", use_container_width=True):
                if mr:
                    res = n.step(mr, ma or "", test_mode=True)
                    st.session_state.steps.append((mr, ma or ""))
                    st.session_state.results.append(res)
                    st.rerun()

    # ── RIGHT: GRAPH + QUERIES ──
    with right:
        st.markdown('<div class="sl">Commitment Graph</div>', unsafe_allow_html=True)
        if n.graph.nodes:
            render_graph(n.graph, highlight=st.session_state.hl)
        else:
            st.caption("Graph builds as steps are added.")

        # Hypothetical
        st.markdown('<div class="sl">Hypothetical Exploration</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.74rem;color:var(--t4);margin:-6px 0 8px">Add a premise, see consequences, auto-rollback. Kripke possible worlds.</div>', unsafe_allow_html=True)

        hp = st.text_input("Suppose...", placeholder="e.g. 'The catalyst is stable in air'", key="hp", label_visibility="collapsed")
        if st.button("Explore hypothesis", key="hgo", use_container_width=True):
            if hp:
                pre_d, pre_a = set(state.derived()), set(state.assumptions())
                with n.suppose(hp) as hyp:
                    hs = hyp.state()
                    new_d = set(hs.derived()) - pre_d
                    new_a = set(hs.assumptions()) - pre_a
                    contras = hyp.contradictions()
                    new_cyc = hs.circular()
                st.session_state.hyp = {"premise": hp, "nd": sorted(new_d), "na": sorted(new_a), "c": contras, "cy": new_cyc}
                st.rerun()

        if st.session_state.hyp:
            hr = st.session_state.hyp
            st.markdown(f'<div class="hbox"><div style="font-size:0.8rem;color:var(--t2);margin-bottom:6px">Supposing: <b style="color:#c8a0ff">{esc(hr["premise"], 100)}</b></div>', unsafe_allow_html=True)
            if hr["na"]:
                st.markdown('<span class="htag new">NEW COMMITMENTS</span>', unsafe_allow_html=True)
                for x in hr["na"]:
                    st.markdown(f'<div class="qi">{esc(x)}</div>', unsafe_allow_html=True)
            if hr["nd"]:
                st.markdown('<span class="htag new">NEW DERIVED</span>', unsafe_allow_html=True)
                for x in hr["nd"]:
                    st.markdown(f'<div class="qi">{esc(x)}</div>', unsafe_allow_html=True)
            if hr["c"]:
                st.markdown('<span class="htag bad">CONTRADICTIONS</span>', unsafe_allow_html=True)
                for c in hr["c"]:
                    st.markdown(f'<div class="qi" style="color:#ff8899">{esc(str(c.get("violated", "?")))}</div>', unsafe_allow_html=True)
            if hr["cy"]:
                st.markdown('<span class="htag bad">CYCLES</span>', unsafe_allow_html=True)
                for cy in hr["cy"]:
                    st.markdown(f'<div class="qi" style="color:#ff8899">{" → ".join(cy)}</div>', unsafe_allow_html=True)
            if not hr["nd"] and not hr["na"] and not hr["c"]:
                st.markdown('<div class="qi" style="color:var(--t4)">No new commitments derived from this premise.</div>', unsafe_allow_html=True)
            st.markdown('<span class="htag ok">ROLLED BACK</span> <span style="font-size:0.7rem;color:var(--t4)">Original state preserved.</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Query tabs
        st.markdown('<div class="sl" style="margin-top:16px">Query the Graph</div>', unsafe_allow_html=True)

        t1, t2, t3, t4, t5, t6 = st.tabs(["Foundations", "Derived", "Cycles", "Gaps", "Weakest Link", "Dependencies"])

        with t1:
            a_list = state.assumptions()
            if a_list:
                for a in a_list:
                    st.markdown(f'<div class="qi">{esc(a)}</div>', unsafe_allow_html=True)
            else:
                st.caption("No foundations yet.")

        with t2:
            d_list = state.derived()
            if d_list:
                for d in d_list:
                    st.markdown(f'<div class="qi">{esc(d)}</div>', unsafe_allow_html=True)
            else:
                st.caption("No derived commitments yet.")

        with t3:
            cycles = state.circular()
            if cycles:
                for c in cycles:
                    st.error(f"Cycle: {' → '.join(c)}")
            else:
                st.markdown('<div style="color:var(--green);font-size:0.82rem;padding:6px 0">No circular reasoning detected.</div>', unsafe_allow_html=True)

        with t4:
            st.markdown('<div style="font-size:0.74rem;color:var(--t4);margin-bottom:8px">Enter a goal to find what premises are missing.</div>', unsafe_allow_html=True)
            goal = st.text_input("Goal", placeholder="e.g. f is differentiable on (a,b)", label_visibility="collapsed", key="gg")
            if goal:
                gap = state.gaps_to(goal)
                if gap.reachable:
                    st.success(f"Already reachable ({gap.method}).")
                else:
                    if gap.closest_nodes:
                        st.markdown('<div class="sl">Closest commitments</div>', unsafe_allow_html=True)
                        for c in gap.closest_nodes:
                            st.markdown(f'<div class="qi">{esc(c)}</div>', unsafe_allow_html=True)
                    if gap.missing_links:
                        st.markdown('<div class="sl">Missing links</div>', unsafe_allow_html=True)
                        for m in gap.missing_links:
                            st.markdown(f'<div class="qi" style="color:var(--gold)">{esc(m)}</div>', unsafe_allow_html=True)
                    if gap.suggested_premises:
                        st.markdown('<div class="sl">Suggested premises</div>', unsafe_allow_html=True)
                        for sp in gap.suggested_premises:
                            st.markdown(f'<div class="qi" style="color:var(--purple)">{esc(sp)}</div>', unsafe_allow_html=True)

        with t5:
            wl = state.weakest_link()
            if wl:
                st.markdown(f'<div class="weak"><b>Weakest link:</b> {esc(wl)}</div>', unsafe_allow_html=True)
                st.markdown('<div style="font-size:0.72rem;color:var(--t4);margin-top:4px">The commitment with the lowest minimum-confidence support path.</div>', unsafe_allow_html=True)
                if st.button("Highlight on graph", key="hlw"):
                    st.session_state.hl = wl
                    st.rerun()
                if st.session_state.hl:
                    if st.button("Clear highlight", key="clw"):
                        st.session_state.hl = None
                        st.rerun()
            else:
                st.caption("All commitments fully supported.")

        with t6:
            nodes = sorted(n.graph.nodes.keys())
            if nodes:
                st.markdown('<div style="font-size:0.74rem;color:var(--t4);margin-bottom:8px">Trace a commitment backward to its foundations.</div>', unsafe_allow_html=True)
                sel = st.selectbox("Commitment", nodes, key="ds", format_func=lambda x: (x[:52] + "...") if len(x) > 52 else x)
                if sel:
                    deps = state.depends_on(sel)
                    if deps:
                        for dep in deps:
                            nd_obj = n.graph.nodes.get(dep)
                            tag = "EXPLICIT" if nd_obj and nd_obj.is_explicit else "DERIVED"
                            st.markdown(f'<div class="dep"><span style="font-family:var(--retro);font-size:0.8rem;color:var(--t4)">[{tag}]</span> {esc(dep)}</div>', unsafe_allow_html=True)
                    else:
                        st.caption("Foundation node — no dependencies.")
            else:
                st.caption("No nodes yet.")

    # Audit trail
    with st.expander("Full audit trail"):
        for entry in n.trace():
            st.text(str(entry))
