import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import random
import pytz
import plotly.graph_objects as go
from datetime import datetime
import os
import nest_asyncio

st.set_page_config(
    page_title="Sales Performance Dashboard",
    page_icon="📊",
    layout="wide",
)

# from oauth2client.service_account import ServiceAccountCredentials
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sheet_id = "1wM7DTHizhg_A3h0qV3EhX4os4hk46uolW-ESQSJkgZs"
worksheet_name = "retail_data"

# === MUST BE THE FIRST STREAMLIT COMMAND ===
st.set_page_config(
    page_title="Sales Performance Dashboard", layout="wide", page_icon="📊"
)

nest_asyncio.apply()

# Your credentials
api_id = 20056320
api_hash = "4b1394e0f07625a3c25ea32fa3030218"
# phone_number = os.environ["PHONE_NUMBER"]
# target = ["https://t.me/+JeQdy_3JC20wYTY1"]
session_name = "customer_session_2"
 
# ══════════════════════════════════════════════════════════════════════════════
# COLOUR CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
G_DARK  = "#1B6B3A"
G_MID   = "#2E8B57"
G_LIGHT = "#3CB371"
G_PALE  = "#E8F5EE"
 
C_HIGH  = "#E53935"   # red   — H potential
C_MED   = "#F59E0B"   # amber — M potential
C_LOW   = "#2E8B57"   # green — L potential
 
SHEET_ID       = st.secrets.get("sheet_id", "")
WORKSHEET_NAME = st.secrets.get("worksheet_name", "Sheet1")
 
# ══════════════════════════════════════════════════════════════════════════════
# CSS  (no f-string — plain string concat avoids brace conflicts)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #F4F7F5; }
[data-testid="stSidebar"]          { background: #fff; border-right: 1px solid #E0EAE4; }
 
.banner {
    background: linear-gradient(135deg, #1B6B3A 0%, #3CB371 100%);
    padding: 26px 34px; border-radius: 16px; color: #fff; margin-bottom: 24px;
}
.banner h1 { margin: 0 0 4px 0; font-size: 1.8rem; font-weight: 700; }
.banner p  { margin: 0; opacity: .82; font-size: 0.9rem; }
 
.section {
    background: #fff; border-radius: 14px; padding: 20px 24px;
    margin-bottom: 20px; border-left: 5px solid #2E8B57;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.section-title {
    font-size: 1rem; font-weight: 700; color: #1B6B3A;
    margin: 0 0 16px 0; display: flex; align-items: center; gap: 8px;
}
 
/* KPI tiles */
.kpi-row { display:flex; gap:14px; flex-wrap:wrap; margin-bottom:22px; }
.kpi {
    flex:1; min-width:110px; background:#fff; border-radius:12px;
    padding:15px 16px; text-align:center;
    box-shadow: 0 2px 6px rgba(0,0,0,.07);
    border-top: 4px solid #2E8B57;
}
.kpi .val { font-size:1.85rem; font-weight:700; color:#1B6B3A; line-height:1.1; }
.kpi .lbl { font-size:0.72rem; color:#6B8C7A; margin-top:4px;
            text-transform:uppercase; letter-spacing:.05em; }
.kpi.red   { border-top-color:#E53935; }
.kpi.red .val { color:#C62828; }
.kpi.amber { border-top-color:#F59E0B; }
.kpi.amber .val { color:#B45309; }
.kpi.blue  { border-top-color:#2563EB; }
.kpi.blue .val  { color:#1E40AF; }
 
/* Buttons */
.stButton>button {
    background: linear-gradient(135deg, #1B6B3A 0%, #3CB371 100%);
    color:#fff; border:none; border-radius:8px; font-weight:600;
    padding:10px 20px; transition:opacity .2s;
}
.stButton>button:hover { opacity:.86; }
</style>
""", unsafe_allow_html=True)
 
 
# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def connect_to_google_sheets():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ]
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
 
 
def load_sheet_data(_gc, sheet_id, worksheet_name):
    try:
        data = _gc.open_by_key(sheet_id).worksheet(worksheet_name).get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except gspread.SpreadsheetNotFound:
        st.error(f"❌ Spreadsheet not found: {sheet_id}"); return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ Worksheet not found: {worksheet_name}"); return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Load error: {e}"); return pd.DataFrame()
 
 
@st.cache_data
def get_telegram_data():
    gc = connect_to_google_sheets()
    return load_sheet_data(gc, SHEET_ID, WORKSHEET_NAME) if gc else pd.DataFrame()
 
 
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
# TABLE STYLER  (original — kept exactly as requested)
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
 
 
# ══════════════════════════════════════════════════════════════════════════════
# CHART 1 — Scrollable Cases per Branch (stacked H / M / L)
# ══════════════════════════════════════════════════════════════════════════════
def chart_cases_by_branch(fdf):
    if "Source_Channel" not in fdf.columns:
        st.info("Source_Channel column not found.")
        return
 
    df = fdf.copy()
    df["_pot"] = df.get("Potential_Level", pd.Series("", index=df.index)) \
                   .str.strip().str.upper().replace("", "?")
 
    # Count per branch × potential
    grp = (
        df.groupby(["Source_Channel", "_pot"])
        .size()
        .reset_index(name="Cases")
    )
    total_per_branch = grp.groupby("Source_Channel")["Cases"].sum()
    branch_order     = total_per_branch.sort_values(ascending=True).index.tolist()
    n_branches       = len(branch_order)
 
    # Dynamic height — 44px per branch, min 300px
    bar_height = max(320, n_branches * 44 + 80)
 
    POT_CFG = {
        "H": {"color": C_HIGH,  "label": "High (H)"},
        "M": {"color": C_MED,   "label": "Medium (M)"},
        "L": {"color": C_LOW,   "label": "Low (L)"},
        "?": {"color": "#B0BEC5","label": "Unknown"},
    }
 
    fig = go.Figure()
    for key, cfg in POT_CFG.items():
        sub = (
            grp[grp["_pot"] == key]
            .set_index("Source_Channel")
            .reindex(branch_order, fill_value=0)
            .reset_index()
        )
        fig.add_trace(go.Bar(
            name=cfg["label"],
            y=sub["Source_Channel"],
            x=sub["Cases"],
            orientation="h",
            marker_color=cfg["color"],
            text=sub["Cases"].where(sub["Cases"] > 0, "").astype(str).str.replace("^0$","",regex=True),
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=11, color="white"),
            hovertemplate="<b>%{y}</b><br>" + cfg["label"] + ": %{x} cases<extra></extra>",
        ))
 
    # Total labels on the right end of each bar
    totals = [int(total_per_branch.get(b, 0)) for b in branch_order]
    fig.add_trace(go.Scatter(
        x=totals,
        y=branch_order,
        mode="text",
        text=[f"  <b>{t}</b>" for t in totals],
        textposition="middle right",
        textfont=dict(size=12, color=G_DARK),
        showlegend=False,
        hoverinfo="skip",
    ))
 
    fig.update_layout(
        barmode="stack",
        height=bar_height,
        margin=dict(t=10, b=10, l=10, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=True, gridcolor="#E6EEE9",
            zeroline=False,
            title=dict(text="Cases Collected", font=dict(size=12)),
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(size=12),
            automargin=True,
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01,
            xanchor="left", x=0,
            font=dict(size=12),
            bgcolor="rgba(0,0,0,0)",
        ),
        bargap=0.22,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
 
    # Wrap in a scrollable div so the chart is always visible even with 50+ branches
    scroll_height = min(bar_height, 520)
    st.markdown(
        f'<div style="overflow-y:auto; max-height:{scroll_height}px; '
        f'border:1px solid #E0EAE4; border-radius:10px; padding:4px;">',
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
 
 
 
 
 
# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
 
    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        if st.button("🧹 Clear Cache", use_container_width=True):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.success("Cache cleared!")
        st.markdown("---")
        st.markdown("**Secrets keys:**")
        st.write(list(st.secrets.keys()))
 
    # ── Banner ────────────────────────────────────────────────────────────────
    today_label = datetime.now(pytz.timezone("Asia/Phnom_Penh")).strftime("%d %B %Y")
    st.markdown(
        "<div class='banner'>"
        "<h1>📊 Sales Performance Dashboard</h1>"
        "<p>CMCB Bank &nbsp;·&nbsp; Customer Portfolio &amp; Market Visit Report"
        " &nbsp;·&nbsp; " + today_label + "</p>"
        "</div>",
        unsafe_allow_html=True,
    )
 
    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner("Loading data…"):
        raw_df = get_telegram_data()
 
    if raw_df.empty:
        st.info("💡 No data found. Check Google Sheets connection.")
        return
 
    display_df = prepare_df(raw_df)
 
    # ── Filters ───────────────────────────────────────────────────────────────
    st.markdown("<div class='section'><div class='section-title'>🔍 Filter Portfolio</div>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1, 1, 2])
 
    all_branches = sorted(display_df["Source_Channel"].dropna().unique().tolist()) \
        if "Source_Channel" in display_df.columns else []
 
    with f1:
        sel_pot = st.selectbox("Customer Potential", ["All", "H", "M", "L"])
    with f2:
        sel_branch = st.selectbox("Branch / Market", ["All"] + all_branches)
    with f3:
        tz_now = datetime.now(pytz.timezone("Asia/Phnom_Penh")).date()
        d_mode = st.radio("Date range", ["Today", "Custom"], horizontal=True)
        if d_mode == "Today":
            start_date = end_date = tz_now
        else:
            if "Message_Date" in display_df.columns and display_df["Message_Date"].notna().any():
                min_d = display_df["Message_Date"].min().date()
                max_d = display_df["Message_Date"].max().date()
            else:
                min_d = max_d = tz_now
            dc1, dc2 = st.columns(2)
            start_date = dc1.date_input("From", min_d, min_value=min_d, max_value=max_d)
            end_date   = dc2.date_input("To",   max_d, min_value=min_d, max_value=max_d)
 
    st.markdown("</div>", unsafe_allow_html=True)
 
    # ── Apply filters ─────────────────────────────────────────────────────────
    fdf = display_df.copy()
    if sel_pot != "All" and "Potential_Level" in fdf.columns:
        fdf = fdf[fdf["Potential_Level"].str.upper() == sel_pot]
    if sel_branch != "All" and "Source_Channel" in fdf.columns:
        fdf = fdf[fdf["Source_Channel"] == sel_branch]
    if "Message_Date" in fdf.columns:
        fdf = fdf[
            (fdf["Message_Date"].dt.date >= start_date) &
            (fdf["Message_Date"].dt.date <= end_date)
        ]
 
    # ── KPI tiles ─────────────────────────────────────────────────────────────
    total = len(fdf)
    h_cnt = len(fdf[fdf["Potential_Level"].str.upper() == "H"]) if "Potential_Level" in fdf.columns else 0
    m_cnt = len(fdf[fdf["Potential_Level"].str.upper() == "M"]) if "Potential_Level" in fdf.columns else 0
    l_cnt = len(fdf[fdf["Potential_Level"].str.upper() == "L"]) if "Potential_Level" in fdf.columns else 0
    n_branches_active = fdf["Source_Channel"].nunique() if "Source_Channel" in fdf.columns else 0
    h_pct = f"{h_cnt/total*100:.0f}%" if total else "—"
 
    st.markdown(
        "<div class='kpi-row'>"
        f"<div class='kpi'><div class='val'>{total}</div><div class='lbl'>Total Cases</div></div>"
        f"<div class='kpi blue'><div class='val'>{n_branches_active}</div><div class='lbl'>Active Branches</div></div>"
        f"<div class='kpi red'><div class='val'>{h_cnt}</div><div class='lbl'>High Potential ({h_pct})</div></div>"
        f"<div class='kpi amber'><div class='val'>{m_cnt}</div><div class='lbl'>Medium Potential</div></div>"
        f"<div class='kpi'><div class='val'>{l_cnt}</div><div class='lbl'>Low Potential</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
 
    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — Cases by Branch (scrollable stacked bar)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<div class='section'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>📍 Cases Collected by Branch"
        "<span style='font-size:0.78rem;font-weight:400;color:#6B8C7A;margin-left:8px;'>"
        "Sorted by total · coloured by Potential Level · scroll if needed</span></div>",
        unsafe_allow_html=True,
    )
    chart_cases_by_branch(fdf)
    st.markdown("</div>", unsafe_allow_html=True)
 
    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — Customer Table (original, preserved)
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"<div class='section'><div class='section-title'>👥 Customer Portfolio"
        f"<span style='font-size:0.82rem;font-weight:400;color:#6B8C7A;margin-left:8px;'>"
        f"{total} records · sorted H → M → L, most complete info first</span></div>",
        unsafe_allow_html=True,
    )
 
    if total == 0:
        st.warning("No customers match the selected filters.")
    else:
        vis_cols = [
            "Name","Tel","Bank","Business","Amount","Interest",
            "Loan_Type","Tenure","Maturity","Potential_Level","Potential_Product","Remark",
        ]
        tdf = fdf[[c for c in vis_cols if c in fdf.columns]].copy()
 
        pot_order = {"H":1,"M":2,"L":3}
        info_cols = ["Amount","Bank","Interest","Loan_Type","Tenure","Maturity"]
        tdf["_p"] = tdf.get("Potential_Level", pd.Series(dtype=str)).map(pot_order).fillna(4)
        tdf["_i"] = tdf[[c for c in info_cols if c in tdf.columns]].apply(
            lambda r: sum(bool(str(x).strip()) for x in r), axis=1)
        tdf = tdf.sort_values(["_p","_i"], ascending=[True,False]).drop(columns=["_p","_i"])
        tdf = tdf.rename(columns={
            "Potential_Level":"Potential",
            "Potential_Product":"Product",
            "Loan_Type":"Loan Type",
        })
 
        st.write(
            style_table(tdf).hide(axis="index").to_html(escape=False),
            unsafe_allow_html=True,
        )
 
        st.markdown("&nbsp;")
        a1, a2, a3 = st.columns(3)
        with a1:
            st.download_button(
                "📥 Download Filtered Data",
                data=fdf.to_csv(index=False),
                file_name="filtered_portfolio.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with a2:
            st.download_button(
                "📥 Download Display Table",
                data=tdf.to_csv(index=False),
                file_name="display_portfolio.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with a3:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
 
    st.markdown("</div>", unsafe_allow_html=True)
 
    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='text-align:center;color:#9AB0A2;font-size:.78rem;margin-top:28px;'>"
        "Sales Performance Dashboard &nbsp;·&nbsp; CMCB Bank &nbsp;·&nbsp; " + today_label +
        "</div>",
        unsafe_allow_html=True,
    )
 
 
if __name__ == "__main__":
    main()
