import nest_asyncio
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import pandas as pd
import re
from datetime import datetime
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

# import sqlite3
import sqlite3
from folium.plugins import HeatMap
import os
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timedelta


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

# === Custom CSS for beautiful styling ===
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


import base64
import os
def get_base64_encoded_image(image_path):
    """Get base64 encoded string of an image"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


# Create three columns for the header
header_col1, header_col2, header_col3 = st.columns([1, 3, 1])

with header_col1:
    try:
        # logo_path = "Logo-CMCB-15.png"
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
    except Exception as e:
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
            <h1 style="color: #004A08; margin: 0; font-size: 2.2rem; font-weight: 700;">
                Planning, Execution and Customer Data Management
            </h1>
            <p style="color: #2E8B57; margin: 5px 0 0 0; font-size: 1.1rem; font-weight: 500;">
                Performance & Execution Management System
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with header_col3:
    st.markdown("")

# === Extract info from text ===



@st.cache_resource
def connect_to_google_sheets():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ]

        # Check if secrets exist first
        if 'service_account' not in st.secrets:
            st.error("❌ Google Sheets credentials not found in secrets")
            st.info("Please add your service account credentials to Streamlit secrets")
            return None

        # Convert to dict (in case it's not already)
        creds_dict = dict(st.secrets["service_account"])
        
        # Validate required fields
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        for field in required_fields:
            if field not in creds_dict:
                st.error(f"❌ Missing required field in secrets: {field}")
                return None
        # Use Credentials from secrets
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=scope,
        )

        gc = gspread.authorize(credentials)
        try:
            # List available spreadsheets to test connection
            # Note: This might not work depending on permissions
            #st.success("✅ Successfully connected to Google Sheets API")
            return gc
        except Exception as test_error:
            st.error(f"❌ Connection test failed: {test_error}")
            return None

    except Exception as e:
        st.error(f"❌ Failed to connect to Google Sheets: {str(e)}")
        st.info("💡 Make sure your Google Sheet is shared with: " + 
               st.secrets["service_account"]["client_email"])
        return None

def load_sheet_data(_gc, sheet_id, worksheet_name):
    """
    Load data from Google Sheets with comprehensive error handling
    """
    try:
        # Validate inputs
        if _gc is None:
            st.error("❌ Google Sheets client is not initialized")
            return pd.DataFrame()

        if not sheet_id:
            st.error("❌ Sheet ID is required")
            return pd.DataFrame()

        if not worksheet_name:
            st.error("❌ Worksheet name is required")
            return pd.DataFrame()

        # Open the spreadsheet
        try:
            spreadsheet = _gc.open_by_key(sheet_id)
        except gspread.SpreadsheetNotFound:
            st.error(f"❌ Spreadsheet not found with ID: {sheet_id}")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Failed to open spreadsheet: {str(e)}")
            return pd.DataFrame()

        # Get the worksheet
        try:
            sheet = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            st.error(f"❌ Worksheet '{worksheet_name}' not found in the spreadsheet")
            return pd.DataFrame()

        # Get all records
        try:
            data = sheet.get_all_records()

            if not data:
                st.info(f"📭 No data found in worksheet '{worksheet_name}'")
                return pd.DataFrame()

            df = pd.DataFrame(data)
            # st.success(f"✅ Successfully loaded {len(df)} records from {worksheet_name}")
            return df

        except Exception as e:
            st.error(f"❌ Failed to read data from worksheet: {str(e)}")
            return pd.DataFrame()

    except Exception as e:
        st.error(f"❌ Unexpected error loading from Google Sheets: {str(e)}")
        return pd.DataFrame()

import re
@st.cache_data
def get_telegram_data():
    gc = connect_to_google_sheets()
    if gc:
        df = load_sheet_data(gc, SHEET_ID, WORKSHEET_NAME)
        return df
    return pd.DataFrame()

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
        df["Tel"] = df["Tel"].astype(str).apply(lambda x: f"0{x}" if x and not x.startswith("0") else x)

    if "Amount" in df.columns:
        df["Amount"] = df["Amount"].apply(format_amount)

    if "Interest" in df.columns:
        df["Interest"] = df["Interest"].apply(format_interest)

    if "Message_Date" in df.columns:
        df["Message_Date"] = pd.to_datetime(df["Message_Date"], errors="coerce")

    return df

# === Streamlit App ===
def main():
    if st.sidebar.button("🧹 Clear Cache"):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.success("Cache cleared successfully!")
        
    with st.sidebar:
        st.header("🔧 Debug Info")
        st.write("Available secrets:", list(st.secrets.keys()))
        

    # Three main functions
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
            # Select only the required columns for sales presentation
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
                "Remark"
            ]
           
            # Filter to only include available columns
            available_columns = [
                col for col in required_columns if col in telegram_df.columns
            ]
            display_df = telegram_df[available_columns].copy()

            def format_amount(value):
                if pd.isna(value) or str(value).strip() == "":
                    return ""
                val_str = str(value).strip()
                # Keep "K" values as is (10K, 20k, etc.)
                if val_str.lower().endswith("k"):
                    return val_str
                # Try convert to float
                try:
                    num = float(val_str.replace("$", "").replace(",", ""))
                    return f"${num:,.2f}"
                except:
                    return ""

            def format_interest(value):
                """Enhanced Interest Rate formatter with detailed error handling"""
                if pd.isna(value) or str(value).strip() in ["", "nan", "None", "null"]:
                    return ""
                val_str = str(value).strip()
                # print(f"🔍 Formatting interest: '{value}' → '{val_str}'")  # Debug line
                # Remove percentage symbol for processing
                clean_val = val_str.replace("%", "").strip()

                # Try multiple conversion strategies
                conversion_attempts = [
                    # Strategy 1: Direct conversion
                    lambda x: float(x),
                    # Strategy 2: Remove commas and spaces
                    lambda x: float(x.replace(",", "").replace(" ", "")),
                    # Strategy 3: Extract first number found
                    lambda x: (
                        float(re.search(r"[-+]?\d*\.?\d+", x).group())
                        if re.search(r"[-+]?\d*\.?\d+", x)
                        else None
                    ),
                ]

                for i, convert_func in enumerate(conversion_attempts):
                    try:
                        num = convert_func(clean_val)
                        if num is not None:
                            formatted = f"{num:.1f}%"
                            # print(f"✅ Success with strategy {i+1}: '{val_str}' → {formatted}")
                            return formatted
                    except (ValueError, AttributeError) as e:
                        continue

            # Clean and format the data for presentation
            def format_sales_data(df):
                df_f = df.copy()
                if "Tel" in df_f.columns:
                    df_f["Tel"] = df_f["Tel"].astype(str)
                    df_f["Tel"] = df_f["Tel"].apply(
                        lambda x: (
                            f"0{x}"
                            if x and not x.startswith("0")
                            else x if x else ""
                        )
                    )
                if "Amount" in df_f.columns:
                    df_f["Amount"] = df_f["Amount"].apply(format_amount)
                if "Interest" in df_f.columns:
                    df_f["Interest"] = df_f["Interest"].apply(format_interest)
                for col in ["Name", "Business", "Bank", "Loan_Type", "Maturity", "Tenure"]:
                    if col in df_f.columns:
                        df_f[col] = df_f[col].astype(str).fillna("").replace("N/A", "")
                if "Message_Date" in df_f.columns:
                    df_f["Message_Date"] = pd.to_datetime(
                        df_f["Message_Date"], errors="coerce"
                    )
                return df_f

            display_df = format_sales_data(display_df)

            def style_sales_dataframe(df):
                """Professional styling for sales presentations"""
                styler = df.style.hide(axis="index")

                # Highlight high potential customers (row-wise background)
                if "Potential" in df.columns:
                    styler = styler.apply(
                        lambda row: [
                            (
                                "background-color: #fff3cd"  # Light yellow for high potential
                                if str(row.get("Potential", "")).strip().upper()
                                == "H"
                                else (
                                    "background-color: #e8f5e8"  # Light green for medium
                                    if str(row.get("Potential", ""))
                                    .strip()
                                    .upper()
                                    == "M"
                                    else "background-color: #f8f9fa"
                                )
                            )  # Light gray for low
                            for _ in row
                        ],
                        axis=1,
                    )

                # Color code based on potential (text color)
                def color_potential(val):
                    if str(val).strip().upper() == "H":
                        return (
                            "color: #d32f2f; font-weight: bold; font-size: 14px;"  # Red
                        )
                    elif str(val).strip().upper() == "M":
                        return "color: #f57c00; font-weight: bold; font-size: 14px;"  # Orange
                    elif str(val).strip().upper() == "L":
                        return "color: #388e3c; font-weight: bold; font-size: 14px;"  # Green
                    return "color: #6c757d; font-size: 14px;"

                if "Potential" in df.columns:
                    styler = styler.map(color_potential, subset=["Potential"])

                # Highlight Amount column
                if "Amount" in df.columns:

                    def highlight_amount(val):
                        return "color: #1e88e5; font-weight: bold; font-size: 14px;"

                    styler = styler.map(highlight_amount, subset=["Amount"])

                # General table properties
                styler = styler.set_properties(
                    **{
                        "text-align": "left",
                        "white-space": "pre-wrap",
                        "font-size": "18px",
                        "border": "1px solid #dee2e6",
                        "padding": "10px 14px",
                    }
                )

                # Force fixed column widths (prevent resizing)
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
                        # Optional: set column width proportions
                        {
                            "selector": "th:nth-child(1), td:nth-child(1)",  # Name
                            "props": [("width", "10%")],
                        },
                        {
                            "selector": "th:nth-child(2), td:nth-child(2)",  # Tel
                            "props": [("width", "10%")],
                        },
                        {
                            "selector": "th:nth-child(3), td:nth-child(3)",  # Bank
                            "props": [("width", "5%")],
                        },
                        {
                            "selector": "th:nth-child(4), td:nth-child(4)",  # Business
                            "props": [("width", "10%")],
                        },
                        {
                            "selector": "th:nth-child(5), td:nth-child(5)",  # Amount
                            "props": [("width", "5%")],
                        },
                        {
                            "selector": "th:nth-child(6), td:nth-child(6)",  # Interest
                            "props": [("width", "5%")],
                        },
                        {
                            "selector": "th:nth-child(7), td:nth-child(7)",  # Loan Type
                            "props": [("width", "5%")],
                        },
                        {
                            "selector": "th:nth-child(8), td:nth-child(8)",  # Tenure
                            "props": [("width", "5%")],
                        },
                        {
                            "selector": "th:nth-child(9), td:nth-child(9)",  # Maturity
                            "props": [("width", "5%")],
                        },
                        {
                            "selector": "th:nth-child(10), td:nth-child(10)",  # Potential
                            "props": [("width", "5%")],
                        },
                        {
                            "selector": "th:nth-child(11), td:nth-child(11)",  # Product
                            "props": [("width", "10%")],
                        },
                        {
                            "selector": "th:nth-child(12), td:nth-child(12)",  # Remark
                            "props": [("width", "15%")],
                        },
                    ]
                )
                return styler
            # Sales Presentation Header
            st.markdown("### 📊 Customer Portfolio Overview")
            # Sales Filters
            st.markdown("### 🔍 Filter Portfolio")
            col1, col2, col3 = st.columns(3)
            
            #all_branches = sorted(
            #    display_df["Source_Channel"].dropna().unique().tolist()
            #)
            # Get today's date for filtering
            today = pd.Timestamp.now().normalize()
            
            # Filter today's data only and get unique Source_Channel
            if "Message_Date" in display_df.columns:
                display_df["Message_Date"] = pd.to_datetime(display_df["Message_Date"], errors="coerce").dt.normalize()
                today_df = display_df[display_df["Message_Date"] == today]
                today_branches = sorted(today_df["Source_Channel"].dropna().unique().tolist())
            else:
                today_branches = sorted(display_df["Source_Channel"].dropna().unique().tolist())
            

            # Randomly select 10 branches (if there are at least 10)
            if "presentation_branches" not in st.session_state:
                st.session_state.presentation_branches = random.sample(today_branches, min(12, len(today_branches)))
            
            presentation_branches = st.session_state.presentation_branches
            all_branches = sorted(display_df["Source_Channel"].dropna().unique().tolist())
            
            with col1:
                selected_potential = st.selectbox(
                    "Customer Potential:", ["All", "H", "M", "L"]
                )
            
            with col2:
                selected_branch = st.selectbox(
                    "📊 Presentation Branch (10 Branch Report)", 
                    ["All"] + all_branches
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
            # Apply filters
            filtered_df = display_df.copy()
            if selected_potential != "All":
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
            # Quick Stats for Sales Team
            total_customers = len(filtered_df)
            high_potential = (
                len(filtered_df[filtered_df["Potential_Level"].str.strip().str.upper() == "H"])
                if "Potential_Level" in display_df.columns
                else 0
            )
            medium_potential = (
                len(filtered_df[filtered_df["Potential_Level"].str.strip().str.upper() == "M"])
                if "Potential_Level" in display_df.columns
                else 0
            )
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Customers", total_customers)
            with col2:
                st.metric(
                    "High Potential",
                    high_potential,
                    delta=(
                        f"{(high_potential/total_customers*100):.1f}%"
                        if total_customers
                        else "0%"
                    ),
                )
            with col3:
                st.metric("Medium Potential", medium_potential)
            
            # Display filtered results
            st.markdown(f"### 👥 Showing {len(filtered_df)} Customers")

            if len(filtered_df) > 0:
                # 1️⃣ Keep only visible columns for display
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
                    "Remark"
                ]
                display_df = filtered_df[visible_columns].copy()
                # 2️⃣ Sort Potential_Level: H > M > L (or others)
                sort_order = {"H": 1, "M": 2, "L": 3}
                display_df["Potential_Level_Order"] = display_df["Potential_Level"].map(sort_order).fillna(4)
                # 2️⃣ Add "Info Completeness Score" — higher = more complete
                info_columns = ["Amount", "Bank", "Interest", "Loan_Type", "Tenure", "Maturity"]
                display_df["Info_Score"] = display_df[info_columns].apply(
                    lambda row: sum(
                        bool(str(x).strip()) for x in row  # counts only non-empty and non-null values
                    ),
                    axis=1
                )

                #info_columns = ["Amount", "Bank", "Interest", "Loan_Type", "Tenure", "Maturity"]
                #display_df["Info_Score"] = display_df[info_columns].notna().sum(axis=1)
                
                # 3️⃣ Sort by Potential_Level then Info_Score (descending = more info first)
                display_df = display_df.sort_values(
                    by=["Potential_Level_Order", "Info_Score"],
                    ascending=[True, False]  # H first, then most-complete info
                )
                #display_df = display_df.sort_values(by="Potential_Level_Order")
                display_df = display_df.drop(columns=["Potential_Level_Order", "Info_Score"])
                # 3️⃣ Rename columns for display
                display_df = display_df.rename(
                    columns={
                        "Potential_Level": "Potential",
                        "Potential_Product": "Product",
                        "Loan_Type": "Loan Type",
                    }
                )
                

                styled_df = style_sales_dataframe(display_df)
                st.write(
                        styled_df.hide(axis="index").to_html(escape=False),
                        unsafe_allow_html=True
                    )
                
                # Sales Team Actions
                st.markdown("### 🚀 Sales Actions")

                col1, col2, col3 = st.columns(3)

                with col1:
                    # Download filtered data
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Filtered Data",
                        data=csv,
                        file_name="filtered_customer_portfolio.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                with col2:
                    # Download full dataset
                    csv_full = display_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Full Portfolio",
                        data=csv_full,
                        file_name="full_customer_portfolio.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                with col3:
                    if st.button("🔄 Refresh Data", use_container_width=True):
                        st.rerun()

                # Quick Insights for Sales Team
                st.markdown("### 💡 Quick Insights")

                if "Potential" in filtered_df.columns:
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        hp_count = len(
                            filtered_df[
                                filtered_df["Potential"].str.strip().str.upper() == "H"
                            ]
                        )
                        st.info(
                            f"**High Potential:** {hp_count} customers need immediate follow-up"
                        )

                    with col2:
                        if "Biz_Type" in filtered_df.columns:
                            top_business = filtered_df["Biz_Type"].mode()
                            if len(top_business) > 0:
                                st.info(f"**Top Business:** {top_business[0]}")

                    with col3:
                        if "Loan_Type" in filtered_df.columns:
                            popular_loan = filtered_df["Loan_Type"].mode()
                            if len(popular_loan) > 0:
                                st.info(f"**Popular Product:** {popular_loan[0]}")

            else:
                st.warning(
                    "No customers match the selected filters. Try adjusting your criteria."
                )

        else:
            st.info(
                "💡 No customer data available. Please ensure data is pushed to Google Sheets first."
            )

            # Help section for sales team
            with st.expander("🆕 How to get started"):
                st.markdown(
                    """
                **For Sales Team Presentation:**
                1. Ensure customer data is pushed to Google Sheets via the 'Google Sheets Sync' tab
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
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #6c757d; margin-top: 30px;'>"
        "Sales Performance Dashboard • CMCB Bank • "
        #f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
