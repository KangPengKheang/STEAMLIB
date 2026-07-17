import nest_asyncio
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import pandas as pd
import re
from datetime import datetime, timedelta
import streamlit as st
import plotly.express as px
import pytz
from rapidfuzz import fuzz, process
import time
import folium
from streamlit_folium import st_folium
from sklearn.cluster import DBSCAN
import numpy as np
import random
import sqlite3
from folium.plugins import HeatMap
import os
import base64
from google.oauth2.service_account import Credentials
import gspread

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
session_name = "customer_session_2"

# === Custom CSS ===
st.markdown(
    """
    <style>
        .main-header {
            background: linear-gradient(135deg, #14532D 0%, #16A34A 50%, #4ADE80 100%);
            padding: 25px;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 25px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.10);
        }

        .function-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
            margin-bottom: 25px;
            border-left: 6px solid #16A34A;
        }

        .stButton > button {
            background: linear-gradient(135deg, #166534 0%, #16A34A 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.18);
        }

        .block-container {
            padding-top: 1.2rem;
        }

        .kpi-shell {
            background: linear-gradient(135deg, #ecfdf3 0%, #f7fff9 55%, #ffffff 100%);
            border: 1px solid #bbf7d0;
            border-radius: 16px;
            padding: 16px 18px;
            margin: 14px 0 16px 0;
            box-shadow: 0 10px 24px rgba(22, 101, 52, 0.08);
        }

        .kpi-shell h4 {
            margin: 0;
            color: #14532d;
            font-size: 1.1rem;
            font-weight: 800;
        }

        .kpi-shell p {
            margin: 6px 0 0 0;
            color: #4b5563;
            font-size: 0.93rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_base64_encoded_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def format_amount(value):
    if pd.isna(value) or str(value).strip() == "":
        return ""
    val_str = str(value).strip()
    if val_str.lower().endswith("k"):
        return val_str
    try:
        num = float(val_str.replace("$", "").replace(",", ""))
        return f"${num:,.2f}"
    except Exception:
        return val_str


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


def shorten_branch_name(branch_name):
    """
    Examples:
    - Sales Photo Report NRM -> NRM
    - Sales Photo Report 271M -> 271M
    - Sales Photo Report 598M -> 598M
    """
    if pd.isna(branch_name):
        return "Unknown"

    name = str(branch_name).strip()

    if len(name) >= 4 and name[-4:] in ["271M", "598M"]:
        return name[-4:]

    if len(name) >= 3:
        return name[-3:]

    return name


def is_filled_value(value):
    if value is None:
        return False

    # Some Sheet cells can arrive as non-scalar values. Avoid using an array-like
    # result from pd.isna() directly in an if statement, which raises ValueError.
    try:
        missing = pd.isna(value)
        if isinstance(missing, (bool, np.bool_)) and missing:
            return False
        if isinstance(missing, (list, tuple, np.ndarray, pd.Series)) and np.all(
            missing
        ):
            return False
    except (TypeError, ValueError):
        pass

    value_str = str(value).strip()
    invalid_tokens = {
        "",
        "nan",
        "none",
        "null",
        "nat",
        "<na>",
        "n/a",
        "na",
        "n.a",
        "n\\a",
        "not available",
        "nil",
        "-",
        "--",
        "__",
    }
    return value_str.lower() not in invalid_tokens


def normalize_tel_for_count(value):
    """Normalize telephone values so formatting differences count together."""
    if not is_filled_value(value):
        return ""

    tel = str(value).strip().lower()
    digits = re.sub(r"\D", "", tel)
    return digits


def build_branch_sales_kpi(df):
    required_info_fields = [
        "Name",
        "Tel",
        "Bank",
        "Business",
        "Amount",
        "Interest",
        "Loan_Type",
        "Tenure",
        "Maturity",
    ]

    if df.empty or "Source_Channel" not in df.columns:
        return pd.DataFrame(
            columns=["Branch", "KPI_Score", "Fill_Rate", "Total_Customers"]
        )

    score_df = df.copy()

    for field in required_info_fields:
        if field not in score_df.columns:
            score_df[field] = ""

    score_df["Branch"] = (
        score_df["Source_Channel"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .replace("", "Unknown")
        .apply(shorten_branch_name)
    )

    filled_matrix = score_df[required_info_fields].apply(
        lambda col: col.map(is_filled_value)
    )
    score_df["Row_Quality_Score"] = (
        filled_matrix.sum(axis=1) / len(required_info_fields) * 100
    )

    branch_kpi = (
        score_df.groupby("Branch", as_index=False)
        .agg(
            Total_Customers=("Branch", "size"),
            Fill_Rate=("Row_Quality_Score", "mean"),
        )
        .sort_values(["Fill_Rate", "Total_Customers"], ascending=[False, False])
    )

    # Floor score so it never rounds up; less information always stays lower.
    branch_kpi["KPI_Score"] = (
        np.floor(branch_kpi["Fill_Rate"]).clip(lower=1, upper=100).astype(int)
    )
    branch_kpi["Fill_Rate"] = branch_kpi["Fill_Rate"].round(1)
    return branch_kpi


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
        st.session_state["google_sheets_error"] = str(e)
        st.error(f"❌ Failed to connect to Google Sheets: {str(e)}")
        try:
            st.info(
                "💡 Make sure your Google Sheet is shared with: "
                + st.secrets["service_account"]["client_email"]
            )
        except Exception:
            pass
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
            error_message = str(e)
            st.session_state["google_sheets_error"] = error_message
            if "Invalid JWT Signature" in error_message:
                st.error(
                    "❌ Google rejected the service-account signature. The configured "
                    "private key is no longer active for this service account."
                )
                st.info(
                    "💡 The spreadsheet and worksheet settings are unchanged. An active "
                    "private key for the same service account must be supplied by the "
                    "Google Cloud project administrator."
                )
            else:
                st.error(f"❌ Failed to open spreadsheet: {error_message}")
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
            st.session_state.pop("google_sheets_error", None)
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
        return load_sheet_data(gc, SHEET_ID, WORKSHEET_NAME)
    return pd.DataFrame()


@st.cache_data
def prepare_sales_df(raw_df):
    df = raw_df.copy()

    if "Name" in df.columns:
        df = df[df["Name"].notna() & (df["Name"].astype(str).str.strip() != "")]

    if "Sender_Name" in df.columns:
        df = df[
            (df["Sender_Name"].astype(str).str.strip() != "Zana MAM")
            & (df["Sender_Name"].astype(str).str.strip() != "Khemra BUTH")
        ]

    if "Tel" in df.columns:
        df["Tel"] = df["Tel"].astype(str).apply(
            lambda x: f"0{x}" if x and x != "nan" and not x.startswith("0") else x
        )

    if "Amount" in df.columns:
        df["Amount"] = df["Amount"].apply(format_amount)

    if "Interest" in df.columns:
        df["Interest"] = df["Interest"].apply(format_interest)

    if "Message_Date" in df.columns:
        df["Message_Date"] = pd.to_datetime(df["Message_Date"], errors="coerce")

    return df


def style_sales_dataframe(df):
    styler = df.style.hide(axis="index")

    def highlight_row(row):
        potential = str(row.get("Potential", "")).strip().upper()
        if potential == "H":
            return ["background-color: #FFFBEB"] * len(row)
        elif potential == "M":
            return ["background-color: #F6FBF8"] * len(row)
        return [""] * len(row)

    def color_potential(val):
        val = str(val).strip().upper()
        if val == "H":
            return "background-color: #FEF3C7; color: #92400E; font-weight: 800; text-align: center;"
        elif val == "M":
            return "background-color: #DBEAFE; color: #1E40AF; font-weight: 800; text-align: center;"
        elif val == "L":
            return "background-color: #DCFCE7; color: #166534; font-weight: 800; text-align: center;"
        return "background-color: #F3F4F6; color: #4B5563; font-weight: 700; text-align: center;"

    def color_status(val):
        status = str(val).strip().lower()
        if any(word in status for word in ["approved", "complete", "active", "success"]):
            return "background-color: #DCFCE7; color: #166534; font-weight: 700; text-align: center;"
        if any(word in status for word in ["pending", "follow", "progress", "waiting"]):
            return "background-color: #FEF3C7; color: #92400E; font-weight: 700; text-align: center;"
        if any(word in status for word in ["reject", "cancel", "decline", "inactive"]):
            return "background-color: #FEE2E2; color: #991B1B; font-weight: 700; text-align: center;"
        return "background-color: #F3F4F6; color: #4B5563; font-weight: 600; text-align: center;"

    styler = styler.apply(highlight_row, axis=1)

    if "Potential" in df.columns:
        styler = styler.map(color_potential, subset=["Potential"])

    if "Status" in df.columns:
        styler = styler.map(color_status, subset=["Status"])

    if "Tel" in df.columns:
        styler = styler.map(
            lambda _: "color: #0F3D5E; font-weight: 700; white-space: nowrap;",
            subset=["Tel"],
        )

    if "Amount" in df.columns:
        styler = styler.map(
            lambda _: "color: #166534; font-weight: 800; text-align: right; white-space: nowrap;",
            subset=["Amount"],
        )

    if "Bank" in df.columns:
        styler = styler.map(
            lambda _: "color: #1F2937; font-weight: 700;",
            subset=["Bank"],
        )

    styler = styler.set_properties(
        **{
            "text-align": "left",
            "white-space": "pre-wrap",
            "font-size": "14px",
            "color": "#273444",
            "border-bottom": "1px solid #E5E7EB",
            "padding": "11px 12px",
        }
    )

    styler = styler.set_table_styles(
        [
            {
                "selector": "table",
                "props": [
                    ("table-layout", "fixed"),
                    ("width", "100%"),
                    ("border-collapse", "separate"),
                    ("border-spacing", "0"),
                    ("font-family", "Inter, Segoe UI, Arial, sans-serif"),
                ],
            },
            {
                "selector": "th",
                "props": [
                    ("background-color", "#0B4F3C"),
                    ("color", "#FFFFFF"),
                    ("font-weight", "700"),
                    ("text-align", "left"),
                    ("font-size", "13px"),
                    ("letter-spacing", "0.35px"),
                    ("border-bottom", "3px solid #C6A15B"),
                    ("padding", "12px"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("border-right", "1px solid #EEF1F4"),
                    ("vertical-align", "middle"),
                    ("line-height", "1.35"),
                ],
            },
            {
                "selector": "tbody tr:hover td",
                "props": [("background-color", "#ECFDF5")],
            },
        ]
    )
    return styler


# =========================
# HEADER
# =========================
header_col1, header_col2, header_col3 = st.columns([1, 3, 1])

with header_col1:
    try:
        logo_path = os.path.join(BASE_DIR, "Logo-CMCB_FA-15.png")
        if os.path.exists(logo_path):
            logo_base64 = get_base64_encoded_image(logo_path)
            st.markdown(
                f"""
                <div style="background: white; padding: 10px; border-radius: 12px;
                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                            display: flex; align-items: center; justify-content: center;">
                    <img src="data:image/png;base64,{logo_base64}"
                         width="100" style="border-radius: 8px;">
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background: #f0f0f0; padding: 20px; border-radius: 12px;
                            text-align: center; color: #666;">
                    <p style="margin: 0;">🏦<br>Logo</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    except Exception:
        st.markdown(
            """
            <div style="background: #f0f0f0; padding: 20px; border-radius: 12px;
                        text-align: center; color: #666;">
                <p style="margin: 0;">🏦<br>Logo</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

with header_col2:
    st.markdown(
        """
        <div style="text-align: center; padding: 15px;">
            <h1 style="color: #14532D; margin: 0; font-size: 2.2rem; font-weight: 800;">
                Planning, Execution and Customer Data Management
            </h1>
            <p style="color: #16A34A; margin: 5px 0 0 0; font-size: 1.1rem; font-weight: 600;">
                Performance & Execution Management System
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with header_col3:
    st.markdown("")


def main():
    if st.sidebar.button("🧹 Clear Cache"):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.success("Cache cleared successfully!")

    with st.sidebar:
        st.header("🔧 Debug Info")
        try:
            st.write("Available secrets:", list(st.secrets.keys()))
        except Exception:
            st.write("Secrets not available")

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
                "Status",
                "Source_Channel",
                "Message_Date",
                "Remark",
            ]

            available_columns = [
                col for col in required_columns if col in telegram_df.columns
            ]
            display_df = telegram_df[available_columns].copy()
            display_df = prepare_sales_df(display_df)

            # Count each Tel across the complete dataset before applying any
            # branch, potential, or date filters.
            tel_counts_all_dates = pd.Series(dtype="int64")
            if "Tel" in display_df.columns:
                tel_count_keys = display_df["Tel"].map(normalize_tel_for_count)
                tel_counts_all_dates = tel_count_keys[tel_count_keys != ""].value_counts()

            st.markdown("### 📊 Customer Portfolio Overview")

            today = datetime.now(pytz.timezone("Asia/Phnom_Penh")).date()

            if (
                "Message_Date" in display_df.columns
                and not display_df["Message_Date"].dropna().empty
            ):
                min_date = display_df["Message_Date"].dropna().min().date()
                max_date = display_df["Message_Date"].dropna().max().date()
            else:
                min_date = today
                max_date = today

            # =========================
            # BIG PICTURE CHART FIRST
            # =========================
            overview_df = display_df.copy()

            default_overview_date = today if today <= max_date else max_date

            if "Message_Date" in overview_df.columns:
                overview_df = overview_df[
                    overview_df["Message_Date"].dt.date == default_overview_date
                ]

            if "Source_Channel" in overview_df.columns and not overview_df.empty:
                branch_summary_raw = overview_df.copy()
                branch_summary_raw["Branch"] = (
                    branch_summary_raw["Source_Channel"]
                    .fillna("Unknown")
                    .astype(str)
                    .str.strip()
                    .apply(shorten_branch_name)
                )

                branch_summary = (
                    branch_summary_raw.groupby("Branch", as_index=False)
                    .size()
                    .rename(columns={"size": "Total_Customers"})
                    .sort_values("Total_Customers", ascending=False)
                )

                fig_branch = px.bar(
                    branch_summary,
                    x="Branch",
                    y="Total_Customers",
                    text="Total_Customers",
                    color="Total_Customers",
                    color_continuous_scale=[
                        [0.0, "#DCFCE7"],
                        [0.25, "#86EFAC"],
                        [0.5, "#4ADE80"],
                        [0.75, "#22C55E"],
                        [1.0, "#166534"],
                    ],
                    title=f"Customer Count by Branch ({default_overview_date})",
                )

                fig_branch.update_traces(
                    textposition="outside",
                    marker_line_color="white",
                    marker_line_width=1.2,
                    opacity=0.95,
                    hovertemplate="<b>Branch:</b> %{x}<br><b>Total Customers:</b> %{y}<extra></extra>",
                )

                fig_branch.update_layout(
                    height=430,
                    showlegend=False,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    coloraxis_showscale=False,
                    title={
                        "text": f"Customer Count by Branch ({default_overview_date})",
                        "x": 0.5,
                        "xanchor": "center",
                        "font": {"size": 22, "color": "#14532D"},
                    },
                    xaxis_title="Branch",
                    yaxis_title="Number of Customers",
                    font={"size": 14, "color": "#1F2937"},
                    margin=dict(t=70, b=70, l=40, r=30),
                )

                fig_branch.update_xaxes(
                    tickangle=0,
                    showgrid=False,
                    categoryorder="total descending",
                )

                fig_branch.update_yaxes(
                    showgrid=True,
                    gridcolor="rgba(20, 83, 45, 0.08)",
                    zeroline=False,
                )

                st.plotly_chart(fig_branch, use_container_width=True)

                with st.expander("📋 Branch Summary Table"):
                    st.table(branch_summary)
            else:
                st.info("No branch summary available for overview chart.")

            branch_kpi = build_branch_sales_kpi(overview_df)
            st.markdown(
                """
                <div class="kpi-shell">
                    <h4>🏆 Sales Key Performance Indicator</h4>
                    <p>
                        Branch score is based on completeness of Name, Tel, Bank, Business,
                        Amount, Interest, Loan Type, Tenure, Maturity, and Potential.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if not branch_kpi.empty:
                kpi_chart_df = branch_kpi.sort_values(
                    ["KPI_Score", "Total_Customers"], ascending=[True, True]
                )
                fig_kpi = px.bar(
                    kpi_chart_df,
                    x="KPI_Score",
                    y="Branch",
                    orientation="h",
                    text="KPI_Score",
                    color="KPI_Score",
                    color_continuous_scale=[
                        [0.0, "#fca5a5"],
                        [0.45, "#facc15"],
                        [1.0, "#16a34a"],
                    ],
                    title="Branch Information Quality Score (Highest to Lowest)",
                )
                fig_kpi.update_traces(
                    texttemplate="%{text}/100",
                    textposition="outside",
                    marker_line_color="white",
                    marker_line_width=1,
                )
                fig_kpi.update_layout(
                    height=max(320, 34 * len(kpi_chart_df) + 130),
                    showlegend=False,
                    coloraxis_showscale=False,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=70, b=35, l=20, r=15),
                    xaxis_title="KPI Score (1 - 100)",
                    yaxis_title="Branch",
                )
                fig_kpi.update_xaxes(range=[0, 100], showgrid=True, gridcolor="rgba(22, 101, 52, 0.08)")
                fig_kpi.update_yaxes(showgrid=False)
                st.plotly_chart(fig_kpi, use_container_width=True)
                st.caption("Quick visual only: branches ranked by information quality score.")
            else:
                st.info("No branch KPI data available yet.")

            # =========================
            # FILTERS BELOW CHART
            # =========================
            st.markdown("### 🔍 Drill-Down Filters")

            if "Source_Channel" in display_df.columns:
                all_branches = sorted(
                    display_df["Source_Channel"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                    .tolist()
                )
            else:
                all_branches = []

            filter_col1, filter_col2, filter_col3 = st.columns(3)

            with filter_col1:
                selected_branch = st.selectbox(
                    "📍 Presentation Branch",
                    ["All"] + all_branches,
                    index=0,
                )

            with filter_col2:
                selected_potential = st.selectbox(
                    "👤 Customer Potential",
                    ["All", "H", "M", "L"],
                    index=0,
                )

            with filter_col3:
                date_filter_type = st.radio(
                    "📅 Date Filter",
                    ["All Dates", "Today", "Date Range"],
                    horizontal=True,
                )

                if date_filter_type == "All Dates":
                    start_date = min_date
                    end_date = max_date
                elif date_filter_type == "Today":
                    start_date = today
                    end_date = today
                else:
                    start_date = st.date_input(
                        "From:",
                        min_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="start_date_filter",
                    )
                    end_date = st.date_input(
                        "To:",
                        max_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="end_date_filter",
                    )

            # =========================
            # DETAIL FILTERED DATA
            # =========================
            filtered_df = display_df.copy()

            if selected_potential != "All" and "Potential_Level" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["Potential_Level"].astype(str).str.strip().str.upper()
                    == selected_potential
                ]

            if selected_branch != "All" and "Source_Channel" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["Source_Channel"].astype(str).str.strip()
                    == selected_branch
                ]

            if "Message_Date" in filtered_df.columns:
                filtered_df = filtered_df[
                    (filtered_df["Message_Date"].dt.date >= start_date)
                    & (filtered_df["Message_Date"].dt.date <= end_date)
                ]

            # =========================
            # KPI
            # =========================
            total_customers = len(filtered_df)
            high_potential = (
                len(
                    filtered_df[
                        filtered_df["Potential_Level"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        == "H"
                    ]
                )
                if "Potential_Level" in filtered_df.columns
                else 0
            )
            medium_potential = (
                len(
                    filtered_df[
                        filtered_df["Potential_Level"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        == "M"
                    ]
                )
                if "Potential_Level" in filtered_df.columns
                else 0
            )
            low_potential = (
                len(
                    filtered_df[
                        filtered_df["Potential_Level"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        == "L"
                    ]
                )
                if "Potential_Level" in filtered_df.columns
                else 0
            )

            st.markdown("### 📈 Filtered Summary")

            if "Tel" in filtered_df.columns:
                tel_values = filtered_df.loc[:, "Tel"]
                phone_number_count = sum(
                    1
                    for value in np.asarray(tel_values, dtype=object).reshape(-1)
                    if is_filled_value(value)
                )
            else:
                phone_number_count = 0

            m1, m2, m3, m4, m5 = st.columns(5)
            with m1:
                st.metric("Total Customers", total_customers)
            with m2:
                st.metric(
                    "High Potential",
                    high_potential,
                    delta=f"{(high_potential / total_customers * 100):.1f}%"
                    if total_customers
                    else "0%",
                )
            with m3:
                st.metric("Medium Potential", medium_potential)
            with m4:
                st.metric("Low Potential", low_potential)
            with m5:
                st.metric("📞 Phone Numbers", phone_number_count)

            st.markdown(f"### 👥 Showing {len(filtered_df)} Customers")

            if len(filtered_df) > 0:
                visible_columns = [
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
                    "Status",
                    "Remark",
                ]
                visible_columns = [
                    c for c in visible_columns if c in filtered_df.columns
                ]

                customer_display_df = filtered_df[visible_columns].copy()

                if "Tel" in customer_display_df.columns:
                    customer_display_df["Tel"] = customer_display_df["Tel"].map(
                        lambda tel: (
                            f"{tel} 🔢 {int(tel_counts_all_dates.get(normalize_tel_for_count(tel), 0))}"
                            if normalize_tel_for_count(tel)
                            else str(tel)
                        )
                    )

                if "Potential_Level" in customer_display_df.columns:
                    sort_order = {"H": 1, "M": 2, "L": 3}
                    customer_display_df["Potential_Level_Order"] = (
                        customer_display_df["Potential_Level"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        .map(sort_order)
                        .fillna(4)
                    )
                else:
                    customer_display_df["Potential_Level_Order"] = 4

                info_columns = [
                    c
                    for c in [
                        "Amount",
                        "Bank",
                        "Interest",
                        "Loan_Type",
                        "Tenure",
                        "Maturity",
                    ]
                    if c in customer_display_df.columns
                ]

                if info_columns:
                    customer_display_df["Info_Score"] = customer_display_df[
                        info_columns
                    ].apply(
                        lambda row: sum(
                            bool(str(x).strip()) and str(x).strip().lower() != "nan"
                            for x in row
                        ),
                        axis=1,
                    )
                else:
                    customer_display_df["Info_Score"] = 0

                customer_display_df = customer_display_df.sort_values(
                    by=["Potential_Level_Order", "Info_Score"],
                    ascending=[True, False],
                )

                customer_display_df = customer_display_df.drop(
                    columns=["Potential_Level_Order", "Info_Score"]
                )

                customer_display_df = customer_display_df.rename(
                    columns={
                        "Potential_Level": "Potential",
                        "Potential_Product": "Product",
                        "Loan_Type": "Loan Type",
                    }
                )

                maximum_table_rows = 150
                table_display_df = customer_display_df.head(maximum_table_rows).copy()
                st.caption(
                    f"Showing {len(table_display_df):,} of {len(customer_display_df):,} "
                    "matching customers (maximum 150 rows)."
                )

                styled_df = style_sales_dataframe(table_display_df)
                table_html = styled_df.to_html(escape=False)
                st.write(table_html, unsafe_allow_html=True)

                st.markdown("### 🚀 Sales Actions")

                c1, c2, c3 = st.columns(3)

                with c1:
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Filtered Data",
                        data=csv,
                        file_name="filtered_customer_portfolio.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                with c2:
                    csv_full = customer_display_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Full Portfolio",
                        data=csv_full,
                        file_name="full_customer_portfolio.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                with c3:
                    if st.button("🔄 Refresh Data", use_container_width=True):
                        st.rerun()

                st.markdown("### 💡 Quick Insights")

                q1, q2, q3 = st.columns(3)

                with q1:
                    st.info(
                        f"**High Potential:** {high_potential} customers need immediate follow-up"
                    )

                with q2:
                    if (
                        "Business" in filtered_df.columns
                        and not filtered_df["Business"].dropna().empty
                    ):
                        top_business = filtered_df["Business"].mode()
                        if len(top_business) > 0:
                            st.info(f"**Top Business:** {top_business.iloc[0]}")

                with q3:
                    if (
                        "Loan_Type" in filtered_df.columns
                        and not filtered_df["Loan_Type"].dropna().empty
                    ):
                        popular_loan = filtered_df["Loan_Type"].mode()
                        if len(popular_loan) > 0:
                            st.info(f"**Popular Product:** {popular_loan.iloc[0]}")

            else:
                st.warning(
                    "No customers match the selected filters. Try adjusting your criteria."
                )

        else:
            if "google_sheets_error" not in st.session_state:
                st.info(
                    "💡 No customer data available. Please ensure data is pushed to Google Sheets first."
                )

            with st.expander("🆕 How to get started"):
                st.markdown(
                    """
                    **For Sales Team Presentation:**
                    1. Ensure customer data is pushed to Google Sheets via the sync process
                    2. Data should include: Customer Name, Phone, Business Type, Potential Level
                    3. Contact admin if you need access to the Google Sheet

                    **Required Columns for Optimal Presentation:**
                    - Customer_Name
                    - Phone_Number
                    - Biz_Type
                    - Potential
                    - Amount
                    - Loan_Type
                    """
                )

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #6c757d; margin-top: 30px;'>"
        "Sales Performance Dashboard • CMCB Bank"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
