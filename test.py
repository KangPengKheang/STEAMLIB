import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import random
import pytz
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import nest_asyncio
import os

# === Page Config ===
st.set_page_config(
    page_title="Sales Performance Dashboard",
    page_icon="📊",
    layout="wide",
)

# from oauth2client.service_account import ServiceAccountCredentials
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHEET_ID = "1wM7DTHizhg_A3h0qV3EhX4os4hk46uolW-ESQSJkgZs"
WORKSHEET_NAME = "retail_data"

# # === Constants ===
# SHEET_ID = st.secrets.get("1wM7DTHizhg_A3h0qV3EhX4os4hk46uolW-ESQSJkgZs", "")
# WORKSHEET_NAME = st.secrets.get("retail_data", "Sheet1")

# === MUST BE THE FIRST STREAMLIT COMMAND ===
st.set_page_config(
    page_title="Sales Performance Dashboard", layout="wide", page_icon="📊"
)
nest_asyncio.apply()

# Your credentials
api_id = 20056320
api_hash = "4b1394e0f07625a3c25ea32fa3030218"
session_name = "customer_session_2"

# === Custom CSS ===
st.markdown(
    """
<style>
    .main-header {
        background: linear-gradient(135deg, #2E8B57 0%, #3CB371 100%);
        padding: 25px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .function-card {
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 25px;
        border-left: 5px solid #2E8B57;
    }
    .metric-card {
        background: linear-gradient(135deg, #f0f8ff 0%, #e0f0e0 100%);
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .stButton>button {
        background: linear-gradient(135deg, #2E8B57 0%, #3CB371 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .highlight {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin: 10px 0;
    }
    .tab-content {
        padding: 20px;
        background: white;
        border-radius: 0 0 15px 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .header-style {
        background: linear-gradient(90deg, #2E8B57 0%, #3CB371 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 15px 0;
        font-size: 1.3em;
        font-weight: bold;
    }
</style>
""",
    unsafe_allow_html=True,
)
 
 
# === Google Sheets Connection ===
@st.cache_resource
def connect_to_google_sheets():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ]
 
        if "service_account" not in st.secrets:
            st.error("❌ Google Sheets credentials not found in secrets")
            st.info("Please add your service account credentials to Streamlit secrets")
            return None
 
        creds_dict = dict(st.secrets["service_account"])
 
        required_fields = ["type", "project_id", "private_key", "client_email"]
        for field in required_fields:
            if field not in creds_dict:
                st.error(f"❌ Missing required field in secrets: {field}")
                return None
 
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=scope,
        )
        gc = gspread.authorize(credentials)
        return gc
 
    except Exception as e:
        st.error(f"❌ Failed to connect to Google Sheets: {str(e)}")
        st.info(
            "💡 Make sure your Google Sheet is shared with: "
            + st.secrets["service_account"].get("client_email", "N/A")
        )
        return None
 
 
def load_sheet_data(_gc, sheet_id, worksheet_name):
    try:
        if _gc is None:
            st.error("❌ Google Sheets client is not initialized")
            return pd.DataFrame()
        if not sheet_id:
            st.error("❌ Sheet ID is required")
            return pd.DataFrame()
        if not worksheet_name:
            st.error("❌ Worksheet name is required")
            return pd.DataFrame()
 
        try:
            spreadsheet = _gc.open_by_key(sheet_id)
        except gspread.SpreadsheetNotFound:
            st.error(f"❌ Spreadsheet not found with ID: {sheet_id}")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Failed to open spreadsheet: {str(e)}")
            return pd.DataFrame()
 
        try:
            sheet = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            st.error(f"❌ Worksheet '{worksheet_name}' not found in the spreadsheet")
            return pd.DataFrame()
 
        try:
            data = sheet.get_all_records()
            if not data:
                st.info(f"📭 No data found in worksheet '{worksheet_name}'")
                return pd.DataFrame()
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"❌ Failed to read data from worksheet: {str(e)}")
            return pd.DataFrame()
 
    except Exception as e:
        st.error(f"❌ Unexpected error loading from Google Sheets: {str(e)}")
        return pd.DataFrame()
 
 
@st.cache_data
def get_telegram_data():
    gc = connect_to_google_sheets()
    if gc:
        df = load_sheet_data(gc, SHEET_ID, WORKSHEET_NAME)
        return df
    return pd.DataFrame()
 
 
# === Formatters ===
def format_amount(value):
    if pd.isna(value) or str(value).strip() == "":
        return ""
    val_str = str(value).strip()
    if val_str.lower().endswith("k"):
        return val_str
    try:
        num = float(val_str.replace("$", "").replace(",", ""))
        return f"${num:,.2f}"
    except:
        return ""
 
 
def format_interest(value):
    if pd.isna(value) or str(value).strip() in ["", "nan", "None", "null"]:
        return ""
    val_str = str(value).strip()
    clean_val = val_str.replace("%", "").strip()
    conversion_attempts = [
        lambda x: float(x),
        lambda x: float(x.replace(",", "").replace(" ", "")),
        lambda x: (
            float(re.search(r"[-+]?\d*\.?\d+", x).group())
            if re.search(r"[-+]?\d*\.?\d+", x)
            else None
        ),
    ]
    for convert_func in conversion_attempts:
        try:
            num = convert_func(clean_val)
            if num is not None:
                return f"{num:.1f}%"
        except (ValueError, AttributeError):
            continue
    return ""
 
 
# === Data Preparation ===
@st.cache_data
def prepare_sales_df(raw_df):
    raw_df = raw_df[
        raw_df["Name"].notna()
        & (raw_df["Name"].str.strip() != "")
        & (raw_df["Sender_Name"].str.strip() != "Zana MAM")
        & (raw_df["Sender_Name"].str.strip() != "Khemra BUTH")
    ]
    df = raw_df.copy()
    if "Tel" in df.columns:
        df["Tel"] = df["Tel"].astype(str).apply(
            lambda x: f"0{x}" if x and not x.startswith("0") else x
        )
    if "Amount" in df.columns:
        df["Amount"] = df["Amount"].apply(format_amount)
    if "Interest" in df.columns:
        df["Interest"] = df["Interest"].apply(format_interest)
    if "Message_Date" in df.columns:
        df["Message_Date"] = pd.to_datetime(df["Message_Date"], errors="coerce")
    return df
 
 
# === Styling ===
def style_sales_dataframe(df):
    styler = df.style.hide(axis="index")
 
    if "Potential" in df.columns:
        styler = styler.apply(
            lambda row: [
                (
                    "background-color: #fff3cd"
                    if str(row.get("Potential", "")).strip().upper() == "H"
                    else (
                        "background-color: #e8f5e8"
                        if str(row.get("Potential", "")).strip().upper() == "M"
                        else "background-color: #f8f9fa"
                    )
                )
                for _ in row
            ],
            axis=1,
        )
 
    def color_potential(val):
        if str(val).strip().upper() == "H":
            return "color: #d32f2f; font-weight: bold; font-size: 14px;"
        elif str(val).strip().upper() == "M":
            return "color: #f57c00; font-weight: bold; font-size: 14px;"
        elif str(val).strip().upper() == "L":
            return "color: #388e3c; font-weight: bold; font-size: 14px;"
        return "color: #6c757d; font-size: 14px;"
 
    if "Potential" in df.columns:
        styler = styler.map(color_potential, subset=["Potential"])
 
    if "Amount" in df.columns:
        styler = styler.map(
            lambda val: "color: #1e88e5; font-weight: bold; font-size: 14px;",
            subset=["Amount"],
        )
 
    styler = styler.set_properties(
        **{
            "text-align": "left",
            "white-space": "pre-wrap",
            "font-size": "18px",
            "border": "1px solid #dee2e6",
            "padding": "10px 14px",
        }
    )
 
    styler = styler.set_table_styles(
        [
            {
                "selector": "table",
                "props": [
                    ("table-layout", "fixed"),
                    ("width", "100%"),
                    ("border-collapse", "collapse"),
                ],
            },
            {
                "selector": "th",
                "props": [
                    ("background-color", "#2E8B57"),
                    ("color", "white"),
                    ("font-weight", "bold"),
                    ("text-align", "center"),
                    ("font-size", "15px"),
                    ("border", "1px solid #1e6b4e"),
                    ("padding", "10px 14px"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("border", "1px solid #dee2e6"),
                    ("padding", "10px 14px"),
                    ("vertical-align", "top"),
                ],
            },
            {"selector": "th:nth-child(1), td:nth-child(1)", "props": [("width", "10%")]},
            {"selector": "th:nth-child(2), td:nth-child(2)", "props": [("width", "10%")]},
            {"selector": "th:nth-child(3), td:nth-child(3)", "props": [("width", "5%")]},
            {"selector": "th:nth-child(4), td:nth-child(4)", "props": [("width", "10%")]},
            {"selector": "th:nth-child(5), td:nth-child(5)", "props": [("width", "5%")]},
            {"selector": "th:nth-child(6), td:nth-child(6)", "props": [("width", "5%")]},
            {"selector": "th:nth-child(7), td:nth-child(7)", "props": [("width", "5%")]},
            {"selector": "th:nth-child(8), td:nth-child(8)", "props": [("width", "5%")]},
            {"selector": "th:nth-child(9), td:nth-child(9)", "props": [("width", "5%")]},
            {"selector": "th:nth-child(10), td:nth-child(10)", "props": [("width", "5%")]},
            {"selector": "th:nth-child(11), td:nth-child(11)", "props": [("width", "10%")]},
            {"selector": "th:nth-child(12), td:nth-child(12)", "props": [("width", "15%")]},
        ]
    )
    return styler
 
 
# === Bank Distribution Charts ===
def render_bank_branch_charts(filtered_df):
    st.markdown("### 🏦 Bank Information Gathered from Each Branch / Market")
 
    if "Bank" not in filtered_df.columns or "Source_Channel" not in filtered_df.columns:
        st.warning("⚠️ Columns 'Bank' or 'Source_Channel' not found in the dataset.")
        return
 
    chart_df = filtered_df[["Source_Channel", "Bank"]].copy()
    chart_df = chart_df[
        chart_df["Source_Channel"].notna()
        & (chart_df["Source_Channel"].str.strip() != "")
        & chart_df["Bank"].notna()
        & (chart_df["Bank"].str.strip() != "")
    ]
 
    if chart_df.empty:
        st.info("No bank / branch data available for the current filters.")
        return
 
    # ── Grouped count ──────────────────────────────────────────────────────────
    bank_branch_count = (
        chart_df.groupby(["Source_Channel", "Bank"])
        .size()
        .reset_index(name="Customers")
    )
 
    # ── Summary metrics row ────────────────────────────────────────────────────
    total_branches = chart_df["Source_Channel"].nunique()
    total_banks = chart_df["Bank"].nunique()
    top_bank = chart_df["Bank"].value_counts().idxmax()
    top_branch = chart_df["Source_Channel"].value_counts().idxmax()
 
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Branches Reporting", total_branches)
    m2.metric("Unique Banks Found", total_banks)
    m3.metric("Most Common Bank", top_bank)
    m4.metric("Busiest Branch", top_branch)
 
    st.markdown("---")
 
    # ── Tab layout for charts ──────────────────────────────────────────────────
    chart_tab1, chart_tab2, chart_tab3 = st.tabs(
        ["📊 Stacked Bar", "🌡️ Heat Map", "🥧 Bank Share"]
    )
 
    # ── TAB 1: Stacked bar ─────────────────────────────────────────────────────
    with chart_tab1:
        st.markdown(
            "Each bar represents one **Branch/Market**. "
            "Segments show how many customers hold a loan with each bank."
        )
 
        branch_order = (
            bank_branch_count.groupby("Source_Channel")["Customers"]
            .sum()
            .sort_values(ascending=False)
            .index.tolist()
        )
 
        fig_stacked = px.bar(
            bank_branch_count,
            x="Source_Channel",
            y="Customers",
            color="Bank",
            barmode="stack",
            category_orders={"Source_Channel": branch_order},
            text_auto=True,
            height=500,
            color_discrete_sequence=px.colors.qualitative.Set2,
            labels={"Source_Channel": "Branch / Market", "Customers": "No. of Customers"},
        )
        fig_stacked.update_layout(
            xaxis_title="Branch / Market",
            yaxis_title="Number of Customers",
            legend_title="Bank",
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickangle=-35, automargin=True),
            margin=dict(t=30, b=100, l=60, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig_stacked.update_traces(
            textfont_size=11, textposition="inside", cliponaxis=False
        )
        st.plotly_chart(fig_stacked, use_container_width=True)
 
        # Grouped (side-by-side) view toggle
        with st.expander("📊 View as Grouped Bars"):
            fig_grouped = px.bar(
                bank_branch_count,
                x="Source_Channel",
                y="Customers",
                color="Bank",
                barmode="group",
                category_orders={"Source_Channel": branch_order},
                height=450,
                color_discrete_sequence=px.colors.qualitative.Set2,
                labels={"Source_Channel": "Branch / Market", "Customers": "No. of Customers"},
            )
            fig_grouped.update_layout(
                xaxis_title="Branch / Market",
                yaxis_title="Number of Customers",
                legend_title="Bank",
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickangle=-35, automargin=True),
                margin=dict(t=30, b=100, l=60, r=20),
            )
            st.plotly_chart(fig_grouped, use_container_width=True)
 
    # ── TAB 2: Heat map ────────────────────────────────────────────────────────
    with chart_tab2:
        st.markdown(
            "Rows = **Branches**, Columns = **Banks**. "
            "Darker green = more customers from that bank at that branch."
        )
 
        pivot = bank_branch_count.pivot_table(
            index="Source_Channel",
            columns="Bank",
            values="Customers",
            fill_value=0,
        )
        pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
 
        # Percentage annotations
        pivot_pct = pivot.div(pivot.sum(axis=1), axis=0).mul(100).round(1)
        annotation_text = pivot.astype(str) + "<br>(" + pivot_pct.astype(str) + "%)"
 
        fig_heat = go.Figure(
            go.Heatmap(
                z=pivot.values,
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                colorscale="Greens",
                text=annotation_text.values,
                texttemplate="%{text}",
                textfont={"size": 11},
                hoverongaps=False,
                showscale=True,
                colorbar=dict(title="Customers"),
            )
        )
        fig_heat.update_layout(
            xaxis_title="Bank",
            yaxis_title="Branch / Market",
            height=max(380, len(pivot) * 40 + 120),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=80, l=150, r=20),
            xaxis=dict(tickangle=-30, automargin=True),
        )
        st.plotly_chart(fig_heat, use_container_width=True)
 
        # Raw pivot table below heatmap
        with st.expander("📋 Full Bank × Branch breakdown table"):
            display_pivot = pivot.copy()
            display_pivot["Total"] = display_pivot.sum(axis=1)
            st.dataframe(
                display_pivot.style.background_gradient(
                    cmap="Greens", axis=None, subset=pivot.columns.tolist()
                ).format(precision=0),
                use_container_width=True,
            )
 
    # ── TAB 3: Donut / share ──────────────────────────────────────────────────
    with chart_tab3:
        col_pie1, col_pie2 = st.columns(2)
 
        with col_pie1:
            st.markdown("**Overall bank share across all branches**")
            bank_total = chart_df["Bank"].value_counts().reset_index()
            bank_total.columns = ["Bank", "Customers"]
            fig_donut = px.pie(
                bank_total,
                values="Customers",
                names="Bank",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_donut.update_traces(textposition="inside", textinfo="percent+label")
            fig_donut.update_layout(
                showlegend=True,
                legend=dict(orientation="v", x=1.0),
                margin=dict(t=20, b=20, l=20, r=20),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_donut, use_container_width=True)
 
        with col_pie2:
            st.markdown("**Select a branch to see its bank breakdown**")
            branch_list = sorted(chart_df["Source_Channel"].unique().tolist())
            selected_b = st.selectbox("Branch:", branch_list, key="pie_branch_select")
            branch_bank_data = (
                chart_df[chart_df["Source_Channel"] == selected_b]["Bank"]
                .value_counts()
                .reset_index()
            )
            branch_bank_data.columns = ["Bank", "Customers"]
            if not branch_bank_data.empty:
                fig_b_donut = px.pie(
                    branch_bank_data,
                    values="Customers",
                    names="Bank",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    title=f"{selected_b}",
                )
                fig_b_donut.update_traces(textposition="inside", textinfo="percent+label")
                fig_b_donut.update_layout(
                    margin=dict(t=40, b=20, l=20, r=20),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_b_donut, use_container_width=True)
 
    # ── Top-N Branch × Bank bar race ──────────────────────────────────────────
    st.markdown("#### 🏆 Top Branches by Bank Volume")
    all_banks_sorted = (
        bank_branch_count.groupby("Bank")["Customers"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )
    selected_bank_focus = st.selectbox(
        "Focus on a specific bank:", ["All Banks"] + all_banks_sorted, key="bank_focus"
    )
 
    if selected_bank_focus == "All Banks":
        top_df = (
            bank_branch_count.groupby("Source_Channel")["Customers"]
            .sum()
            .reset_index()
            .sort_values("Customers", ascending=True)
            .tail(15)
        )
        fig_top = px.bar(
            top_df,
            x="Customers",
            y="Source_Channel",
            orientation="h",
            height=max(350, len(top_df) * 35 + 80),
            color="Customers",
            color_continuous_scale="Greens",
            labels={"Source_Channel": "Branch / Market"},
            text="Customers",
        )
    else:
        top_df = (
            bank_branch_count[bank_branch_count["Bank"] == selected_bank_focus]
            .sort_values("Customers", ascending=True)
            .tail(15)
        )
        fig_top = px.bar(
            top_df,
            x="Customers",
            y="Source_Channel",
            orientation="h",
            height=max(350, len(top_df) * 35 + 80),
            color="Customers",
            color_continuous_scale="Blues",
            labels={"Source_Channel": "Branch / Market"},
            text="Customers",
            title=f"Top branches for {selected_bank_focus}",
        )
 
    fig_top.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=40, l=10, r=40),
        coloraxis_showscale=False,
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
    )
    fig_top.update_traces(textposition="outside", textfont_size=12)
    st.plotly_chart(fig_top, use_container_width=True)
 
 
# === Main App ===
def main():
    # Sidebar
    if st.sidebar.button("🧹 Clear Cache"):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.success("Cache cleared successfully!")
 
    with st.sidebar:
        st.header("🔧 Debug Info")
        st.write("Available secrets:", list(st.secrets.keys()))
 
    # Header
    st.markdown(
        """
    <div class="main-header">
        <h1>📊 Sales Performance Dashboard</h1>
        <p>CMCB Bank — Customer Portfolio & Market Visit Report</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
 
    tab = st.tabs(["📍 Market Visit Presentation"])[0]
 
    with tab:
        st.markdown(
            """
        <div class="function-card">
            <h2>👥 Customer Portfolio Presentation</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )
 
        telegram_df = get_telegram_data()
 
        if not telegram_df.empty:
            required_columns = [
                "Sender_Name",
                "Name",
                "Tel",
                "Bank",
                "Business",
                "Amount",
                "Interest",
                "Loan_Type",
                "Tenure",
                "Maturity",
                "Potential_Level",
                "Potential_Product",
                "Source_Channel",
                "Message_Date",
                "Remark",
            ]
            available_columns = [c for c in required_columns if c in telegram_df.columns]
            display_df = telegram_df[available_columns].copy()
 
            # ── Format data ────────────────────────────────────────────────────
            def format_sales_data(df):
                df_f = df.copy()
                if "Tel" in df_f.columns:
                    df_f["Tel"] = df_f["Tel"].astype(str).apply(
                        lambda x: f"0{x}" if x and not x.startswith("0") else x if x else ""
                    )
                if "Amount" in df_f.columns:
                    df_f["Amount"] = df_f["Amount"].apply(format_amount)
                if "Interest" in df_f.columns:
                    df_f["Interest"] = df_f["Interest"].apply(format_interest)
                for col in ["Name", "Business", "Bank", "Loan_Type", "Maturity", "Tenure"]:
                    if col in df_f.columns:
                        df_f[col] = df_f[col].astype(str).fillna("").replace("N/A", "")
                if "Message_Date" in df_f.columns:
                    df_f["Message_Date"] = pd.to_datetime(df_f["Message_Date"], errors="coerce")
                return df_f
 
            display_df = format_sales_data(display_df)
 
            # ── Filters ────────────────────────────────────────────────────────
            st.markdown("### 🔍 Filter Portfolio")
            col1, col2, col3 = st.columns(3)
 
            today_ts = pd.Timestamp.now().normalize()
            if "Message_Date" in display_df.columns:
                display_df["Message_Date"] = pd.to_datetime(
                    display_df["Message_Date"], errors="coerce"
                ).dt.normalize()
                today_df = display_df[display_df["Message_Date"] == today_ts]
                today_branches = sorted(
                    today_df["Source_Channel"].dropna().unique().tolist()
                )
            else:
                today_branches = sorted(
                    display_df["Source_Channel"].dropna().unique().tolist()
                )
 
            if "presentation_branches" not in st.session_state:
                st.session_state.presentation_branches = random.sample(
                    today_branches, min(12, len(today_branches))
                )
 
            all_branches = sorted(
                display_df["Source_Channel"].dropna().unique().tolist()
            )
 
            with col1:
                selected_potential = st.selectbox(
                    "Customer Potential:", ["All", "H", "M", "L"]
                )
            with col2:
                selected_branch = st.selectbox(
                    "📊 Presentation Branch (10 Branch Report)",
                    ["All"] + all_branches,
                )
            with col3:
                today = datetime.now(pytz.timezone("Asia/Phnom_Penh")).date()
                date_filter_type = st.radio(
                    "Date Filter:", ["Today", "Date Range"], horizontal=True
                )
                if date_filter_type == "Today":
                    start_date = end_date = today
                else:
                    min_date = display_df["Message_Date"].min().date()
                    max_date = display_df["Message_Date"].max().date()
                    start_date = st.date_input(
                        "From:", min_date, min_value=min_date, max_value=max_date
                    )
                    end_date = st.date_input(
                        "To:", max_date, min_value=min_date, max_value=max_date
                    )
 
            # ── Apply filters ──────────────────────────────────────────────────
            filtered_df = display_df.copy()
            if selected_potential != "All" and "Potential_Level" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["Potential_Level"].str.upper() == selected_potential
                ]
            if selected_branch != "All":
                filtered_df = filtered_df[
                    filtered_df["Source_Channel"] == selected_branch
                ]
            if "Message_Date" in filtered_df.columns:
                filtered_df = filtered_df[
                    (filtered_df["Message_Date"].dt.date >= start_date)
                    & (filtered_df["Message_Date"].dt.date <= end_date)
                ]
 
            # ── Quick stats ────────────────────────────────────────────────────
            total_customers = len(filtered_df)
            high_potential = (
                len(filtered_df[filtered_df["Potential_Level"].str.strip().str.upper() == "H"])
                if "Potential_Level" in filtered_df.columns
                else 0
            )
            medium_potential = (
                len(filtered_df[filtered_df["Potential_Level"].str.strip().str.upper() == "M"])
                if "Potential_Level" in filtered_df.columns
                else 0
            )
 
            st.markdown("### 📊 Customer Portfolio Overview")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Total Customers", total_customers)
            with c2:
                st.metric(
                    "High Potential",
                    high_potential,
                    delta=(
                        f"{(high_potential / total_customers * 100):.1f}%"
                        if total_customers
                        else "0%"
                    ),
                )
            with c3:
                st.metric("Medium Potential", medium_potential)
 
            # ── BANK DISTRIBUTION CHARTS ──────────────────────────────────────
            st.markdown("---")
            render_bank_branch_charts(filtered_df)
            st.markdown("---")
 
            # ── Customer table ─────────────────────────────────────────────────
            st.markdown(f"### 👥 Showing {len(filtered_df)} Customers")
 
            if len(filtered_df) > 0:
                visible_columns = [
                    "Name", "Tel", "Bank", "Business", "Amount", "Interest",
                    "Loan_Type", "Tenure", "Maturity", "Potential_Level",
                    "Potential_Product", "Remark",
                ]
                table_df = filtered_df[
                    [c for c in visible_columns if c in filtered_df.columns]
                ].copy()
 
                sort_order = {"H": 1, "M": 2, "L": 3}
                if "Potential_Level" in table_df.columns:
                    table_df["_pot_ord"] = table_df["Potential_Level"].map(sort_order).fillna(4)
                else:
                    table_df["_pot_ord"] = 4
 
                info_columns = ["Amount", "Bank", "Interest", "Loan_Type", "Tenure", "Maturity"]
                table_df["_info_score"] = table_df[
                    [c for c in info_columns if c in table_df.columns]
                ].apply(lambda row: sum(bool(str(x).strip()) for x in row), axis=1)
 
                table_df = table_df.sort_values(
                    by=["_pot_ord", "_info_score"], ascending=[True, False]
                ).drop(columns=["_pot_ord", "_info_score"])
 
                table_df = table_df.rename(
                    columns={
                        "Potential_Level": "Potential",
                        "Potential_Product": "Product",
                        "Loan_Type": "Loan Type",
                    }
                )
 
                styled_df = style_sales_dataframe(table_df)
                st.write(
                    styled_df.hide(axis="index").to_html(escape=False),
                    unsafe_allow_html=True,
                )
 
                # ── Actions ────────────────────────────────────────────────────
                st.markdown("### 🚀 Sales Actions")
                a1, a2, a3 = st.columns(3)
                with a1:
                    st.download_button(
                        label="📥 Download Filtered Data",
                        data=filtered_df.to_csv(index=False),
                        file_name="filtered_customer_portfolio.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with a2:
                    st.download_button(
                        label="📥 Download Full Portfolio",
                        data=table_df.to_csv(index=False),
                        file_name="full_customer_portfolio.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with a3:
                    if st.button("🔄 Refresh Data", use_container_width=True):
                        st.rerun()
 
                # ── Quick insights ─────────────────────────────────────────────
                st.markdown("### 💡 Quick Insights")
                if "Potential_Level" in filtered_df.columns:
                    i1, i2, i3 = st.columns(3)
                    with i1:
                        hp = len(
                            filtered_df[
                                filtered_df["Potential_Level"].str.strip().str.upper() == "H"
                            ]
                        )
                        st.info(f"**High Potential:** {hp} customers need immediate follow-up")
                    with i2:
                        if "Loan_Type" in filtered_df.columns:
                            popular_loan = filtered_df["Loan_Type"].mode()
                            if len(popular_loan) > 0:
                                st.info(f"**Popular Product:** {popular_loan[0]}")
                    with i3:
                        if "Bank" in filtered_df.columns:
                            top_bk = filtered_df["Bank"].mode()
                            if len(top_bk) > 0:
                                st.info(f"**Top Bank in Market:** {top_bk[0]}")
 
            else:
                st.warning(
                    "No customers match the selected filters. Try adjusting your criteria."
                )
 
        else:
            st.info(
                "💡 No customer data available. Please ensure data is pushed to Google Sheets first."
            )
            with st.expander("🆕 How to get started"):
                st.markdown(
                    """
                **For Sales Team Presentation:**
                1. Ensure customer data is pushed to Google Sheets via the 'Google Sheets Sync' tab
                2. Data should include: Customer Name, Phone, Business Type, Potential Level
                3. Contact admin if you need access to the Google Sheet
 
                **Required Columns for Optimal Presentation:**
                - Name, Tel, Bank, Business, Amount, Interest
                - Loan_Type, Tenure, Maturity
                - Potential_Level, Potential_Product
                - Source_Channel, Message_Date, Remark
                """
                )
 
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #6c757d; margin-top: 30px;'>"
        "Sales Performance Dashboard • CMCB Bank"
        "</div>",
        unsafe_allow_html=True,
    )
 
 
if __name__ == "__main__":
    main()
 
