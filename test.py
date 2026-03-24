import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import random
import pytz
import plotly.graph_objects as go
from datetime import datetime

# from oauth2client.service_account import ServiceAccountCredentials
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHEET_ID = "1wM7DTHizhg_A3h0qV3EhX4os4hk46uolW-ESQSJkgZs"
WORKSHEET_NAME = "retail_data"

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

G_DARK  = "#1B6B3A"
G_MID   = "#2E8B57"
G_LIGHT = "#3CB371"
 
# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
_CSS = """
<style>
[data-testid="stAppViewContainer"] { background: #F4F7F5; }
[data-testid="stSidebar"] { background: #fff; border-right: 1px solid #E0EAE4; }
 
.banner {
    background: linear-gradient(135deg, """ + G_DARK + """ 0%, """ + G_LIGHT + """ 100%);
    padding: 28px 36px; border-radius: 16px; color: #fff; margin-bottom: 28px;
}
.banner h1 { margin: 0 0 4px 0; font-size: 1.85rem; font-weight: 700; }
.banner p  { margin: 0; opacity: .85; font-size: 0.92rem; }
 
.card {
    background: #fff; border-radius: 14px; padding: 20px 26px;
    margin-bottom: 18px; border-left: 5px solid """ + G_MID + """;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.card h3 { margin: 0; color: """ + G_DARK + """; font-size: 1.05rem; font-weight: 700; }
 
.kpi-row { display:flex; gap:14px; flex-wrap:wrap; margin-bottom:22px; }
.kpi {
    flex:1; min-width:120px; background:#fff; border-radius:12px;
    padding:16px 18px; text-align:center;
    box-shadow: 0 2px 6px rgba(0,0,0,.07);
    border-top: 4px solid """ + G_MID + """;
}
.kpi .val { font-size:1.9rem; font-weight:700; color:""" + G_DARK + """; line-height:1.1; }
.kpi .lbl { font-size:0.74rem; color:#6B8C7A; margin-top:4px; text-transform:uppercase; letter-spacing:.05em; }
.kpi.red   { border-top-color:#E53935; }
.kpi.amber { border-top-color:#F59E0B; }
.kpi.blue  { border-top-color:#2563EB; }
 
.chart-label {
    font-size:0.78rem; font-weight:700; color:""" + G_DARK + """;
    text-transform:uppercase; letter-spacing:.07em; margin-bottom:4px;
}
 
.stButton>button {
    background: linear-gradient(135deg, """ + G_DARK + """ 0%, """ + G_LIGHT + """ 100%);
    color:#fff; border:none; border-radius:8px; font-weight:600;
    padding:10px 20px; transition:opacity .2s;
}
.stButton>button:hover { opacity:.86; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)
 
 
# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS HELPERS
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
        for field in ["type", "project_id", "private_key", "client_email"]:
            if field not in creds_dict:
                st.error(f"❌ Missing field in secrets: {field}")
                return None
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"❌ Connection failed: {e}")
        return None
 
 
def load_sheet_data(_gc, sheet_id, worksheet_name):
    try:
        spreadsheet = _gc.open_by_key(sheet_id)
        sheet       = spreadsheet.worksheet(worksheet_name)
        data        = sheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except gspread.SpreadsheetNotFound:
        st.error(f"❌ Spreadsheet not found: {sheet_id}")
        return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ Worksheet not found: {worksheet_name}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Load error: {e}")
        return pd.DataFrame()
 
 
@st.cache_data
def get_telegram_data():
    gc = connect_to_google_sheets()
    if gc:
        return load_sheet_data(gc, SHEET_ID, WORKSHEET_NAME)
    return pd.DataFrame()
 
 
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
        lambda x: (
            float(re.search(r"[-+]?\d*\.?\d+", x).group())
            if re.search(r"[-+]?\d*\.?\d+", x) else None
        ),
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
def prepare_display_df(raw_df):
    df = raw_df.copy()
    if "Name" in df.columns:
        df = df[df["Name"].notna() & (df["Name"].str.strip() != "")]
    if "Sender_Name" in df.columns:
        df = df[~df["Sender_Name"].str.strip().isin(["Zana MAM", "Khemra BUTH"])]
    if "Tel" in df.columns:
        df["Tel"] = df["Tel"].astype(str).apply(
            lambda x: f"0{x}" if x and not x.startswith("0") else x
        )
    if "Amount"   in df.columns: df["Amount"]   = df["Amount"].apply(format_amount)
    if "Interest" in df.columns: df["Interest"] = df["Interest"].apply(format_interest)
    if "Message_Date" in df.columns:
        df["Message_Date"] = pd.to_datetime(df["Message_Date"], errors="coerce").dt.normalize()
    for col in ["Name","Business","Bank","Loan_Type","Maturity","Tenure","Source_Channel","Potential_Level"]:
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
            "H":"color:#C62828;font-weight:700;font-size:14px;",
            "M":"color:#E65100;font-weight:700;font-size:14px;",
            "L":"color:#2E7D32;font-weight:700;font-size:14px;",
        }.get(str(val).strip().upper(), "color:#6c757d;font-size:14px;")
 
    styler = df.style.hide(axis="index")
    styler = styler.apply(row_bg, axis=1)
    if "Potential" in df.columns:
        styler = styler.map(pot_color, subset=["Potential"])
    if "Amount" in df.columns:
        styler = styler.map(
            lambda _: "color:#1565C0;font-weight:700;font-size:14px;",
            subset=["Amount"],
        )
    styler = styler.set_properties(**{
        "text-align":"left","white-space":"pre-wrap",
        "font-size":"14px","border":"1px solid #DEE2E6","padding":"9px 13px",
    })
    styler = styler.set_table_styles([
        {"selector":"table","props":[("table-layout","fixed"),("width","100%"),("border-collapse","collapse")]},
        {"selector":"th","props":[("background-color",G_MID),("color","white"),("font-weight","bold"),
                                  ("font-size","13px"),("border","1px solid #1e6b4e"),
                                  ("padding","10px 13px"),("text-align","center")]},
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
# BANK × BRANCH CHARTS
# ══════════════════════════════════════════════════════════════════════════════
def render_bank_charts(filtered_df):
    """
    Left  — Horizontal bar: overall customer count per Bank
    Right — Stacked bar: each Branch broken down by Bank
    Below — Expandable pivot table
    """
    if "Bank" not in filtered_df.columns or "Source_Channel" not in filtered_df.columns:
        st.warning("⚠️ 'Bank' or 'Source_Channel' column missing.")
        return
 
    df = filtered_df[["Source_Channel", "Bank"]].copy()
    df = df[df["Source_Channel"].str.strip().ne("") & df["Bank"].str.strip().ne("")]
 
    if df.empty:
        st.info("No bank / branch data for the selected filters.")
        return
 
    # ── KPI tiles ─────────────────────────────────────────────────────────────
    n_branches = df["Source_Channel"].nunique()
    n_banks    = df["Bank"].nunique()
    top_bank   = df["Bank"].value_counts().idxmax()
    top_branch = df["Source_Channel"].value_counts().idxmax()
 
    st.markdown(
        f"""
        <div class="kpi-row">
            <div class="kpi">
                <div class="val">{n_branches}</div>
                <div class="lbl">Branches</div>
            </div>
            <div class="kpi blue">
                <div class="val">{n_banks}</div>
                <div class="lbl">Banks Found</div>
            </div>
            <div class="kpi amber">
                <div class="val" style="font-size:1.25rem">{top_bank}</div>
                <div class="lbl">Top Bank</div>
            </div>
            <div class="kpi red">
                <div class="val" style="font-size:1.05rem">{top_branch}</div>
                <div class="lbl">Busiest Branch</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
 
    # ── Consistent colour per bank ────────────────────────────────────────────
    banks_by_freq = df["Bank"].value_counts().index.tolist()
    PALETTE = [
        "#2E8B57","#2563EB","#F59E0B","#E53935","#7C3AED",
        "#0891B2","#EA580C","#16A34A","#DB2777","#64748B",
    ]
    color_map = {b: PALETTE[i % len(PALETTE)] for i, b in enumerate(banks_by_freq)}
 
    col_l, col_r = st.columns([1, 2], gap="large")
 
    # ── LEFT: Overall bank totals ─────────────────────────────────────────────
    with col_l:
        st.markdown('<p class="chart-label">Overall Bank Share</p>', unsafe_allow_html=True)
 
        vc = df["Bank"].value_counts().reset_index()
        vc.columns = ["Bank", "Customers"]
        vc = vc.sort_values("Customers", ascending=True)
 
        fig_h = go.Figure(go.Bar(
            x=vc["Customers"],
            y=vc["Bank"],
            orientation="h",
            marker_color=[color_map.get(b, G_MID) for b in vc["Bank"]],
            text=vc["Customers"],
            textposition="outside",
            textfont=dict(size=13, color="#1B3A2D"),
            hovertemplate="<b>%{y}</b>: %{x} customers<extra></extra>",
        ))
        fig_h.update_layout(
            height=max(260, len(vc) * 46 + 60),
            margin=dict(t=8, b=8, l=8, r=52),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="#E6EEE9", zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, tickfont=dict(size=13)),
            showlegend=False,
            bargap=0.28,
        )
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})
 
    # ── RIGHT: Branch × Bank stacked bar ─────────────────────────────────────
    with col_r:
        st.markdown('<p class="chart-label">Bank Distribution by Branch</p>', unsafe_allow_html=True)
 
        bb = (
            df.groupby(["Source_Channel", "Bank"])
            .size()
            .reset_index(name="n")
        )
        branch_order = (
            bb.groupby("Source_Channel")["n"]
            .sum()
            .sort_values(ascending=False)
            .index.tolist()
        )
 
        fig_s = go.Figure()
        for bank in banks_by_freq:
            sub = (
                bb[bb["Bank"] == bank]
                .set_index("Source_Channel")
                .reindex(branch_order, fill_value=0)
                .reset_index()
            )
            fig_s.add_trace(go.Bar(
                name=bank,
                x=sub["Source_Channel"],
                y=sub["n"],
                marker_color=color_map[bank],
                text=sub["n"].where(sub["n"] > 0, "").astype(str).str.replace("0",""),
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(size=11, color="white"),
                hovertemplate=f"<b>{bank}</b><br>%{{x}}: %{{y}} customers<extra></extra>",
            ))
 
        fig_s.update_layout(
            barmode="stack",
            height=420,
            margin=dict(t=8, b=90, l=8, r=8),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                tickangle=-38, tickfont=dict(size=11), showgrid=False,
                categoryorder="array", categoryarray=branch_order,
            ),
            yaxis=dict(
                showgrid=True, gridcolor="#E6EEE9", zeroline=False,
                title=dict(text="Customers", font=dict(size=12)),
                tickfont=dict(size=11),
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.01,
                xanchor="left", x=0,
                font=dict(size=12),
                bgcolor="rgba(0,0,0,0)",
                itemwidth=40,
            ),
            hoverlabel=dict(bgcolor="white", font_size=13),
            bargap=0.18,
        )
        st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False})
 
    # ── Pivot table (collapsed by default) ───────────────────────────────────
    with st.expander("📋 Full Branch × Bank breakdown table"):
        pivot = (
            df.groupby(["Source_Channel", "Bank"])
            .size()
            .unstack(fill_value=0)
        )
        pivot.index.name = "Branch"
        pivot["Total"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("Total", ascending=False)
 
        bank_cols = [c for c in pivot.columns if c != "Total"]
        st.dataframe(
            pivot.style
                .background_gradient(cmap="Greens", subset=bank_cols, axis=None)
                .format(precision=0)
                .set_properties(**{"text-align": "center"})
                .set_table_styles([
                    {"selector": "th", "props": [
                        ("background-color", G_MID),
                        ("color", "white"),
                        ("font-weight", "bold"),
                    ]},
                    {"selector": "td:last-child", "props": [
                        ("font-weight", "700"),
                        ("color", G_DARK),
                    ]},
                ]),
            use_container_width=True,
        )
 
 
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
        f"""
        <div class="banner">
            <h1>📊 Sales Performance Dashboard</h1>
            <p>CMCB Bank &nbsp;·&nbsp; Customer Portfolio &amp; Market Visit Report &nbsp;·&nbsp; {today_label}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
 
    # ── Load ──────────────────────────────────────────────────────────────────
    with st.spinner("Loading data…"):
        raw_df = get_telegram_data()
 
    if raw_df.empty:
        st.info("💡 No data found. Check your Google Sheets connection and secrets.")
        with st.expander("🆕 Setup guide"):
            st.markdown("""
            1. Share the Google Sheet with your service account email.
            2. Set `sheet_id` and `worksheet_name` in Streamlit secrets.
            3. Add `service_account` credentials block to secrets.
            """)
        return
 
    display_df = prepare_display_df(raw_df)
 
    # ── Filters ───────────────────────────────────────────────────────────────
    st.markdown('<div class="card"><h3>🔍 Filter Portfolio</h3></div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1, 1, 2])
 
    all_branches = (
        sorted(display_df["Source_Channel"].dropna().unique().tolist())
        if "Source_Channel" in display_df.columns else []
    )
 
    with f1:
        selected_potential = st.selectbox("Customer Potential", ["All", "H", "M", "L"])
    with f2:
        selected_branch = st.selectbox("Branch / Market", ["All"] + all_branches)
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
 
    # ── Apply filters ─────────────────────────────────────────────────────────
    fdf = display_df.copy()
    if selected_potential != "All" and "Potential_Level" in fdf.columns:
        fdf = fdf[fdf["Potential_Level"].str.upper() == selected_potential]
    if selected_branch != "All" and "Source_Channel" in fdf.columns:
        fdf = fdf[fdf["Source_Channel"] == selected_branch]
    if "Message_Date" in fdf.columns:
        fdf = fdf[
            (fdf["Message_Date"].dt.date >= start_date) &
            (fdf["Message_Date"].dt.date <= end_date)
        ]
 
    # ── Portfolio KPIs ────────────────────────────────────────────────────────
    total = len(fdf)
    h_cnt = len(fdf[fdf["Potential_Level"].str.upper() == "H"]) if "Potential_Level" in fdf.columns else 0
    m_cnt = len(fdf[fdf["Potential_Level"].str.upper() == "M"]) if "Potential_Level" in fdf.columns else 0
    l_cnt = len(fdf[fdf["Potential_Level"].str.upper() == "L"]) if "Potential_Level" in fdf.columns else 0
    h_pct = f"{h_cnt/total*100:.0f}%" if total else "—"
 
    st.markdown(
        f"""
        <div class="kpi-row">
            <div class="kpi">
                <div class="val">{total}</div>
                <div class="lbl">Total Customers</div>
            </div>
            <div class="kpi red">
                <div class="val">{h_cnt}</div>
                <div class="lbl">High Potential ({h_pct})</div>
            </div>
            <div class="kpi amber">
                <div class="val">{m_cnt}</div>
                <div class="lbl">Medium Potential</div>
            </div>
            <div class="kpi">
                <div class="val">{l_cnt}</div>
                <div class="lbl">Low Potential</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
 
    # ══════════════════════════════════════════════════════════════════════════
    # BANK × BRANCH SECTION
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="card"><h3>🏦 Bank Information Gathered from the Market</h3></div>',
        unsafe_allow_html=True,
    )
    render_bank_charts(fdf)
 
    st.markdown("---")
 
    # ══════════════════════════════════════════════════════════════════════════
    # CUSTOMER TABLE
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(
        f'<div class="card"><h3>👥 Customer Portfolio &nbsp;·&nbsp; {total} records</h3></div>',
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
            lambda r: sum(bool(str(x).strip()) for x in r), axis=1
        )
        tdf = tdf.sort_values(["_p","_i"], ascending=[True,False]).drop(columns=["_p","_i"])
        tdf = tdf.rename(columns={
            "Potential_Level": "Potential",
            "Potential_Product": "Product",
            "Loan_Type": "Loan Type",
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
 
    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='text-align:center;color:#9AB0A2;font-size:.8rem;margin-top:32px;'>"
        f"Sales Performance Dashboard &nbsp;·&nbsp; CMCB Bank &nbsp;·&nbsp; {today_label}"
        f"</div>",
        unsafe_allow_html=True,
    )
 
 
if __name__ == "__main__":
    main()
 
