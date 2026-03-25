import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import pytz
import plotly.graph_objects as go
from datetime import datetime
import os

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG — must be first, called exactly once
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Sales Performance Dashboard",
    page_icon="📊",
    layout="wide",
)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
# from oauth2client.service_account import ServiceAccountCredentials
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHEET_ID = "1wM7DTHizhg_A3h0qV3EhX4os4hk46uolW-ESQSJkgZs"
WORKSHEET_NAME = "retail_data"

G_DARK  = "#1B6B3A"
G_MID   = "#2E8B57"
C_HIGH  = "#E53935"
C_MED   = "#F59E0B"
C_LOW   = "#2E8B57"

# ══════════════════════════════════════════════════════════════════════════════
# SHARED CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
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
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def shorten_branch(name: str) -> str:
    """Last 4 chars for xxxM pattern (271M, 598M), last 3 for everything else."""
    s = str(name).strip()
    if not s:
        return s
    if re.match(r"^\d{3}M$", s[-4:]):
        return s[-4:]
    return s[-3:]


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
        sheet = gc.open_by_key(sheet_id).worksheet(worksheet_name)
        data  = sheet.get_all_records()
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
    return load_sheet_data(gc, SHEET_ID, WORKSHEET_NAME) if gc else pd.DataFrame()


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


# ══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════════════════
def chart_total_cases_bar(fdf):
    if "Source_Channel" not in fdf.columns:
        return
    branch_totals = (
        fdf.groupby("Source_Channel").size()
        .reset_index(name="Cases")
        .sort_values("Cases", ascending=False)
    )
    branch_totals["Label"] = branch_totals["Source_Channel"].apply(shorten_branch)
    if branch_totals.empty:
        st.info("No branch data available.")
        return
    n = len(branch_totals)
    colours = [f"rgba(27,107,58,{max(0.35, 1 - i*0.6/max(n-1,1)):.2f})" for i in range(n)]
    fig = go.Figure(go.Bar(
        x=branch_totals["Label"],
        y=branch_totals["Cases"],
        customdata=branch_totals["Source_Channel"],
        marker_color=colours, marker_line_width=0,
        text=branch_totals["Cases"], textposition="outside",
        textfont=dict(size=12, color=G_DARK, family="DM Sans", weight=700),
        hovertemplate="<b>%{customdata}</b><br>Total Cases: %{y}<extra></extra>",
    ))
    fig.update_layout(
        height=400, margin=dict(t=30, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=12, family="DM Sans", weight=600),
                   tickangle=0, automargin=True),
        yaxis=dict(showgrid=True, gridcolor="#EAF0EC", zeroline=False,
                   title=dict(text="Number of Cases", font=dict(size=12, family="DM Sans")),
                   tickfont=dict(size=11, family="DM Sans")),
        showlegend=False, bargap=0.3,
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="DM Sans"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def chart_cases_by_branch(fdf):
    if "Source_Channel" not in fdf.columns:
        return
    df = fdf.copy()
    df["_pot"]   = df.get("Potential_Level", pd.Series("", index=df.index)) \
                     .str.strip().str.upper().replace("", "?")
    df["_label"] = df["Source_Channel"].apply(shorten_branch)

    grp = df.groupby(["Source_Channel","_label","_pot"]).size().reset_index(name="Cases")
    total_per    = grp.groupby("Source_Channel")["Cases"].sum()
    branch_order = total_per.sort_values(ascending=True).index.tolist()
    label_map    = df[["Source_Channel","_label"]].drop_duplicates().set_index("Source_Channel")["_label"]
    label_order  = [label_map.get(b, b) for b in branch_order]
    bar_height   = max(320, len(branch_order) * 44 + 80)

    POT_CFG = {
        "H": {"color": C_HIGH,    "label": "High (H)"},
        "M": {"color": C_MED,     "label": "Medium (M)"},
        "L": {"color": C_LOW,     "label": "Low (L)"},
        "?": {"color": "#B0BEC5", "label": "Unknown"},
    }
    fig = go.Figure()
    for key, cfg in POT_CFG.items():
        sub = (grp[grp["_pot"] == key]
               .set_index("Source_Channel").reindex(branch_order, fill_value=0).reset_index())
        sub["_label"] = sub["Source_Channel"].apply(shorten_branch)
        fig.add_trace(go.Bar(
            name=cfg["label"], y=sub["_label"], x=sub["Cases"], orientation="h",
            marker_color=cfg["color"], marker_line_width=0,
            text=sub["Cases"].where(sub["Cases"]>0,"").astype(str).str.replace("^0$","",regex=True),
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color="white", family="DM Sans"),
            hovertemplate="<b>%{y}</b><br>" + cfg["label"] + ": %{x} cases<extra></extra>",
        ))

    totals = [int(total_per.get(b, 0)) for b in branch_order]
    fig.add_trace(go.Scatter(
        x=totals, y=label_order, mode="text",
        text=[f"  <b>{t}</b>" for t in totals],
        textposition="middle right",
        textfont=dict(size=12, color=G_DARK, family="DM Sans"),
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(
        barmode="stack", height=bar_height,
        margin=dict(t=10, b=10, l=10, r=70),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#EAF0EC", zeroline=False,
                   title=dict(text="Cases Collected", font=dict(size=12, family="DM Sans")),
                   tickfont=dict(size=11, family="DM Sans")),
        yaxis=dict(showgrid=False, tickfont=dict(size=12, family="DM Sans"), automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                    font=dict(size=12, family="DM Sans"), bgcolor="rgba(0,0,0,0)"),
        bargap=0.22, hoverlabel=dict(bgcolor="white", font_size=13, font_family="DM Sans"),
    )
    scroll_height = min(bar_height, 520)
    st.markdown(
        f'<div style="overflow-y:auto;max-height:{scroll_height}px;'
        f'border:1px solid #E0EAE4;border-radius:10px;padding:4px;">',
        unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def chart_potential_pie(fdf, branch_label):
    if "Potential_Level" not in fdf.columns:
        return
    counts = fdf["Potential_Level"].str.upper().value_counts().reset_index()
    counts.columns = ["Level","Count"]
    label_map = {"H":"High","M":"Medium","L":"Low"}
    color_map = {"High": C_HIGH, "Medium": C_MED, "Low": C_LOW, "Unknown":"#B0BEC5"}
    counts["Label"] = counts["Level"].map(label_map).fillna("Unknown")

    fig = go.Figure(go.Pie(
        labels=counts["Label"], values=counts["Count"],
        hole=0.55,
        marker_colors=[color_map.get(l,"#ccc") for l in counts["Label"]],
        marker_line=dict(color="#fff", width=3),
        textinfo="percent+label",
        textfont=dict(size=13, family="DM Sans", weight=600),
        insidetextorientation="radial",
        hovertemplate="<b>%{label}</b><br>Cases: %{value}<br>Share: %{percent}<extra></extra>",
        pull=[0.04 if l == "High" else 0 for l in counts["Label"]],
    ))
    fig.update_layout(
        height=320, margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)", showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5,
                    xanchor="left", x=1.02, font=dict(size=13, family="DM Sans")),
        annotations=[dict(
            text=f"<b>{branch_label}</b><br><span style='font-size:11px'>{counts['Count'].sum()} cases</span>",
            x=0.5, y=0.5, font=dict(size=15, color=G_DARK, family="DM Sans"), showarrow=False,
        )],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    today_label = datetime.now(pytz.timezone("Asia/Phnom_Penh")).strftime("%d %B %Y")

    # ── Sidebar navigation ────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 📊 Navigation")
        page = st.radio(
            "", ["📊 Summary", "🏢 Branch Detail"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.markdown("### ⚙️ Controls")
        if st.button("🧹 Clear Cache", use_container_width=True):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.success("Cache cleared!")
        if "service_account" in st.secrets:
            st.markdown("---")
            st.markdown("**Service account:**")
            st.code(st.secrets["service_account"].get("client_email", "not found"))

    # ── Load data (shared) ────────────────────────────────────────────────────
    with st.spinner("Loading data…"):
        raw_df = get_sheet_data()

    if raw_df.empty:
        st.info("💡 No data found. Check Google Sheets connection.")
        return

    display_df = prepare_df(raw_df)

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 1 — SUMMARY
    # ═════════════════════════════════════════════════════════════════════════
    if page == "📊 Summary":

        st.markdown(
            "<div class='banner'><h1>📊 Summary — All Branches</h1>"
            "<p>CMCB Bank &nbsp;·&nbsp; Overall Branch Performance</p>"
            f"<div class='badge'>📅 {today_label}</div></div>",
            unsafe_allow_html=True,
        )

        # Filters
        st.markdown("<div class='section'><div class='section-title'>🔍 Filter</div>", unsafe_allow_html=True)
        f1, f2 = st.columns([1, 2])
        with f1:
            sel_pot = st.selectbox("Customer Potential", ["All","H","M","L"])
        with f2:
            tz_now = datetime.now(pytz.timezone("Asia/Phnom_Penh")).date()
            d_mode = st.radio("Date range", ["Today","Custom"], horizontal=True)
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

        # Apply filters
        fdf = display_df.copy()
        if sel_pot != "All" and "Potential_Level" in fdf.columns:
            fdf = fdf[fdf["Potential_Level"].str.upper() == sel_pot]
        if "Message_Date" in fdf.columns:
            fdf = fdf[(fdf["Message_Date"].dt.date >= start_date) &
                      (fdf["Message_Date"].dt.date <= end_date)]

        # KPIs
        total = len(fdf)
        h_cnt = len(fdf[fdf["Potential_Level"].str.upper()=="H"]) if "Potential_Level" in fdf.columns else 0
        m_cnt = len(fdf[fdf["Potential_Level"].str.upper()=="M"]) if "Potential_Level" in fdf.columns else 0
        l_cnt = len(fdf[fdf["Potential_Level"].str.upper()=="L"]) if "Potential_Level" in fdf.columns else 0
        n_br  = fdf["Source_Channel"].nunique() if "Source_Channel" in fdf.columns else 0
        h_pct = f"{h_cnt/total*100:.0f}%" if total else "—"

        st.markdown(
            "<div class='kpi-row'>"
            f"<div class='kpi'><div class='val'>{total}</div><div class='lbl'>Total Cases</div></div>"
            f"<div class='kpi blue'><div class='val'>{n_br}</div><div class='lbl'>Active Branches</div></div>"
            f"<div class='kpi red'><div class='val'>{h_cnt}</div><div class='lbl'>High ({h_pct})</div></div>"
            f"<div class='kpi amber'><div class='val'>{m_cnt}</div><div class='lbl'>Medium</div></div>"
            f"<div class='kpi'><div class='val'>{l_cnt}</div><div class='lbl'>Low</div></div>"
            "</div>", unsafe_allow_html=True,
        )

        # Chart 1 — Ranked vertical bar
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-title'>🏆 Total Cases per Branch"
            "<span style='font-size:0.78rem;font-weight:400;color:#6B8C7A;margin-left:8px;'>"
            "Ranked · darker = more · hover for full branch name</span></div>",
            unsafe_allow_html=True,
        )
        chart_total_cases_bar(fdf)
        st.markdown("</div>", unsafe_allow_html=True)

        # Chart 2 — Stacked H/M/L
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-title'>📍 Cases by Branch &amp; Potential Level"
            "<span style='font-size:0.78rem;font-weight:400;color:#6B8C7A;margin-left:8px;'>"
            "Stacked H / M / L · scroll if needed</span></div>",
            unsafe_allow_html=True,
        )
        chart_cases_by_branch(fdf)
        st.markdown("</div>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 2 — BRANCH DETAIL
    # ═════════════════════════════════════════════════════════════════════════
    elif page == "🏢 Branch Detail":

        st.markdown(
            "<div class='banner'><h1>🏢 Branch Detail</h1>"
            "<p>CMCB Bank &nbsp;·&nbsp; Potential Customer Breakdown per Branch</p>"
            f"<div class='badge'>📅 {today_label}</div></div>",
            unsafe_allow_html=True,
        )

        if "Source_Channel" not in display_df.columns:
            st.error("Source_Channel column not found.")
            return

        all_branches = sorted(display_df["Source_Channel"].dropna().unique().tolist())

        # Filters
        st.markdown("<div class='section'><div class='section-title'>🔍 Select Branch &amp; Date</div>", unsafe_allow_html=True)
        f1, f2, f3 = st.columns([1.5, 1, 2])
        with f1:
            sel_branch = st.selectbox(
                "Branch", all_branches,
                format_func=lambda x: f"{shorten_branch(x)}  —  {x}",
            )
        with f2:
            sel_pot = st.selectbox("Potential", ["All","H","M","L"])
        with f3:
            tz_now = datetime.now(pytz.timezone("Asia/Phnom_Penh")).date()
            d_mode = st.radio("Date range", ["Today","Custom"], horizontal=True, key="br_date")
            if d_mode == "Today":
                start_date = end_date = tz_now
            else:
                if "Message_Date" in display_df.columns and display_df["Message_Date"].notna().any():
                    min_d = display_df["Message_Date"].min().date()
                    max_d = display_df["Message_Date"].max().date()
                else:
                    min_d = max_d = tz_now
                dc1, dc2 = st.columns(2)
                start_date = dc1.date_input("From", min_d, min_value=min_d, max_value=max_d, key="br_from")
                end_date   = dc2.date_input("To",   max_d, min_value=min_d, max_value=max_d, key="br_to")
        st.markdown("</div>", unsafe_allow_html=True)

        # Apply filters
        fdf = display_df[display_df["Source_Channel"] == sel_branch].copy()
        if "Message_Date" in fdf.columns:
            fdf = fdf[(fdf["Message_Date"].dt.date >= start_date) &
                      (fdf["Message_Date"].dt.date <= end_date)]

        branch_label = shorten_branch(sel_branch)

        # KPIs
        total = len(fdf)
        h_cnt = len(fdf[fdf["Potential_Level"].str.upper()=="H"]) if "Potential_Level" in fdf.columns else 0
        m_cnt = len(fdf[fdf["Potential_Level"].str.upper()=="M"]) if "Potential_Level" in fdf.columns else 0
        l_cnt = len(fdf[fdf["Potential_Level"].str.upper()=="L"]) if "Potential_Level" in fdf.columns else 0
        h_pct = f"{h_cnt/total*100:.0f}%" if total else "—"
        m_pct = f"{m_cnt/total*100:.0f}%" if total else "—"
        l_pct = f"{l_cnt/total*100:.0f}%" if total else "—"

        st.markdown(
            "<div class='kpi-row'>"
            f"<div class='kpi'><div class='val'>{total}</div><div class='lbl'>Total Cases</div></div>"
            f"<div class='kpi red'><div class='val'>{h_cnt}</div><div class='lbl'>High ({h_pct})</div></div>"
            f"<div class='kpi amber'><div class='val'>{m_cnt}</div><div class='lbl'>Medium ({m_pct})</div></div>"
            f"<div class='kpi'><div class='val'>{l_cnt}</div><div class='lbl'>Low ({l_pct})</div></div>"
            "</div>", unsafe_allow_html=True,
        )

        if total == 0:
            st.warning("No data found for this branch / date range.")
            return

        # Pie + Quick Stats
        col_pie, col_stats = st.columns([1.6, 1])

        with col_pie:
            st.markdown("<div class='section'>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='section-title'>🎯 Potential Mix — {branch_label}"
                f"<span style='font-size:0.78rem;font-weight:400;color:#6B8C7A;margin-left:8px;'>"
                f"{sel_branch}</span></div>",
                unsafe_allow_html=True,
            )
            chart_potential_pie(fdf, branch_label)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_stats:
            st.markdown("<div class='section'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>📋 Quick Stats</div>", unsafe_allow_html=True)

            def stat_row(label, value, color="#1B6B3A"):
                return (
                    f"<div style='display:flex;justify-content:space-between;align-items:center;"
                    f"padding:10px 0;border-bottom:1px solid #F0F4F2;'>"
                    f"<span style='font-size:0.85rem;color:#6B8C7A;font-weight:500;'>{label}</span>"
                    f"<span style='font-size:1rem;font-weight:700;color:{color};'>{value}</span></div>"
                )

            top_bank   = fdf["Bank"].value_counts().index[0] \
                         if "Bank" in fdf.columns and fdf["Bank"].str.strip().ne("").any() else "—"
            loan_types = fdf["Loan_Type"].nunique() if "Loan_Type" in fdf.columns else 0
            avg_int    = "—"
            if "Interest" in fdf.columns:
                nums = fdf["Interest"].str.replace("%","",regex=False) \
                           .apply(pd.to_numeric, errors="coerce").dropna()
                avg_int = f"{nums.mean():.1f}%" if not nums.empty else "—"

            st.markdown(
                stat_row("Total Cases",      total) +
                stat_row("High Potential",   f"{h_cnt}  ({h_pct})", C_HIGH) +
                stat_row("Medium Potential", f"{m_cnt}  ({m_pct})", "#B45309") +
                stat_row("Low Potential",    f"{l_cnt}  ({l_pct})", C_LOW) +
                stat_row("Top Bank",         top_bank) +
                stat_row("Loan Types",       loan_types) +
                stat_row("Avg Interest",     avg_int),
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # Customer table
        tdf_source = fdf.copy()
        if sel_pot != "All" and "Potential_Level" in tdf_source.columns:
            tdf_source = tdf_source[tdf_source["Potential_Level"].str.upper() == sel_pot]

        table_total = len(tdf_source)
        st.markdown(
            f"<div class='section'><div class='section-title'>👥 Customer List — {branch_label}"
            f"<span style='font-size:0.82rem;font-weight:400;color:#6B8C7A;margin-left:8px;'>"
            f"{table_total} records · sorted H → M → L</span></div>",
            unsafe_allow_html=True,
        )

        if table_total == 0:
            st.warning("No customers match the selected filters.")
        else:
            vis_cols = ["Name","Tel","Bank","Business","Amount","Interest",
                        "Loan_Type","Tenure","Maturity","Potential_Level","Potential_Product","Remark"]
            tdf = tdf_source[[c for c in vis_cols if c in tdf_source.columns]].copy()
            pot_order = {"H":1,"M":2,"L":3}
            info_cols = ["Amount","Bank","Interest","Loan_Type","Tenure","Maturity"]
            tdf["_p"] = tdf.get("Potential_Level", pd.Series(dtype=str)).map(pot_order).fillna(4)
            tdf["_i"] = tdf[[c for c in info_cols if c in tdf.columns]].apply(
                lambda r: sum(bool(str(x).strip()) for x in r), axis=1)
            tdf = tdf.sort_values(["_p","_i"], ascending=[True,False]).drop(columns=["_p","_i"])
            tdf = tdf.rename(columns={"Potential_Level":"Potential",
                                      "Potential_Product":"Product","Loan_Type":"Loan Type"})
            st.write(style_table(tdf).hide(axis="index").to_html(escape=False), unsafe_allow_html=True)

            st.markdown("&nbsp;")
            a1, a2, a3 = st.columns(3)
            with a1:
                st.download_button("📥 Download Branch Data", data=fdf.to_csv(index=False),
                                   file_name=f"{branch_label}_portfolio.csv", mime="text/csv",
                                   use_container_width=True)
            with a2:
                st.download_button("📥 Download Display Table", data=tdf.to_csv(index=False),
                                   file_name=f"{branch_label}_display.csv", mime="text/csv",
                                   use_container_width=True)
            with a3:
                if st.button("🔄 Refresh Data", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='text-align:center;color:#9AB0A2;font-size:.78rem;margin-top:28px;padding-bottom:20px;'>"
        f"Sales Performance Dashboard &nbsp;·&nbsp; CMCB Bank &nbsp;·&nbsp; {today_label}</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
