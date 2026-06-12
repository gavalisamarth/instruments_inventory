# =============================================================================
# ADANI MAIN STORE — BLOOMBERG TERMINAL THEME
# File: app.py  |  Run: python -m streamlit run app.py
# =============================================================================

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os, datetime, sys, base64

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# ── Load Adani logo as base64 for inline HTML embedding ──
def _load_logo_b64():
    logo_path = os.path.join(SCRIPT_DIR, "adani_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

LOGO_B64 = _load_logo_b64()

from inventory_chatbot_copy import (
    load_inventory, save_inventory, log_issue,
    get_supabase
)

# ── User Database ─────────────────────────────────────────────────────────────
def load_users():
    try:
        supabase = get_supabase()
        response = supabase.table("users").select("*").execute()
        df = pd.DataFrame(response.data)
        if df.empty:
            df = pd.DataFrame(columns=["Name", "Email", "Department", "Password"])
        return df
    except Exception as e:
        st.error(f"Cannot read users from Supabase: {e}")
        return pd.DataFrame(columns=["Name", "Email", "Department", "Password"])

def save_user(name, email, dept, password):
    try:
        supabase = get_supabase()
        supabase.table("users").insert({
            "Name": name, 
            "Email": email, 
            "Department": dept, 
            "Password": password
        }).execute()
        return True
    except Exception as e:
        st.error(f"Registration failed! Could not save to Supabase: {e}")
        return False

try:
    import analytics as anlx
    ANALYTICS_READY = True
except Exception as e:
    ANALYTICS_READY = False
    print(f"[analytics] import failed: {e}")
try:
    import importlib, email_alerts
    importlib.reload(email_alerts)
    EMAIL_READY = True
except Exception:
    EMAIL_READY = False

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Adani Store Terminal",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Session state ─────────────────────────────────────────────────────────────
if "active_page" not in st.session_state: st.session_state.active_page = "dashboard"
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "user_dept" not in st.session_state: st.session_state.user_dept = ""

PAGE = st.session_state.active_page

# ── Data ──────────────────────────────────────────────────────────────────────
# Cache TTL = 5s — manual Excel edits appear within 5 seconds
# Also tracks file modification time: if Excel is saved externally,
# cache is busted immediately on next interaction.

@st.cache_data(ttl=5)
def get_inventory(_mtime=0): return load_inventory()

@st.cache_data(ttl=5)
def get_log():
    try:
        supabase = get_supabase()
        response = supabase.table("transaction_logs").select("*").execute()
        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        st.error(f"Error reading log from Supabase: {e}")
        return pd.DataFrame()

def get_inventory_fresh():
    """Always reads Supabase — bypasses cache. Used after manual edits."""
    return get_inventory(_mtime=datetime.datetime.now().timestamp())

df     = get_inventory()
log_df = get_log()
if df is None:
    st.error("⚠️ Cannot load inventory from Supabase"); st.stop()

low_df    = df[df["Quantity"] < df["MinStock"]]
low_count = len(low_df)
out_count = len(df[df["Quantity"] == 0])
now       = datetime.datetime.now()

# ── HTML table helper ─────────────────────────────────────────────────────────
def html_table(data: pd.DataFrame, status_col: str = None) -> str:
    STATUS_MAP = {
        "🔴 Out of Stock": ('<span style="color:#1a1a1f;">■</span>'
                            ' <span style="color:#ef4444;font-weight:600;">OUT OF STOCK</span>'),
        "🟡 Low Stock":    ('<span style="color:#1a1a1f;">■</span>'
                            ' <span style="color:#f97316;font-weight:600;">LOW STOCK</span>'),
        "🟢 Available":    ('<span style="color:#1a1a1f;">■</span>'
                            ' <span style="color:#22c55e;font-weight:600;">AVAILABLE</span>'),
        "🟢 OK":           ('<span style="color:#1a1a1f;">■</span>'
                            ' <span style="color:#22c55e;font-weight:600;">OK</span>'),
    }
    headers = "".join(f"<th>{col.upper()}</th>" for col in data.columns)
    rows = ""
    for _, row in data.iterrows():
        cells = ""
        for col, val in row.items():
            if col == status_col and str(val) in STATUS_MAP:
                cells += f"<td>{STATUS_MAP[str(val)]}</td>"
            else:
                cells += f"<td>{val}</td>"
        rows += f"<tr>{cells}</tr>"
    return f"""
    <div class='tbl-wrap'>
      <table class='htbl'>
        <thead><tr>{headers}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""

# ═════════════════════════════════════════════════════════════════════════════
# ADANI BRAND THEME CSS
# Primary: Teal #00b4d8  |  Background: Deep Navy #050d1a
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, *::before, *::after {
    font-family: 'Inter', sans-serif;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
    box-sizing: border-box;
}

/* ── Root variables — Adani Brand ── */
:root {
    --bg:         #050d1a;
    --sidebar:    #07111f;
    --surface:    #0c1a2e;
    --surface2:   #0f2040;
    --border:     rgba(0,180,216,0.12);
    --teal:       #00b4d8;
    --teal-dim:   rgba(0,180,216,0.12);
    --teal-glow:  rgba(0,180,216,0.25);
    --purple:     #7b2ff7;
    --pink:       #f72585;
    --green:      #22c55e;
    --red:        #ef4444;
    --amber:      #f59e0b;
    --text-1:     #e8f4f8;
    --text-2:     #7fb3c8;
    --text-3:     #2e5a72;
}

/* ── Animations ── */
@keyframes fadeInSlide {
    0% { opacity: 0; transform: translateY(10px); }
    100% { opacity: 1; transform: translateY(0); }
}

/* ── App background ── */
.stApp { 
    background: var(--bg) !important; 
    color: var(--text-1); 
    animation: fadeInSlide 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer { display:none !important; }
header, [data-testid="stHeader"] { background: transparent !important; }

/* ── Custom Hamburger Menu Icon ── */
[data-testid="collapsedControl"] svg {
    display: none !important;
}
[data-testid="collapsedControl"]::after {
    content: '☰' !important;
    font-size: 1.6rem !important;
    color: var(--teal) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* ── Remove block padding ── */
.main .block-container { padding:0 !important; margin:0 !important; max-width:100% !important; }
[data-testid="stHorizontalBlock"] { gap:0 !important; }

/* ── Hide Form Input Instructions (prevents overlapping) ── */
div[data-testid="InputInstructions"] { display: none !important; }

/* ══════════════════════════════
   SIDEBAR COLUMN
══════════════════════════════ */
[data-testid="stSidebar"] {
    background: var(--sidebar) !important;
    border-right: 1px solid var(--border) !important;
    padding: 0 !important;
}
[data-testid="stSidebarUserContent"] {
    padding-top: 1rem !important;
}

/* ── All sidebar buttons base ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    color: var(--text-2) !important;
    width: 100% !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    box-shadow: none !important;
    transform: none !important;
    transition: all 0.12s ease !important;
    display: flex !important;
    align-items: center !important;
    border-radius: 4px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(0,180,216,0.06) !important;
    color: var(--text-1) !important;
    transform: none !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:1px !important; padding:0 !important; }

/* ── NEW ISSUE button (teal CTA) ── */
.new-issue-btn .stButton > button {
    background: linear-gradient(90deg, #00b4d8, #7b2ff7) !important;
    color: #fff !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.5px !important;
    height: 38px !important;
    border-radius: 4px !important;
    margin: 0 12px !important;
    width: calc(100% - 24px) !important;
    justify-content: center !important;
    padding: 0 !important;
}
.new-issue-btn .stButton > button:hover {
    background: linear-gradient(90deg, #00caf0, #9b4fff) !important;
    color: #fff !important;
}

/* ── Nav items ── */
.nav-item .stButton > button {
    height: 42px !important;
    font-size: 0.86rem !important;
    font-weight: 400 !important;
    letter-spacing: 0.4px !important;
    padding: 0 16px !important;
    gap: 12px !important;
    justify-content: flex-start !important;
    border-radius: 6px !important;
    border: 1px solid transparent !important;
    color: var(--text-2) !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
.nav-item .stButton > button:hover {
    background: rgba(0,180,216,0.06) !important;
    color: var(--text-1) !important;
    transform: translateX(4px) !important;
}
.nav-active .stButton > button {
    background: var(--teal-dim) !important;
    color: var(--teal) !important;
    border: 1px solid var(--border) !important;
    font-weight: 500 !important;
}
.nav-active .stButton > button:hover {
    background: rgba(0,180,216,0.18) !important;
    color: var(--teal) !important;
    transform: translateX(4px) !important;
}

/* ── Reload btn ── */
.reload-btn .stButton > button {
    height: 36px !important;
    font-size: 0.75rem !important;
    padding: 0 16px !important;
    justify-content: flex-start !important;
    border-radius: 0 !important;
    color: var(--text-3) !important;
    letter-spacing: 0.3px !important;
}
.reload-btn .stButton > button:hover { color: var(--text-2) !important; }

/* ── Sidebar divider ── */
[data-testid="stSidebar"] hr {
    border-color: var(--border) !important; margin: 8px 0 !important;
}

/* ══════════════════════════════
   TOP BAR
══════════════════════════════ */
.top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    height: 52px;
    background: var(--sidebar);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 100;
}
.top-bar-left { display:flex; align-items:center; gap:8px; }
.top-bar-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    background: linear-gradient(90deg, #00b4d8, #7b2ff7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.top-bar-sep { color: var(--text-3); margin: 0 4px; }
.top-bar-page { font-size: 0.75rem; color: var(--text-2); font-weight: 500; letter-spacing:0.5px; text-transform:uppercase; }
.top-bar-right { font-size: 0.72rem; color: var(--text-3); letter-spacing: 0.3px; }

/* ══════════════════════════════
   CONTENT AREA
══════════════════════════════ */
.content-pad { padding: 24px 28px; }

/* ══════════════════════════════
   KPI CARDS
══════════════════════════════ */
.kpi-row { display:flex; gap:1px; margin-bottom:24px; }
.kpi-box {
    flex:1;
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
    border-radius: 6px;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
.kpi-box:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 24px -8px rgba(0,0,0,0.5), 0 0 15px 0 rgba(0, 180, 216, 0.1);
    border-color: rgba(0, 180, 216, 0.35);
}
.kpi-box::after {
    content:'';
    position:absolute;
    top:0; left:0; right:0;
    height:2px;
}
.kpi-box.orange::after { background: linear-gradient(90deg,#00b4d8,#7b2ff7); }
.kpi-box.green::after  { background: var(--green); }
.kpi-box.red::after    { background: var(--red); }
.kpi-label {
    font-size: 0.64rem;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: var(--text-3);
    margin: 0 0 8px;
}
.kpi-val {
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -1px;
    margin: 0;
}
.kpi-val.orange { color: var(--teal); }
.kpi-val.green  { color: var(--green); }
.kpi-val.red    { color: var(--red); }
.kpi-sub {
    font-size: 0.68rem;
    color: var(--text-3);
    margin: 6px 0 0;
    letter-spacing: 0.3px;
}

/* ══════════════════════════════
   SECTION HEADERS
══════════════════════════════ */
.sec-hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0 10px;
    border-bottom: 1px solid var(--border);
    margin: 20px 0 14px;
}
.sec-hdr-left {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: var(--text-2);
}
.sec-hdr-badge {
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 2px;
    background: rgba(0,180,216,0.15);
    color: var(--teal);
    letter-spacing: 0.5px;
}
.sec-hdr-badge.red {
    background: rgba(239,68,68,0.15);
    color: var(--red);
}

/* ══════════════════════════════
   TABLES
══════════════════════════════ */
.tbl-wrap {
    border: 1px solid var(--border);
    border-radius: 0;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin-bottom: 16px;
    background: var(--surface);
}
.htbl { width:100%; border-collapse:collapse; font-size:0.82rem; }
.htbl thead tr { background:#040c18; border-bottom:1px solid var(--border); }
.htbl thead th {
    padding: 9px 16px;
    text-align: left;
    font-size: 0.65rem;
    font-weight: 700;
    color: var(--text-3);
    letter-spacing: 1px;
    text-transform: uppercase;
    white-space: nowrap;
}
.htbl tbody tr { 
    border-bottom: 1px solid rgba(0,180,216,0.05); 
    transition: background-color 0.2s cubic-bezier(0.16, 1, 0.3, 1), transform 0.1s ease !important; 
}
.htbl tbody tr:hover {
    background-color: rgba(0, 180, 216, 0.06) !important;
}
.htbl tbody tr:last-child { border-bottom: none; }
.htbl tbody tr:hover { background: rgba(0,180,216,0.06); }
.htbl tbody td { padding: 10px 16px; color: var(--text-1); font-size:0.82rem; vertical-align:middle; }
.htbl tbody td:first-child { color: var(--teal); font-weight: 600; }

/* ══════════════════════════════
   ALERT BOXES
══════════════════════════════ */
.alert {
    padding: 12px 16px;
    border-left: 3px solid;
    margin: 10px 0;
    font-size: 0.84rem;
    font-weight: 500;
}
.alert.ok   { border-color: var(--green);  background: rgba(34,197,94,0.07);  color: #4ade80; }
.alert.warn { border-color: var(--amber);  background: rgba(245,158,11,0.07); color: #fbbf24; }
.alert.err  { border-color: var(--red);    background: rgba(239,68,68,0.07);  color: #f87171; }
.alert.info { border-color: var(--teal);   background: var(--teal-dim);       color: #67e8f9; }

/* ══════════════════════════════
   ITEM PREVIEW CARD
══════════════════════════════ */
.item-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 2px solid var(--teal);
    padding: 20px;
}
.ic-label { font-size: 0.62rem; font-weight:700; letter-spacing:1.2px; text-transform:uppercase; color:var(--text-3); margin:0 0 3px; }
.ic-val   { font-size: 0.9rem; color: var(--text-1); margin:0 0 14px; font-weight:500; }
.ic-code  { font-size: 1.3rem; color: var(--teal); font-weight:700; margin:0 0 14px; }
.ic-hr    { border:none; border-top:1px solid var(--border); margin:12px 0; }
.ic-qty-ok  { font-size:1.8rem; font-weight:700; color:var(--green); margin:0; }
.ic-qty-low { font-size:1.8rem; font-weight:700; color:var(--red);   margin:0; }

/* ══════════════════════════════
   PAGE TITLE
══════════════════════════════ */
.pg-title { font-size:1.5rem; font-weight:700; color:var(--text-1); margin:0 0 2px; letter-spacing:-0.3px; }
.pg-sub   { font-size:0.75rem; color:var(--text-3); margin:0 0 20px; letter-spacing:0.3px; text-transform:uppercase; }

/* ══════════════════════════════
   INPUTS
══════════════════════════════ */
input, textarea, select {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 3px !important;
    color: var(--text-1) !important;
    font-size: 0.84rem !important;
}
input:focus, textarea:focus { border-color: var(--teal) !important; }

/* ══════════════════════════════
   SUBMIT BUTTON
══════════════════════════════ */
.submit-btn .stButton > button {
    background: linear-gradient(90deg, #00b4d8, #7b2ff7) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 3px !important;
    padding: 12px 24px !important;
    font-weight: 700 !important;
    font-size: 0.84rem !important;
    letter-spacing: 0.5px !important;
    width: 100% !important;
    box-shadow: none !important;
}
.submit-btn .stButton > button:hover {
    background: linear-gradient(90deg, #00caf0, #9b4fff) !important;
    transform: none !important;
}

/* ── Download btn ── */
.stDownloadButton > button {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--text-2) !important;
    border-radius: 3px !important;
    font-size: 0.78rem !important;
    width: auto !important;
    letter-spacing: 0.3px !important;
}
.stDownloadButton > button:hover {
    border-color: var(--teal) !important;
    color: var(--teal) !important;
}

hr { border-color: var(--border) !important; margin: 10px 0 !important; }

/* ══════════════════════════════
   MOBILE OPTIMIZATION
══════════════════════════════ */
@media (max-width: 768px) {
    .top-bar {
        flex-direction: column !important;
        height: auto !important;
        align-items: flex-start !important;
        padding: 12px 20px !important;
        gap: 6px !important;
    }
    .top-bar-left {
        flex-wrap: wrap !important;
    }
    .top-bar-title {
        font-size: 0.65rem !important;
    }
    .top-bar-right {
        font-size: 0.6rem !important;
        opacity: 0.7 !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION WALL
# ═════════════════════════════════════════════════════════════════════════════
if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center; color: var(--teal); margin-top:50px;'>ADANI STORE TERMINAL</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: var(--text-3); font-size: 0.9rem;'>Please log in to continue</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        auth_mode = st.radio("Mode", ["Login", "Register"], horizontal=True, label_visibility="collapsed")
        
        if auth_mode == "Login":
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("LOGIN", use_container_width=True)
                if submit:
                    users_df = load_users()
                    match = users_df[(users_df["Email"] == email) & (users_df["Password"] == password)]
                    if not match.empty:
                        user_info = match.iloc[0]
                        st.session_state.authenticated = True
                        st.session_state.user_name = user_info["Name"]
                        st.session_state.user_dept = user_info["Department"]
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
        else:
            with st.form("register_form"):
                name = st.text_input("Full Name")
                dept = st.text_input("Department")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("REGISTER", use_container_width=True)
                if submit:
                    if name and email and password:
                        users_df = load_users()
                        if email in users_df["Email"].values:
                            st.error("Email already registered.")
                        else:
                            success = save_user(name, email, dept, password)
                            if success:
                                st.success("Registered successfully! Please log in.")
                    else:
                        st.error("Please fill all required fields.")
    st.stop()


# ═════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ═════════════════════════════════════════════════════════════════════════════
NAV_ITEMS = [
    ("dashboard",  "📊  Overview"),
    ("search",     "🔍  Search"),
    ("issue",      "📤  Issue Instrument"),
    ("inventory",  "📦  Full Inventory"),
    ("log",        "🧾  Transaction Log"),
    ("analytics",  "📈  Analytics"),
]

# ════════════════════
# SIDEBAR
# ════════════════════
with st.sidebar:

    # Brand — Adani Logo as styled text
    st.markdown("""
    <div style='padding:22px 20px 18px;
                border-bottom:1px solid rgba(255,255,255,0.07);
                background:transparent;'>
        <div style='display:flex; align-items:center; gap:0; line-height:1;'>
            <span style='font-size:1.8rem; font-weight:700; letter-spacing:-0.5px;
                background:linear-gradient(90deg,#00b4d8 0%,#7b2ff7 40%,#f72585 100%);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                background-clip:text; font-family:Arial,sans-serif;'>adani</span>
            <span style='color:#6b7280; font-size:1.6rem; margin:0 10px;
                font-weight:300; line-height:1;'>|</span>
            <span style='font-size:1.1rem; font-weight:500; color:#9ca3af;
                letter-spacing:0.3px; font-family:Arial,sans-serif;'>Electricity</span>
        </div>
        <div style='font-size:0.65rem; color:#4b5563; letter-spacing:1.5px;
                    text-transform:uppercase; margin-top:10px;'>
            C&amp;I Main Store Terminal
        </div>
    </div>""", unsafe_allow_html=True)

    # New Issue CTA
    st.markdown("<div style='padding:10px 0 4px;'>", unsafe_allow_html=True)
    st.markdown("<div class='new-issue-btn'>", unsafe_allow_html=True)
    if st.button("➕ NEW ISSUE", key="new_issue_cta", use_container_width=True):
        st.session_state.active_page = "issue"
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Nav items
    for key, label in NAV_ITEMS:
        is_active = PAGE == key
        wrap = "nav-active nav-item" if is_active else "nav-item"
        st.markdown(f"<div class='{wrap}'>", unsafe_allow_html=True)
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state.active_page = key
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Bottom
    st.divider()
    st.markdown(f"""
    <div style='padding:4px 16px 10px;'>
        <div style='font-size:0.62rem; color:#374151; letter-spacing:0.5px;
                    text-transform:uppercase; line-height:2;'>
            {now.strftime("%d %b %Y")}&nbsp;&nbsp;{now.strftime("%H:%M")}
        </div>
    </div>""", unsafe_allow_html=True)
    st.markdown("<div class='reload-btn'>", unsafe_allow_html=True)
    if st.button("🔄 RELOAD DATA", key="reload", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 LOG OUT", key="logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_name = ""
        st.session_state.user_dept = ""
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════
# MAIN CONTENT
# ════════════════════
with st.container():

    PAGE_LABELS = {
        "dashboard":  "DASHBOARD",
        "search":     "SEARCH",
        "issue":      "ISSUE INSTRUMENT",
        "inventory":  "FULL INVENTORY",
        "log":        "TRANSACTION LOG",
        "analytics":  "USAGE ANALYTICS",
    }

    # Top bar
    st.markdown(f"""
    <div class='top-bar'>
        <div class='top-bar-left'>
            <span class='top-bar-title'>ADANI STORE TERMINAL</span>
            <span class='top-bar-sep'>›</span>
            <span class='top-bar-page'>{PAGE_LABELS.get(PAGE,'')}</span>
        </div>
        <div class='top-bar-right'>
            C&amp;I MAIN STORE &nbsp;·&nbsp; {now.strftime("%d %b %Y  %H:%M")}
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='content-pad'>", unsafe_allow_html=True)

    # ── DASHBOARD ──────────────────────────────────────────────────────────────
    if PAGE == "dashboard":
        st.markdown("<div class='pg-title'>INSTRUMENT INVENTORY OVERVIEW</div>", unsafe_allow_html=True)
        st.markdown("<div class='pg-sub'>Adani Thermal Power Plant · C&I Main Store · Live Stock Status</div>", unsafe_allow_html=True)

        k1,k2,k3,k4 = st.columns(4)
        with k1:
            st.markdown(f"""<div class='kpi-box orange'>
                <div class='kpi-label'>Total Instruments</div>
                <div class='kpi-val orange'>{len(df)}</div>
                <div class='kpi-sub'>Unique item types in store</div>
            </div>""", unsafe_allow_html=True)
        with k2:
            st.markdown(f"""<div class='kpi-box orange'>
                <div class='kpi-label'>Units in Store</div>
                <div class='kpi-val orange'>{int(df["Quantity"].sum())}</div>
                <div class='kpi-sub'>Total quantity across all items</div>
            </div>""", unsafe_allow_html=True)
        with k3:
            cls = "red" if low_count > 0 else "green"
            st.markdown(f"""<div class='kpi-box {cls}'>
                <div class='kpi-label'>Low Stock Items</div>
                <div class='kpi-val {cls}'>{low_count}</div>
                <div class='kpi-sub'>Below minimum threshold</div>
            </div>""", unsafe_allow_html=True)
        with k4:
            cls = "red" if out_count > 0 else "green"
            st.markdown(f"""<div class='kpi-box {cls}'>
                <div class='kpi-label'>Out of Stock</div>
                <div class='kpi-val {cls}'>{out_count}</div>
                <div class='kpi-sub'>Zero quantity available</div>
            </div>""", unsafe_allow_html=True)

        if not low_df.empty:
            badge_cls = "red" if out_count > 0 else ""
            st.markdown(f"""
            <div class='sec-hdr'>
                <span class='sec-hdr-left'>⚠ PROCUREMENT ACTION REQUIRED</span>
                <span class='sec-hdr-badge {badge_cls}'>{low_count} ITEMS</span>
            </div>""", unsafe_allow_html=True)
            alert = low_df[["ItemCode","ItemName","Category","Quantity","MinStock","Location"]].copy()
            alert["SHORTFALL"] = (alert["MinStock"] - alert["Quantity"]).astype(int)
            alert["STATUS"]    = alert["Quantity"].apply(
                lambda q: "🔴 Out of Stock" if q==0 else "🟡 Low Stock")
            alert.columns = ["ITEM CODE","ITEM NAME","CATEGORY","CURRENT QTY","MIN STOCK","LOCATION","SHORTFALL","STATUS"]
            st.markdown(html_table(alert.sort_values("SHORTFALL", ascending=False), status_col="STATUS"), unsafe_allow_html=True)
        else:
            st.markdown("<div class='alert ok'>■  All stock levels within limits. No procurement action required.</div>", unsafe_allow_html=True)

        if not log_df.empty:
            st.markdown("""
            <div class='sec-hdr'>
                <span class='sec-hdr-left'>↓ RECENT TRANSACTIONS</span>
            </div>""", unsafe_allow_html=True)
            st.markdown(html_table(log_df.tail(8).iloc[::-1].reset_index(drop=True)), unsafe_allow_html=True)

    # ── SEARCH ─────────────────────────────────────────────────────────────────
    elif PAGE == "search":
        st.markdown("<div class='pg-title'>INSTRUMENT SEARCH</div>", unsafe_allow_html=True)
        st.markdown("<div class='pg-sub'>Search across all C&I instruments by code, name, or category</div>", unsafe_allow_html=True)

        c1,c2 = st.columns([3,1])
        with c1:
            keyword = st.text_input("", placeholder="Search — PT001, RTD, Pressure Transmitter, Rack B12...",
                                    label_visibility="collapsed")
        with c2:
            cat_f = st.selectbox("", ["ALL CATEGORIES"]+sorted(df["Category"].unique().tolist()),
                                 label_visibility="collapsed")

        filtered = df.copy()
        if keyword.strip():
            kw = keyword.strip()
            filtered = filtered[
                filtered["ItemName"].str.contains(kw, case=False, na=False) |
                filtered["ItemCode"].str.contains(kw, case=False, na=False) |
                filtered["Category"].str.contains(kw, case=False, na=False)
            ]
        if cat_f != "ALL CATEGORIES":
            filtered = filtered[filtered["Category"] == cat_f]

        if keyword.strip() or cat_f != "ALL CATEGORIES":
            st.markdown(f"""
            <div class='sec-hdr'>
                <span class='sec-hdr-left'>SEARCH RESULTS</span>
                <span class='sec-hdr-badge'>{len(filtered)} FOUND</span>
            </div>""", unsafe_allow_html=True)

        if filtered.empty and keyword.strip():
            st.markdown(f"<div class='alert warn'>No results for <b>'{keyword}'</b>. Try a partial name or item code.</div>", unsafe_allow_html=True)
        elif not filtered.empty:
            disp = filtered[["ItemCode","ItemName","Category","Quantity","MinStock","Location"]].copy()
            disp["STATUS"] = filtered.apply(
                lambda r: "🔴 Out of Stock" if r["Quantity"]==0
                else ("🟡 Low Stock" if r["Quantity"]<r["MinStock"] else "🟢 Available"), axis=1)
            disp.columns = ["ITEM CODE","ITEM NAME","CATEGORY","QTY","MIN","LOCATION","STATUS"]
            st.markdown(html_table(disp, status_col="STATUS"), unsafe_allow_html=True)
        else:
            st.markdown("<div class='alert info'>Enter a search term above to query the inventory.</div>", unsafe_allow_html=True)

    # ── ISSUE ──────────────────────────────────────────────────────────────────
    elif PAGE == "issue":
        st.markdown("<div class='pg-title'>ISSUE INSTRUMENT</div>", unsafe_allow_html=True)
        st.markdown("<div class='pg-sub'>Record instrument issue from main store to field engineer</div>", unsafe_allow_html=True)

        left, right = st.columns([1,1], gap="large")
        with left:
            st.markdown("<div class='sec-hdr'><span class='sec-hdr-left'>ENGINEER DETAILS</span></div>", unsafe_allow_html=True)
            engineer_name = st.text_input("Full Name *", value=st.session_state.user_name)
            emp_id        = st.text_input("Employee ID", placeholder="e.g. AD-CI-1042")
            
            dept_options = ["C&I", "Mechanical", "Electrical", "Operations", "Maintenance", "Safety", "Civil", "IT", "Other"]
            default_index = dept_options.index(st.session_state.user_dept) if st.session_state.user_dept in dept_options else 0
            department    = st.selectbox("Department", dept_options, index=default_index)

            st.markdown("<div class='sec-hdr'><span class='sec-hdr-left'>INSTRUMENT SELECTION</span></div>", unsafe_allow_html=True)
            hint = st.text_input("Filter list", placeholder="type to narrow...", key="isearch")
            sdf  = df.copy()
            if hint.strip():
                sdf = sdf[sdf["ItemName"].str.contains(hint.strip(), case=False, na=False) |
                          sdf["ItemCode"].str.contains(hint.strip(), case=False, na=False)]
            opts = {f"[{r['ItemCode']}]  {r['ItemName']}  —  Qty:{int(r['Quantity'])}  @  {r['Location']}": i
                    for i, r in sdf.iterrows()}
            sel_lbl = st.selectbox("Select Instrument", ["— SELECT —"]+list(opts.keys()),
                                   label_visibility="collapsed")
            qty_req = st.number_input("Quantity *", min_value=1, max_value=9999, value=1)
            purpose = st.text_area("Purpose / Work Order", placeholder="e.g. Replacing PT on Unit 2 boiler", height=80)

        with right:
            st.markdown("<div class='sec-hdr'><span class='sec-hdr-left'>ITEM DETAILS</span></div>", unsafe_allow_html=True)
            if sel_lbl != "— SELECT —":
                idx   = opts[sel_lbl]; sel = df.loc[idx]
                cur   = int(sel["Quantity"]); mn = int(sel["MinStock"])
                after = cur - qty_req
                qcls  = "ic-qty-low" if cur < mn else "ic-qty-ok"
                st.markdown(f"""
                <div class='item-card'>
                    <div class='ic-label'>Item Code</div>
                    <div class='ic-code'>{sel['ItemCode']}</div>
                    <div class='ic-label'>Item Name</div>
                    <div class='ic-val'>{sel['ItemName']}</div>
                    <div class='ic-label'>Category</div>
                    <div class='ic-val'>{sel['Category']}</div>
                    <div class='ic-label'>Rack Location</div>
                    <div class='ic-val'>▣ {sel['Location']}</div>
                    <div class='ic-hr'></div>
                    <div class='ic-label'>Current Stock</div>
                    <div class='{qcls}'>{cur} units</div>
                    <div class='ic-label' style='margin-top:8px;'>Minimum Required</div>
                    <div class='ic-val'>{mn} units</div>
                </div>""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if qty_req > cur:
                    st.markdown(f"<div class='alert err'>✕  Insufficient stock — only {cur} units available.</div>", unsafe_allow_html=True)
                elif after < mn:
                    st.markdown(f"<div class='alert warn'>⚠  After issue: {after} units remaining (below min {mn}). Alert will fire.</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='alert ok'>✓  Stock OK — {after} units will remain after issue.</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='alert info'>Select an instrument on the left to see live details.</div>", unsafe_allow_html=True)

        st.divider()
        st.markdown("<div class='submit-btn'>", unsafe_allow_html=True)
        bc,_ = st.columns([1,2])
        with bc:
            submit = st.button("▲  CONFIRM & ISSUE INSTRUMENT", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if submit:
            if not engineer_name.strip():
                st.markdown("<div class='alert err'>✕  Engineer name is required.</div>", unsafe_allow_html=True)
            elif sel_lbl == "— SELECT —":
                st.markdown("<div class='alert err'>✕  Select an instrument.</div>", unsafe_allow_html=True)
            else:
                idx = opts[sel_lbl]; s = df.loc[idx]
                cur = int(s["Quantity"]); mn = int(s["MinStock"])
                if qty_req > cur:
                    st.markdown(f"<div class='alert err'>✕  Only {cur} units available.</div>", unsafe_allow_html=True)
                else:
                    new_qty = cur - qty_req
                    if save_inventory(s["ItemCode"], new_qty):
                        df.loc[idx,"Quantity"] = new_qty
                        log_issue(engineer_name.strip(), s["ItemCode"], s["ItemName"],
                                  qty_req, new_qty, department=department)
                        st.cache_data.clear()
                        st.markdown(f"""<div class='alert ok'>
                            ✓  ISSUED: {qty_req} × {s['ItemName']} → {engineer_name}<br>
                            &nbsp;&nbsp;&nbsp;Remaining: {new_qty} units at {s['Location']}
                        </div>""", unsafe_allow_html=True)

                        # ── Issue confirmation email (fires on EVERY issue) ──
                        if EMAIL_READY:
                            email_alerts.send_issue_confirmation(
                                engineer_name = engineer_name.strip(),
                                emp_id        = emp_id.strip() if emp_id else "",
                                item_code     = s["ItemCode"],
                                item_name     = s["ItemName"],
                                category      = s["Category"],
                                location      = s["Location"],
                                qty_taken     = qty_req,
                                qty_remaining = new_qty,
                                purpose       = purpose.strip() if purpose else ""
                            )
                            st.markdown("<div class='alert info'>↗  Issue confirmation emailed to officials.</div>",
                                        unsafe_allow_html=True)

                        # ── Additional low stock alert if below MinStock ──
                        if new_qty < mn and EMAIL_READY:
                            email_alerts.send_low_stock_alert(
                                item_code=s["ItemCode"], item_name=s["ItemName"],
                                qty_left=new_qty, min_stock=mn, location=s["Location"],
                                engineer_name=engineer_name.strip(), qty_taken=qty_req)
                            st.markdown("<div class='alert warn'>⚠  Low stock alert also sent.</div>",
                                        unsafe_allow_html=True)
                        st.balloons()
                    else:
                        df.loc[idx,"Quantity"] = cur
                        st.markdown("<div class='alert err'>✕  Save failed — close Excel file first.</div>", unsafe_allow_html=True)

    # ── INVENTORY ──────────────────────────────────────────────────────────────
    elif PAGE == "inventory":
        st.markdown("<div class='pg-title'>FULL INVENTORY</div>", unsafe_allow_html=True)
        st.markdown("<div class='pg-sub'>Complete stock register — all C&I instruments in main store</div>", unsafe_allow_html=True)

        f1,f2,f3 = st.columns(3)
        with f1: cf  = st.selectbox("CATEGORY", ["ALL"]+sorted(df["Category"].unique().tolist()))
        with f2: sf  = st.selectbox("STATUS", ["ALL","LOW STOCK","OUT OF STOCK","OK"])
        with f3: sof = st.selectbox("SORT BY", ["Item Code","Item Name","Qty: Low→High","Qty: High→Low"])

        view = df.copy()
        if cf  != "ALL":            view = view[view["Category"]==cf]
        if sf  == "LOW STOCK":      view = view[(view["Quantity"]<view["MinStock"]) & (view["Quantity"]>0)]
        elif sf == "OUT OF STOCK":  view = view[view["Quantity"]==0]
        elif sf == "OK":            view = view[view["Quantity"]>=view["MinStock"]]

        sc = {"Item Code":"ItemCode","Item Name":"ItemName","Qty: Low→High":"Quantity","Qty: High→Low":"Quantity"}
        view = view.sort_values(sc[sof], ascending=(sof!="Qty: High→Low"))
        view = view[["ItemCode","ItemName","Category","Quantity","MinStock","Location"]].copy()
        view["STATUS"] = df.loc[view.index].apply(
            lambda r: "🔴 Out of Stock" if r["Quantity"]==0
            else ("🟡 Low Stock" if r["Quantity"]<r["MinStock"] else "🟢 OK"), axis=1)
        view.columns = ["ITEM CODE","ITEM NAME","CATEGORY","QTY","MIN STOCK","LOCATION","STATUS"]

        st.markdown(f"""
        <div class='sec-hdr'>
            <span class='sec-hdr-left'>INVENTORY REGISTER</span>
            <span class='sec-hdr-badge'>{len(view)} OF {len(df)} ITEMS</span>
        </div>""", unsafe_allow_html=True)
        st.markdown(html_table(view, status_col="STATUS"), unsafe_allow_html=True)
        csv = view.to_csv(index=False).encode("utf-8")
        st.download_button("↓ EXPORT CSV", csv, f"inventory_{datetime.date.today()}.csv", "text/csv")

    # ── LOG ────────────────────────────────────────────────────────────────────
    elif PAGE == "log":
        st.markdown("<div class='pg-title'>TRANSACTION LOG</div>", unsafe_allow_html=True)
        st.markdown("<div class='pg-sub'>Complete audit trail of all instrument issues and returns</div>", unsafe_allow_html=True)

        if log_df.empty:
            st.markdown("<div class='alert info'>No transactions recorded yet. Issues will appear here automatically.</div>", unsafe_allow_html=True)
        else:
            k1,k2,k3 = st.columns(3)
            with k1:
                st.markdown(f"""<div class='kpi-box orange'>
                    <div class='kpi-label'>Total Transactions</div>
                    <div class='kpi-val orange'>{len(log_df)}</div>
                </div>""", unsafe_allow_html=True)
            with k2:
                st.markdown(f"""<div class='kpi-box orange'>
                    <div class='kpi-label'>Units Issued</div>
                    <div class='kpi-val orange'>{int(log_df["QuantityTaken"].sum())}</div>
                </div>""", unsafe_allow_html=True)
            with k3:
                st.markdown(f"""<div class='kpi-box orange'>
                    <div class='kpi-label'>Engineers</div>
                    <div class='kpi-val orange'>{log_df["EngineerName"].nunique()}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            fa,fb,fc = st.columns(3)
            with fa: ef  = st.selectbox("ENGINEER", ["ALL"]+sorted(log_df["EngineerName"].unique().tolist()))
            with fb: itf = st.selectbox("ITEM CODE",["ALL"]+sorted(log_df["ItemCode"].unique().tolist()))
            with fc: ord = st.selectbox("ORDER",    ["Latest First","Oldest First"])

            vl = log_df.copy()
            if ef  != "ALL": vl = vl[vl["EngineerName"]==ef]
            if itf != "ALL": vl = vl[vl["ItemCode"]    ==itf]
            if ord == "Latest First": vl = vl.iloc[::-1]

            st.markdown(f"""
            <div class='sec-hdr'>
                <span class='sec-hdr-left'>ALL TRANSACTIONS</span>
                <span class='sec-hdr-badge'>{len(vl)} RECORDS</span>
            </div>""", unsafe_allow_html=True)
            st.markdown(html_table(vl.reset_index(drop=True)), unsafe_allow_html=True)
            csv_l = vl.to_csv(index=False).encode("utf-8")
            st.download_button("↓ EXPORT LOG", csv_l, f"log_{datetime.date.today()}.csv", "text/csv")

    # ── ANALYTICS ──────────────────────────────────────────────────────────────
    elif PAGE == "analytics":
        st.markdown("<div class='pg-title'>USAGE ANALYTICS</div>", unsafe_allow_html=True)
        st.markdown("<div class='pg-sub'>Instrument consumption patterns · Adani Thermal Power Plant · C&I Main Store</div>",
                    unsafe_allow_html=True)

        if not ANALYTICS_READY:
            st.markdown("<div class='alert err'>✕  Analytics module not loaded. Check analytics.py.</div>",
                        unsafe_allow_html=True)
        else:
            adf = anlx.load_log()

            if adf.empty:
                st.markdown("<div class='alert info'>No transaction data yet. Issue instruments first — analytics will appear here.</div>",
                            unsafe_allow_html=True)
            else:
                # ── Summary KPIs ──────────────────────────────────────────────
                smry = anlx.generate_summary(adf)
                k1,k2,k3,k4 = st.columns(4)
                with k1:
                    st.markdown(f"""<div class='kpi-box orange'>
                        <div class='kpi-label'>Total Transactions</div>
                        <div class='kpi-val orange'>{smry.get('total_records',0)}</div>
                        <div class='kpi-sub'>{smry.get('date_from','—')} → {smry.get('date_to','—')}</div>
                    </div>""", unsafe_allow_html=True)
                with k2:
                    st.markdown(f"""<div class='kpi-box orange'>
                        <div class='kpi-label'>Total Units Issued</div>
                        <div class='kpi-val orange'>{smry.get('total_qty',0)}</div>
                        <div class='kpi-sub'>Across all instruments</div>
                    </div>""", unsafe_allow_html=True)
                with k3:
                    st.markdown(f"""<div class='kpi-box orange'>
                        <div class='kpi-label'>Unique Instruments</div>
                        <div class='kpi-val orange'>{smry.get('unique_items',0)}</div>
                        <div class='kpi-sub'>Different item types issued</div>
                    </div>""", unsafe_allow_html=True)
                with k4:
                    st.markdown(f"""<div class='kpi-box orange'>
                        <div class='kpi-label'>Engineers</div>
                        <div class='kpi-val orange'>{smry.get('unique_engineers',0)}</div>
                        <div class='kpi-sub'>Top: {smry.get('top_engineer','—')}</div>
                    </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── SECTION: Most Frequent ────────────────────────────────────
                st.markdown("""<div class='sec-hdr'>
                    <span class='sec-hdr-left'>▲ MOST FREQUENTLY ISSUED INSTRUMENTS</span>
                </div>""", unsafe_allow_html=True)
                mf = anlx.most_frequent_instruments(adf)
                if not mf.empty:
                    mf_disp = mf.copy()
                    mf_disp.columns = ["ITEM CODE","ITEM NAME","TIMES ISSUED","TOTAL QTY ISSUED"]
                    st.markdown(html_table(mf_disp), unsafe_allow_html=True)

                # ── SECTION: Least Used ───────────────────────────────────────
                st.markdown("""<div class='sec-hdr'>
                    <span class='sec-hdr-left'>▼ LEAST USED INSTRUMENTS</span>
                </div>""", unsafe_allow_html=True)
                lu = anlx.least_used_instruments(adf)
                if not lu.empty:
                    lu.columns = ["ITEM CODE","ITEM NAME","USAGE COUNT"]
                    st.markdown(html_table(lu), unsafe_allow_html=True)

                # ── SECTION: Top 10 Ranked ────────────────────────────────────
                st.markdown("""<div class='sec-hdr'>
                    <span class='sec-hdr-left'>◈ TOP 10 INSTRUMENTS — RANKED</span>
                </div>""", unsafe_allow_html=True)
                t10 = anlx.top10_instruments(adf)
                if not t10.empty:
                    t10.columns = ["RANK","ITEM CODE","ITEM NAME","TOTAL ISSUES","TOTAL QTY"]
                    st.markdown(html_table(t10), unsafe_allow_html=True)

                # ── CHARTS (2 per row) ────────────────────────────────────────
                st.markdown("""<div class='sec-hdr'>
                    <span class='sec-hdr-left'>◉ CHARTS &amp; VISUALIZATIONS</span>
                </div>""", unsafe_allow_html=True)

                ch1, ch2 = st.columns(2)
                with ch1:
                    fig1 = anlx.chart_top10(adf)
                    if fig1:
                        st.pyplot(fig1, use_container_width=True)
                        plt.close(fig1)
                with ch2:
                    fig2 = anlx.chart_department_pie(adf)
                    if fig2:
                        st.pyplot(fig2, use_container_width=True)
                        plt.close(fig2)

                ch3, ch4 = st.columns(2)
                with ch3:
                    fig3 = anlx.chart_monthly_trend(adf)
                    if fig3:
                        st.pyplot(fig3, use_container_width=True)
                        plt.close(fig3)
                with ch4:
                    fig4 = anlx.chart_category_usage(adf)
                    if fig4:
                        st.pyplot(fig4, use_container_width=True)
                        plt.close(fig4)

                # ── SECTION: Department Usage ─────────────────────────────────
                st.markdown("""<div class='sec-hdr'>
                    <span class='sec-hdr-left'>⊞ DEPARTMENT-WISE USAGE</span>
                </div>""", unsafe_allow_html=True)
                dept = anlx.department_usage(adf)
                if not dept.empty:
                    dept.columns = ["DEPARTMENT","TOTAL ISSUES","TOTAL QTY","TOP INSTRUMENT"]
                    st.markdown(html_table(dept), unsafe_allow_html=True)

                # ── SECTION: Monthly Trends ───────────────────────────────────
                st.markdown("""<div class='sec-hdr'>
                    <span class='sec-hdr-left'>📅 MONTHLY USAGE TRENDS</span>
                </div>""", unsafe_allow_html=True)
                mt = anlx.monthly_trends(adf)
                if not mt.empty:
                    mt.columns = ["MONTH","TOTAL ISSUES","TOTAL QTY ISSUED"]
                    st.markdown(html_table(mt), unsafe_allow_html=True)

                # ── SECTION: Critical Consumption ─────────────────────────────
                st.markdown("""<div class='sec-hdr'>
                    <span class='sec-hdr-left'>⚠ CRITICAL CONSUMPTION DETECTION</span>
                    <span class='sec-hdr-badge red'>ALERTS</span>
                </div>""", unsafe_allow_html=True)
                crit_df, alerts = anlx.critical_consumption(adf)
                if alerts:
                    for a in alerts:
                        st.markdown(f"<div class='alert warn'>⚠  {a}</div>", unsafe_allow_html=True)
                    if not crit_df.empty:
                        crit_df.columns = ["ITEM CODE","ITEM NAME","LAST 30 DAYS","PREV 30 DAYS","CHANGE %"]
                        st.markdown(html_table(crit_df), unsafe_allow_html=True)
                else:
                    st.markdown("<div class='alert ok'>✓ No critical consumption spikes detected in the last 30 days.</div>",
                                unsafe_allow_html=True)

                # ── Export ────────────────────────────────────────────────────
                st.markdown("<br>", unsafe_allow_html=True)
                full_csv = adf.to_csv(index=False).encode("utf-8")
                st.download_button("↓ EXPORT FULL ANALYTICS DATA",
                                   full_csv,
                                   f"analytics_{datetime.date.today()}.csv",
                                   "text/csv")

    st.markdown("</div>", unsafe_allow_html=True)
