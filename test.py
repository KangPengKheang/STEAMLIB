import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import pytz
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════════
# COLOUR CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
G_DARK  = "#1B6B3A"
G_MID   = "#2E8B57"
G_LIGHT = "#3CB371"
G_PALE  = "#E8F5EE"

C_HIGH  = "#E53935"
C_MED   = "#F59E0B"
C_LOW   = "#2E8B57"

# from oauth2client.service_account import ServiceAccountCredentials
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHEET_ID = "1wM7DTHizhg_A3h0qV3EhX4os4hk46uolW-ESQSJkgZs"
WORKSHEET_NAME = "retail_data"

SHARED_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
* { font-family: 'DM Sans', sans-serif; }

[data-testid="stAppViewContainer"] { background: #F0F4F2; }
[data-testid="stSidebar"]          { background: #fff; border-right: 1px solid #D8E8E0; }

.banner {
    background: linear-gradient(135deg, #0F4727 0%, #1B6B3A 45%, #3CB371 100%);
    padding: 30px 38px; border-radius: 18px; color: #fff; margin-bottom: 26px;
    box-shadow: 0 8px 32px rgba(27,107,58,0.25);
    position: relative; overflow: hidden;
}
.banner::before {
    content: ""; position: absolute; top: -40px; right: -40px;
    width: 200px; height: 200px; border-radius: 50%;
    background: rgba(255,255,255,0.06);
}
.banner h1 { margin: 0 0 6px 0; font-size: 1.9rem; font-weight: 700; letter-spacing: -0.3px; }
.banner p  { margin: 0; opacity: .80; font-size: 0.88rem; font-weight: 500; }
.banner .badge {
    display: inline-block; background: rgba(255,255,255,0.18);
    border-radius: 20px; padding: 3px 12px; font-size: 0.78rem;
    font-weight: 600; letter-spacing: 0.04em; margin-top: 10px;
    border: 1px solid rgba(255,255,255,0.25);
}

.section {
    background: #fff; border-radius: 16px; padding: 22px 26px;
    margin-bottom: 22px; border-left: 5px solid #2E8B57;
    box-shadow: 0 2px 12px rgba(0,0,0,.05);
}
.section-title {
    font-size: 1rem; font-weight: 700; color: #1B6B3A;
    margin: 0 0 18px 0; display: flex; align-items: center; gap: 8px;
}

.kpi-row { display:flex; gap:14px; flex-wrap:wrap; margin-bottom:22px; }
.kpi {
    flex:1; min-width:120px; background:#fff; border-radius:14px;
    padding:18px 18px; text-align:center;
    box-shadow: 0 2px 10px rgba(0,0,0,.07);
    border-top: 4px solid #2E8B57;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.kpi:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.10); }
.kpi .val { font-size:2rem; font-weight:700; color:#1B6B3A; line-height:1.1; letter-spacing:-1px; }
.kpi .lbl { font-size:0.70rem; color:#6B8C7A; margin-top:5px;
            text-transform:uppercase; letter-spacing:.07em; font-weight:600; }
.kpi.red    { border-top-color:#E53935; }
.kpi.red .val { color:#C62828; }
.kpi.amber  { border-top-color:#F59E0B; }
.kpi.amber .val { color:#B45309; }
.kpi.blue   { border-top-color:#2563EB; }
.kpi.blue .val  { color:#1E40AF; }

.stButton>button {
    background: linear-gradient(135deg, #1B6B3A 0%, #3CB371 100%);
    color:#fff; border:none; border-radius:9px; font-weight:600;
    padding:10px 22px; transition: opacity .2s, transform .15s;
    font-family: 'DM Sans', sans-serif;
}
.stButton>button:hover { opacity:.88; transform: translateY(-1px); }
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
# BRANCH LABEL HELPER
# ══════════════════════════════════════════════════════════════════════════════
def shorten_branch(name: str) -> str:
    """
    Return a short label for a Source_Channel value.
    - '...271M' or '...598M'  → last 4 characters (e.g. '271M', '598M')
    - everything else          → last 3 characters (e.g. 'NRM', 'PPH')
    """
    s = str(name).strip()
    if not s:
        return s
    # Check if the last 4 chars match the special pattern (digit+digit+digit+M)
    last4 = s[-4:]
    if re.match(r"^\d{3}M$", last4):
        return last4
    return s[-3:]


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def connect_to_google_sheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        if "service_account" not in st.secrets:
            st.error("❌ Google Sheets credentials not found in secrets.")
            return None
        creds_dict = dict(st.secrets["service_account"])
        for f in ["type", "project_id", "private_key", "client_email"]:
            if f not in creds_dict:
                st.error(f"❌ Missing field in secrets: {f}")
                return None
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Connection failed: {e}")
        return None


def load_sheet_data(gc, sheet_id, worksheet_name):
    try:
        spreadsheet = gc.open_by_key(sheet_id)
        sheet       = spreadsheet.worksheet(worksheet_name)
        data        = sheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except gspread.SpreadsheetNotFound:
        st.error(f"❌ Spreadsheet not found. ID: `{sheet_id}`")
        return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ Worksheet `{worksheet_name}` not found.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Load error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_sheet_data():
    gc = connect_to_google_sheets()
    if gc is None:
        return pd.DataFrame()
    return load_sheet_data(gc, SHEET_ID, WORKSHEET_NAME)


# ══════════════════════════════════════════════════════════════════════════════
# FORMATTERS
# ══════════════════════════════════════════════════════════════════════════════
def format_amount(value):
    if pd.isna(value) or str(value).strip() == "":
        return ""
    v = str(value).strip()
    if v.lower().endswith("k"):
        return v
    try:
        return f"${float(v.replace('$','').replace(',','')):,.2f}"
    except:
        return ""


def format_interest(value):
    if pd.isna(value) or str(value).strip() in ["", "nan", "None", "null"]:
        return ""
    clean = str(value).strip().replace("%", "").strip()
    for fn in [
        lambda x: float(x),
        lambda x: float(x.replace(",", "").replace(" ", "")),
        lambda x: (float(re.search(r"[-+]?\d*\.?\d+", x).group())
                   if re.search(r"[-+]?\d*\.?\d+", x) else None),
    ]:
        try:
            n = fn(clean)
            if n is not None:
                return f"{n:.1f}%"
        except:
            continue
    return ""


# ══════════════════════════════════════════════════════════════════════════════
# DATA PREP
# ══════════════════════════════════════════════════════════════════════════════
def prepare_df(raw):
    df = raw.copy()
    if "Name" in df.columns:
        df = df[df["Name"].notna() & (df["Name"].str.strip() != "")]
    if "Sender_Name" in df.columns:
        df = df[~df["Sender_Name"].str.strip().isin(["Zana MAM", "Khemra BUTH"])]
    if "Tel" in df.columns:
        df["Tel"] = df["Tel"].astype(str).apply(
            lambda x: f"0{x}" if x and not x.startswith("0") else x)
    if "Amount"   in df.columns: df["Amount"]   = df["Amount"].apply(format_amount)
    if "Interest" in df.columns: df["Interest"] = df["Interest"].apply(format_interest)
    if "Message_Date" in df.columns:
        df["Message_Date"] = pd.to_datetime(df["Message_Date"], errors="coerce").dt.normalize()
    for col in ["Name","Business","Bank","Loan_Type","Maturity","Tenure",
                "Source_Channel","Potential_Level"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace({"nan":"","None":"","N/A":""}).str.strip()
    return df


# ══════════════════════════════════════════════════════════════════════════════
# TABLE STYLER
# ══════════════════════════════════════════════════════════════════════════════
def style_table(df):
    def row_bg(row):
        lvl   = str(row.get("Potential","")).strip().upper()
        color = {"H":"#FFF3CD","M":"#E8F5E8","L":"#F8F9FA"}.get(lvl,"#FFFFFF")
        return [f"background-color:{color}"] * len(row)

    def pot_color(val):
        return {
            "H": "color:#C62828;font-weight:700;font-size:14px;",
            "M": "color:#E65100;font-weight:700;font-size:14px;",
            "L": "color:#2E7D32;font-weight:700;font-size:14px;",
        }.get(str(val).strip().upper(), "color:#6c757d;font-size:14px;")

    styler = df.style.hide(axis="index")
    styler = styler.apply(row_bg, axis=1)
    if "Potential" in df.columns:
        styler = styler.map(pot_color, subset=["Potential"])
    if "Amount" in df.columns:
        styler = styler.map(
            lambda _: "color:#1565C0;font-weight:700;font-size:14px;",
            subset=["Amount"])
    styler = styler.set_properties(**{
        "text-align":"left","white-space":"pre-wrap",
        "font-size":"14px","border":"1px solid #DEE2E6","padding":"9px 13px",
    })
    styler = styler.set_table_styles([
        {"selector":"table","props":[("table-layout","fixed"),("width","100%"),("border-collapse","collapse")]},
        {"selector":"th","props":[("background-color",G_MID),("color","white"),
                                  ("font-weight","bold"),("font-size","13px"),
                                  ("border","1px solid #1e6b4e"),("padding","10px 13px"),
                                  ("text-align","center")]},
        {"selector":"td","props":[("border","1px solid #DEE2E6"),("padding","9px 13px"),("vertical-align","top")]},
        {"selector":"th:nth-child(1),td:nth-child(1)","props":[("width","11%")]},
        {"selector":"th:nth-child(2),td:nth-child(2)","props":[("width","10%")]},
        {"selector":"th:nth-child(3),td:nth-child(3)","props":[("width","7%")]},
        {"selector":"th:nth-child(4),td:nth-child(4)","props":[("width","10%")]},
        {"selector":"th:nth-child(5),td:nth-child(5)","props":[("width","8%")]},
        {"selector":"th:nth-child(6),td:nth-child(6)","props":[("width","7%")]},
        {"selector":"th:nth-child(7),td:nth-child(7)","props":[("width","7%")]},
        {"selector":"th:nth-child(8),td:nth-child(8)","props":[("width","6%")]},
        {"selector":"th:nth-child(9),td:nth-child(9)","props":[("width","8%")]},
        {"selector":"th:nth-child(10),td:nth-child(10)","props":[("width","6%")]},
        {"selector":"th:nth-child(11),td:nth-child(11)","props":[("width","8%")]},
        {"selector":"th:nth-child(12),td:nth-child(12)","props":[("width","12%")]},
    ])
    return styler
