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
import re
import random
import warnings
#import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from zoneinfo import ZoneInfo
kh_time = datetime.now(ZoneInfo("Asia/Phnom_Penh"))
import logging
import folium
from streamlit_folium import st_folium

# logging.getLogger('streamlit.runtime.scriptrunner').setLevel(logging.ERROR)

# import sqlite3
import sqlite3
from folium.plugins import HeatMap
import os
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timedelta
import hashlib
import time

# from oauth2client.service_account import ServiceAccountCredentials
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHEET_ID = "1wM7DTHizhg_A3h0qV3EhX4os4hk46uolW-ESQSJkgZs"
WORKSHEET_NAME = "merchant_data"

# === MUST BE THE FIRST STREAMLIT COMMAND ===
st.set_page_config(
    page_title="Merchant Delivery", layout="wide", page_icon="📊"
)

nest_asyncio.apply()

# Your credentials
api_id = 20056320
api_hash = "4b1394e0f07625a3c25ea32fa3030218"
# phone_number = os.environ["PHONE_NUMBER"]
# target = ["https://t.me/+JeQdy_3JC20wYTY1"]
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
# ==============================================================================
# PASSWORD CONFIGURATION
# ==============================================================================
import streamlit as st
import base64
import hashlib

# Load logo
with open("Logo-CMCB_FA-15.png", "rb") as f:
    logo_data = base64.b64encode(f.read()).decode()


@st.cache_resource
def connect_to_google_sheets():
    try:
        # Simple connection test
        if 'service_account' not in st.secrets:
            st.error("❌ Service account not found in secrets")
            return None
            
        # Create credentials from service account info
        credentials = Credentials.from_service_account_info(
            dict(st.secrets["service_account"]),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.file",
            ]
        )
        gc = gspread.authorize(credentials)
        return gc
        
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        return None

def clean_dataframe_for_streamlit(df):
    """Minimal cleaning - just fix Streamlit warnings"""
    if df is None or df.empty:
        return df

    df_clean = df.copy()

    # Convert all object columns to string (safest approach)
    for col in df_clean.columns:
        if df_clean[col].dtype == "object":
            df_clean[col] = df_clean[col].astype(str)
    
    # Handle dates (optional)
    if "Message_Date" in df_clean.columns:
        df_clean["Message_Date"] = pd.to_datetime(df_clean["Message_Date"], errors="coerce")
    
    return df_clean


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

@st.cache_data(ttl=120) 
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

# === Scrape Telegram data ===
def safe_format_interest(x):
    try:
        # If it's already a number, format it
        if pd.isna(x):
            return ""
        elif isinstance(x, (int, float)):
            return f"{x:.0f}%"
        else:
            # Try to convert string to number
            clean_x = str(x).replace("%", "").strip()
            return f"{float(clean_x):.0f}%"
    except (ValueError, TypeError):
        # Return original if conversion fails
        return str(x) if not pd.isna(x) else ""


def fix_dataframe_types(df):
    """
    Force convert all columns to proper Arrow-compatible types
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # First, convert ALL object columns to string with proper null handling
    for col in df.columns:
        if df[col].dtype == 'object':
            # Handle mixed types (int, float, str, None) properly
            df[col] = df[col].apply(
                lambda x: (
                    str(x).strip() 
                    if pd.notna(x) and x is not None 
                    else ""
                )
            )
    
    # Specific fixes for problematic columns
    problematic_cols = ["Maturity", "Tel", "Amount", "Interest", "Tenure"]
    
    for col in problematic_cols:
        if col in df.columns:
            # Force string conversion with cleanup
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .replace({
                    'nan': '', 'None': '', 'NaT': '', 
                    '<NA>': '', 'NoneType': '', 'float64': '',
                    'int64': '', 'NaN': '', 'null': ''
                })
                .replace(r'^\s*$', '', regex=True)  # Remove empty strings
            )
    
    return df

@st.cache_data(ttl=300, show_spinner=False)
def load_and_clean_data():
    """Load and clean data with caching"""
    try:
        gc = connect_to_google_sheets()
        if not gc:
            return pd.DataFrame()
        
        telegram_df = load_sheet_data(gc, SHEET_ID, WORKSHEET_NAME)
        
        if telegram_df is None or telegram_df.empty:
            return pd.DataFrame()
        
        # Convert all to string
        telegram_df = telegram_df.astype(str)
        
        # Clean values
        telegram_df = telegram_df.replace({
            'nan': '', 'None': '', 'NaN': '', 'null': '',
            'NaT': '', 'none': '', '<NA>': '', 'NoneType': ''
        })
        return telegram_df
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        return pd.DataFrame()

# Define Cambodia timezone once
CAMBODIA_TZ = pytz.timezone('Asia/Phnom_Penh')

def now_cambodia():
    """Get current datetime in Cambodia timezone"""
    return datetime.now(CAMBODIA_TZ)

def today_cambodia():
    """Get current date in Cambodia timezone"""
    return now_cambodia().date()
    

# === Streamlit App ===
def main():
    import os
    import streamlit as st

    # -------------------------
    # Header Section
    # -------------------------
    header_col1, header_col2, header_col3 = st.columns([1, 3, 1])

    with header_col1:
        try:
            logo_path = "Logo-CMCB_FA-15.png"
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
                <h1 style="color: #004A08; margin: 0; font-size: 2.2rem; font-weight: 700;">
                    Merchant Delivery Management
                </h1>
                <p style="color: #2E8B57; margin: 5px 0 0 0;
                          font-size: 1.1rem; font-weight: 500;">
                    Performance & Execution Management System
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with header_col3:
        st.empty()

    # -------------------------
    # Tabs Section
    # -------------------------
    tabs = st.tabs([
        "📍 Merchant Delivery",
    ])

    with tabs[0]:
        st.markdown(
            """
            <div class="function-card">
                <h2>👥 Customer Portfolio Presentation</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        with st.spinner("🔄 Loading customer data..."):
            try:
                #gc = connect_to_google_sheets()
                telegram_df = load_and_clean_data()
                #telegram_df = load_sheet_data(gc, SHEET_ID, WORKSHEET_NAME)
    
                if telegram_df is None or telegram_df.empty:
                    st.error("❌ No data found from Google Sheets")
                    st.stop()
                
                # 🚨 CRITICAL FIX: Convert ALL columns to string type FIRST
                telegram_df = telegram_df.astype(str)
                
                # 🚨 Clean up "nan" strings
                telegram_df = telegram_df.replace({
                    'nan': '', 'None': '', 'NaN': '', 'null': '', 
                    'NaT': '', 'none': '', '<NA>': '', 'NoneType': ''
                })

                telegram_df = telegram_df.copy()
                st.success(f"✅ Loaded {len(telegram_df)} customers")

            except Exception as e:
                st.error(f"❌ Error loading data: {str(e)}")
                st.stop() 
    
        # -------------------------
        # BASIC DATA CLEANING
        # -------------------------
        # Remove unwanted columns if they exist
        unwanted = ["Latitude", "Longitude", "Raw_Text", "Has_Image", "Has_Location"]
        for col in unwanted:
            if col in telegram_df.columns:
                telegram_df = telegram_df.drop(columns=[col])
    
        # Fill missing values
        telegram_df = telegram_df.fillna("")
    
        # -------------------------
        # DATE PROCESSING
        # -------------------------
        # Check if Message_Date exists and convert to datetime
        if "Message_Time" in telegram_df.columns:
            try:
                telegram_df["Message_Time"] = pd.to_datetime(telegram_df["Message_Time"], errors='coerce')
            except:
                telegram_df["Message_Time"] = pd.NaT
        else:
            telegram_df["Message_Time"] = pd.NaT
    
        # -------------------------
        # FILTER UI
        # -------------------------
        st.markdown("### 🔍 Filter Portfolio")
        # Simple two-column layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Date picker
            if "Message_Time" in telegram_df.columns:
                min_date = telegram_df["Message_Time"].min().date()
                max_date = telegram_df["Message_Time"].max().date()
                
                date_range = st.date_input(
                    "Select Date Range:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                
                if len(date_range) == 2:
                    start_date, end_date = date_range
                else:
                    start_date = end_date = date_range[0]
            else:
                start_date = end_date = None
                st.info("No date column available")
        
        with col2:
            # Merchant search
            if "Merchant_Name" in telegram_df.columns:
                merchant_search = st.text_input(
                    "Search Merchant:",
                    placeholder="Type merchant name..."
                )
            else:
                merchant_search = ""
                st.info("No merchant column available")
        
        # Apply filters
        filtered_df = telegram_df.copy()

        # Date filter
        if start_date and end_date and "Message_Time" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Message_Time"].notna()]
            filtered_df = filtered_df[
                (filtered_df["Message_Time"].dt.date >= start_date) &
                (filtered_df["Message_Time"].dt.date <= end_date)
            ]
        
        # Merchant search filter
        if merchant_search and "Merchant_Name" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["Merchant_Name"].str.contains(merchant_search, case=False, na=False)
            ]
        
        # Display results
        #st.markdown(f"### 📊 Found {len(filtered_df)} Records")
        #st.dataframe(filtered_df, use_container_width=True)
        
        # -------------------------
        # DISPLAY RESULTS
        # -------------------------
        st.markdown(f"### 👥 Showing {len(filtered_df)} Customers")
    
        if len(filtered_df) == 0:
            st.warning("No customers match the selected filters")
            st.stop()

        # Limit to reasonable number of columns
        #if len(display_columns) > 15:
        #    display_columns = display_columns[:15]
        
        display_df = filtered_df.copy()
    
        # Format Message_Date for display
        #if "Message_Time" in display_df.columns:
        #    display_df["Message_Time"] = display_df["Message_Time"].dt.strftime("%Y-%m-%d %H:%M:%S").replace("NaT", "")
    
        # -------------------------
        # SIMPLE HTML TABLE DISPLAY (No Arrow issues)
        # -------------------------
        def display_simple_table(df, max_rows=100, column_lengths=None):
            """Display DataFrame with customizable column lengths"""
            if df.empty:
                return "<p>No data to display</p>"
            
            display_data = df.head(max_rows).copy()
            
            # Default column lengths
            default_lengths = {
                "Merchant_Name": 20,	
                "Store_ID": 20,  # Fixed: Changed from Store_Acc to Store_ID
                "Message_Time": 20,
                "Channel": 20,
                "Sender_Name": 20
            }
            
            # Merge with user-provided lengths
            if column_lengths:
                default_lengths.update(column_lengths)
            
            html = """
            <div style="overflow-x: auto; border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-top: 20px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background-color: #2E8B57; color: white;">
            """
            
            # Headers
            for col in display_data.columns:
                max_len = default_lengths.get(col, 100)
                html += f'<th style="padding: 12px 8px; border: 1px solid #1e6b4e; text-align: left;">{col}</th>'
            html += "</tr></thead><tbody>"
            
            # Rows
            for idx, row in display_data.iterrows():
                # Alternate row colors for better readability
                bg_color = "#f9f9f9" if idx % 2 == 0 else "white"
                html += f'<tr style="background-color: {bg_color};">'
                for col in display_data.columns:
                    value = str(row[col]) if pd.notna(row[col]) else ""
                    
                    # Get max length for this column
                    max_len = default_lengths.get(col, 100)
                    
                    # Truncate if needed
                    if len(value) > max_len:
                        display_value = value[:max_len-3] + "..."
                        html += f'<td style="padding: 10px 8px; border: 1px solid #ddd;" title="{value}">{display_value}</td>'
                    else:
                        html += f'<td style="padding: 10px 8px; border: 1px solid #ddd;">{value}</td>'
                html += "</tr>"
            
            html += "</tbody></table></div>"
            
            if len(df) > max_rows:
                html += f'<p style="color: #666; margin-top: 10px;">Showing {max_rows} of {len(df)} rows</p>'
            
            return html
        
        # Display the table
        st.markdown(display_simple_table(display_df, max_rows=50), unsafe_allow_html=True)
    
        # -------------------------
        # DOWNLOAD BUTTONS
        # -------------------------
        st.markdown("### 📥 Download Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV Download
            csv_data = display_df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv_data,
                file_name="customer_portfolio.csv",
                mime="text/csv"
            )
        
        with col2:
            # Excel Download - No caching needed
            def convert_to_excel(df):
                """Convert DataFrame to Excel bytes"""
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Customers')
                return output.getvalue()
            
            excel_data = convert_to_excel(display_df)
            st.download_button(
                label="Download as Excel",
                data=excel_data,
                file_name="customer_portfolio.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
        # -------------------------
        # QUICK STATS
        # -------------------------
        st.markdown("### 📊 Quick Stats")
        
        #if len(filtered_df) > 0:
        #    cols = st.columns(4)
        #    
        #    with cols[0]:
        #        st.metric("Total Customers", len(filtered_df))
        #    
        #    with cols[1]:
        #        if "Potential_Level" in filtered_df.columns:
        #            high_pot = len(filtered_df[filtered_df["Potential_Level"].str.upper() == "H"])
        #            st.metric("High Potential", high_pot)
        #        else:
        #            st.metric("Data Loaded", "✓")
        #    
        #    with cols[2]:
        #        if "Amount" in filtered_df.columns:
        #            # Try to extract numeric amounts
        #            try:
        #                amounts = filtered_df["Amount"].str.replace('$', '').str.replace(',', '').str.replace('K', '000')
        #                numeric_amounts = pd.to_numeric(amounts, errors='coerce')
        #                total_amount = numeric_amounts.sum()
        #                if not pd.isna(total_amount):
        #                    st.metric("Total Amount", f"${total_amount:,.0f}")
        #            except:
        #                st.metric("Amount Field", "Available")
        #        else:
        #            st.metric("Columns", len(display_df.columns))
            
        #    with cols[3]:
        #        if "Source_Channel" in filtered_df.columns:
        #            unique_sources = filtered_df["Source_Channel"].nunique()
        #            st.metric("Sources", unique_sources)
        #        else:
        #            st.metric("Rows", len(filtered_df))
    
        # -------------------------
        # REFRESH BUTTON
        # -------------------------
        if st.button("🔄 Refresh Data", type="secondary"):
            st.cache_data.clear()
            st.experimental_rerun()


    
if __name__ == "__main__":
    main()
