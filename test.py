import nest_asyncio
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import pandas as pd
import re
from datetime import datetime, timedelta, date
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

patterns = {
    "Name": r"Name:\s*([^\n]*)",
    "Tel": r"Tel:\s*([^\n]*)",
    "Business": r"Business:\s*([^\n]*)",
    "Bank": r"Bank:\s*([^\n]*)",
    "Amount": r"Amount:\s*([^\n]*)",
    "Interest": r"Interest:\s*([^\n]*)",
    "Loan Type": r"Loan\s*Type:\s*([^\n]*)",
    "Tenure": r"Tenure:\s*([^\n]*)",
    "Maturity": r"Maturity:\s*([^\n]*)",
    "Potential H/M/L": r"Potential\s*H/M/L:\s*([^\n]*)",
    "Potential Product": r"Potential\s*Product:\s*([^\n]*)",
}

import base64
import os


def get_base64_encoded_image(image_path):
    """Get base64 encoded string of an image"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


# ==============================================================================
# PASSWORD CONFIGURATION
# ==============================================================================
import streamlit as st
import base64
import hashlib


# FIXED: Proper password verification


# Load logo
with open("Logo-CMCB_FA-15.png", "rb") as f:
    logo_data = base64.b64encode(f.read()).decode()

# --- Initialize session state variables ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "customers" not in st.session_state:
    st.session_state.customers = pd.DataFrame()


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


@st.cache_data(ttl=300)
# Access control configuration
def load_users_from_sheets(_gc, sheet_id, worksheet_name="Users"):
    """Load users from Google Sheets with duplicate header handling"""
    try:
        sheet = _gc.open_by_key(sheet_id)
        worksheet = sheet.worksheet(worksheet_name)

        # 🚨 FIX: Get all values first to handle duplicates manually
        all_values = worksheet.get_all_values()

        if not all_values:
            print("⚠️ No data in sheet")
            return {}

        # Get headers (first row)
        raw_headers = all_values[0]

        # 🚨 FIX: Make headers unique by adding suffixes to duplicates
        headers = []
        header_count = {}

        for h in raw_headers:
            if h in header_count:
                header_count[h] += 1
                headers.append(f"{h}_{header_count[h]}")
            else:
                header_count[h] = 0
                headers.append(h)

        print(f"📋 Original headers: {raw_headers}")
        print(f"📋 Fixed headers: {headers}")

        # Create DataFrame with unique headers
        data = all_values[1:]  # Skip header row
        df = pd.DataFrame(data, columns=headers)

        # Now process the users
        users_dict = {}
        for _, user in df.iterrows():
            # Skip if password is empty
            if pd.isna(user.get('password', '')) or str(user.get('password', '')).strip() == '':
                continue

            password = str(user['password']).strip()

            # Handle allowed_sources
            allowed_raw = user.get('allowed_sources', 'all')
            if pd.isna(allowed_raw) or str(allowed_raw).strip() == '':
                sources = 'all'
            elif str(allowed_raw).strip().lower() == 'all':
                sources = 'all'
            else:
                sources = [s.strip() for s in str(allowed_raw).split(',') if s.strip()]

            users_dict[password] = {
                "username": str(user.get('username', 'Unknown')).strip(),
                "allowed_sources": sources,
                "branch": str(user.get('branch', '')).strip(),
                "role": str(user.get('role', 'rm')).strip(),
                "is_active": str(user.get('is_active', 'TRUE')).strip().upper() == 'TRUE'
            }

        print(f"✅ Loaded {len(users_dict)} users")
        return users_dict

    except Exception as e:
        st.error(f"❌ Error loading users: {e}")
        import traceback
        traceback.print_exc()
        return None  # Return None on error


def authenticate_simple_user(password):
    """Authenticate user with proper None handling"""
    try:
        # Connect to Google Sheets
        gc = connect_to_google_sheets()
        if gc is None:
            st.error("❌ Cannot connect to Google Sheets")
            return None

        # Load users - this now returns dictionary or None
        users_dict = load_users_from_sheets(gc, SHEET_ID, "Users")

        # 🚨 FIX: Check if users_dict is None or empty
        if users_dict is None:
            st.error("❌ Failed to load users - check Google Sheets connection")
            return None

        if not users_dict:
            st.error("❌ No users found in the sheet")
            return None

        # Clean input password
        input_password = str(password).strip()

        # Debug (remove in production)
        print(f"🔍 Attempting login for: {input_password[:3]}...")

        # Check direct match
        if input_password in users_dict:
            user_info = users_dict[input_password]

            # Check if active
            if not user_info.get("is_active", True):
                st.error("❌ Account is inactive")
                return None

            print(f"✅ Login successful for: {user_info['username']}")
            return user_info

        # Try case-insensitive match
        for pwd, info in users_dict.items():
            if str(pwd).strip().lower() == input_password.lower():
                if not info.get("is_active", True):
                    st.error("❌ Account is inactive")
                    return None

                print(f"✅ Login successful (case-insensitive) for: {info['username']}")
                return info

        # No match
        print("❌ No matching password found")
        st.error("❌ Invalid password or inactive account")
        return None

    except Exception as e:
        print(f"❌ Authentication error: {e}")
        import traceback
        traceback.print_exc()
        st.error("❌ Authentication system error")
        return None


def debug_users_sheet():
    """Debug function to check users sheet"""
    st.write("### 🔧 Users Sheet Debug")

    gc = connect_to_google_sheets()
    if gc is None:
        st.error("❌ Cannot connect")
        return

    try:
        sheet = gc.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet("Users")

        # Get all values
        all_values = worksheet.get_all_values()

        st.write(f"**Rows in sheet:** {len(all_values)}")

        if len(all_values) > 0:
            st.write("**Headers (raw):**")
            st.write(all_values[0])

            # Check for duplicates
            headers = all_values[0]
            duplicates = [h for h in headers if headers.count(h) > 1]
            if duplicates:
                st.error(f"❌ Duplicate headers found: {set(duplicates)}")
            else:
                st.success("✅ No duplicate headers")

            # Show first few rows
            if len(all_values) > 1:
                st.write("**First data row:**")
                st.write(all_values[1])

        # Test loading with our fixed function
        users = load_users_from_sheets(gc, SHEET_ID, "Users")

        if users:
            st.success(f"✅ Successfully loaded {len(users)} users")

            # Show usernames (without passwords)
            st.write("**Usernames loaded:**")
            for pwd, info in list(users.items())[:5]:
                st.write(f"- {info['username']} (active: {info['is_active']})")
        else:
            st.error("❌ Failed to load users")

    except Exception as e:
        st.error(f"❌ Debug error: {e}")


def login_form():

    st.markdown(
        """
    <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .login-card h2 {
            margin-top: 10px;
            color: #2E8B57;
        }
        .stTextInput>div>div>input {
            padding-left: 35px;
        }
        /* Center the login form */
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 80vh;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ---- Bank Logo ----
    st.markdown(
        """
        <div style='display: flex; justify-content: center; align-items: center; margin-bottom: 5px;'>
            <img src='data:image/png;base64,{}' width='120' alt='Bank Logo'>
        </div>
        """.format(
            logo_data
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <h3 style="color: #038C3E; margin-bottom: 5px; font-size: 18px;">CUSTOMER MANAGEMENT SYSTEM</h3>
        <p style="font-size: 13px; color: #666; margin-bottom: 20px; line-height: 1.4;">
            Enter your password to access the system
        </p>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        password = st.text_input(
            "🔑 Password",
            type="password",
            max_chars=50,
            placeholder="Enter your password",
            help="Enter your assigned password",
        )
        # Add debug checkbox (remove in production)
        #debug_mode = st.checkbox("🔧 Debug Mode", value=False)
        submitted = st.form_submit_button("Login →", use_container_width=True)
        if submitted:
            if not password:
                st.error("❌ Please enter a password")
            else:
                user_data = authenticate_simple_user(password)

                if user_data:
                    st.success(f"✅ Welcome, {user_data['username']}!")
                    st.session_state.logged_in = True
                    st.session_state.user_data = user_data
                    st.session_state.staff_id = password

                    # Load customer data with user-specific filtering

                    with st.spinner("Loading customer data..."):
                        try:
                            gc = connect_to_google_sheets()
                            full_data = load_sheet_data(gc, SHEET_ID, WORKSHEET_NAME)

                            # 🎯 DATA LOADING VERIFICATION - ADD THIS BLOCK
                            if full_data is not None and not full_data.empty:
                                st.info(
                                    f"📊 Raw data loaded: {len(full_data)} rows, {len(full_data.columns)} columns"
                                )

                                # Show column names for verification
                                with st.expander(
                                    "🔍 View Raw Data Structure", expanded=False
                                ):
                                    st.write("**Columns:**", list(full_data.columns))
                                    st.write("**First 2 rows:**")
                                    st.dataframe(full_data.head(2))
                                    st.write("**Data types:**")
                                    st.write(full_data.dtypes)

                                # Apply basic filters with safe column access
                                filtered_data = full_data.copy()
                                initial_count = len(filtered_data)
                                filter_steps = []

                                # Check and apply name filters if columns exist
                                if "Name" in filtered_data.columns:
                                    before_name = len(filtered_data)
                                    filtered_data = filtered_data[
                                        filtered_data["Name"].notna()
                                        & (filtered_data["Name"].str.strip() != "")
                                    ]
                                    after_name = len(filtered_data)
                                    filter_steps.append(
                                        f"Name filter: {before_name} → {after_name}"
                                    )

                                # Apply sender name exclusions if column exists
                                if "Sender_Name" in filtered_data.columns:
                                    before_sender = len(filtered_data)
                                    excluded_senders = ["Zana MAM", "Khemra BUTH"]
                                    filtered_data = filtered_data[
                                        ~filtered_data["Sender_Name"]
                                        .str.strip()
                                        .isin(excluded_senders)
                                    ]
                                    after_sender = len(filtered_data)
                                    filter_steps.append(
                                        f"Sender filter: {before_sender} → {after_sender}"
                                    )

                                # Apply user-specific source filtering
                                if user_data.get("allowed_sources") != "all":
                                    if "Source_Channel" in filtered_data.columns:
                                        before_source = len(filtered_data)
                                        allowed_sources = user_data["allowed_sources"]
                                        filtered_data = filtered_data[
                                            filtered_data["Source_Channel"].isin(
                                                allowed_sources
                                            )
                                        ]
                                        after_source = len(filtered_data)
                                        filter_steps.append(
                                            f"Source filter: {before_source} → {after_source}"
                                        )
                                        st.info(
                                            f"🔐 User allowed sources: {allowed_sources}"
                                        )

                                # Show filtering progress
                                with st.expander(
                                    "📈 Filtering Progress", expanded=False
                                ):
                                    for step in filter_steps:
                                        st.write(step)
                                    st.metric("Final Record Count", len(filtered_data))

                                # Store in session state
                                st.session_state.portfolio_data = filtered_data
                                st.session_state.customers = filtered_data

                                # Final success message with details
                                #st.success(
                                #    f"✅ Successfully loaded {len(filtered_data)} customers (from {initial_count} initial records)"
                                #)

                                # Show final data sample
                                with st.expander(
                                    "👀 Preview Final Data", expanded=False
                                ):
                                    st.dataframe(filtered_data.head(3))

                            else:
                                st.warning("⚠️ No customer data found")
                                st.session_state.portfolio_data = pd.DataFrame()
                                st.session_state.customers = pd.DataFrame()

                        except Exception as e:
                            st.error(f"❌ Error loading customer data: {str(e)}")
                            # Show detailed error for debugging
                            with st.expander("🐛 Error Details"):
                                st.exception(e)
                            st.session_state.portfolio_data = pd.DataFrame()

                    st.experimental_rerun()
                else:
                    st.error("❌ Invalid password or inactive account")


# Keep your old function for compatibility (but it won't be used)
def authenticate_user(staff_id):
    """Legacy function - kept for compatibility"""
    return False


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


# Helper function for map visualization
def create_customer_map(data):
    """Create an interactive map of customer locations"""
    if data.empty or "Latitude" not in data.columns or "Longitude" not in data.columns:
        st.warning("No location data available for mapping.")
        return None

    # Filter out rows with missing coordinates
    map_data = data.dropna(subset=["Latitude", "Longitude"])

    if map_data.empty:
        st.warning("No valid coordinates found for mapping.")
        return None

    # Create base map centered on average coordinates
    avg_lat = map_data["Latitude"].mean()
    avg_lon = map_data["Longitude"].mean()

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)

    # Define color coding based on potential
    POTENTIAL_COLORS = {
        "H": "red",  # High potential - Red
        "M": "orange",  # Medium potential - Orange
        "L": "green",  # Low potential - Green
        "": "gray",  # Unknown - Gray
    }

    # Add markers for each customer
    for _, row in map_data.iterrows():
        # Determine marker color based on potential
        potential = str(row.get("Potential", "")).strip().upper()
        color = POTENTIAL_COLORS.get(potential, "gray")

        # Create popup content
        popup_html = f"""
        <div style='width: 250px; font-size: 12px;'>
            <h4>{row.get('Customer Name', 'Unknown')}</h4>
            <b>Business:</b> {row.get('Biz Type', 'N/A')}<br>
            <b>Potential:</b> {potential}<br>
            <b>Income:</b> ${row.get('Monthly Income', 'N/A')}<br>
            <b>Product Interest:</b> {row.get('Product Interest', 'N/A')}<br>
            <b>Phone:</b> {row.get('Phone Number', 'N/A')}<br>
            <b>Visit Date:</b> {row.get('Message Date', 'N/A')}
        </div>
        """

        # Add marker to map
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row.get("Customer Name", "Unknown"),
            icon=folium.Icon(color=color, icon="user", prefix="fa"),
        ).add_to(m)

    return m


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


def advanced_clean_potential_level(potential_level):
    """Advanced cleaning with specific pattern matching"""
    if pd.isna(potential_level) or potential_level is None:
        return "L"

    loan_type_str = str(potential_level).strip().upper()

    # HIGH Potential patterns
    high_patterns = ["H", "H (", "HIGH"]  # H (KHQR), H (Give Certificate TD)

    # MEDIUM Potential patterns
    medium_patterns = [
        "M",
        "M (",  # M (Visit and take property customer)
        "M QR",
        "MEDIUM",
    ]

    # LOW Potential patterns (everything else)
    low_patterns = [
        "L",
        "LOW",
        "NO",
        "N/A",
        "TD",
        "LOAN",
        "BACK",
        "ISSUES",
        "EXISTING",
        "KHQR",
        "QR",
        "",
        " ",  # Empty values
        "L/",
        "L (",
        "L QR",  # L variations
    ]

    # Check for high potential
    for pattern in high_patterns:
        if pattern in loan_type_str:
            return "H"

    # Check for medium potential
    for pattern in medium_patterns:
        if pattern in loan_type_str:
            return "M"

    # Everything else is low potential
    return "L"


import time


def save_daily_plan_to_sheet(plan_data):
    try:
        #time.sleep(50)
        # Use the correct function name that you defined
        gc = connect_to_google_sheets()  # Changed from setup_gsheets()
        if not gc:
            st.error("❌ Failed to connect to Google Sheets")
            return False

        # Use the correct sheet ID
        sheet = gc.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet("plan")

        # Use staff_id instead of password for consistency
        staff_id = st.session_state.get('staff_id', '')
        master_plan_date = st.session_state.get("plan_date", datetime.now().date())

        print(f"🔍 DEBUG - Saving plan for staff: {staff_id}, date: {master_plan_date}")
        print(f"🔍 DEBUG - Number of tasks: {len(plan_data)}")

        rows = []
        for i, task in enumerate(plan_data):
            # If no customers, save task once
            if not task.get("customers") or len(task["customers"]) == 0:
                row = [
                    task["start_time"].strftime("%H:%M"),
                    task["end_time"].strftime("%H:%M"),
                    master_plan_date.strftime("%d/%m/%Y"),
                    task.get("activity", ""),
                    task.get("location", ""),
                    task.get("num_customers", ""),
                    "",  # customer name
                    "",  # customer contact
                    "",  # customer business
                    staff_id,
                    kh_time.strftime("%Y-%m-%d %H:%M:%S")
                ]
                rows.append(row)
                print(f"🔍 DEBUG - Added task {i+1} without customers")
            else:
                # Save one row per customer
                for j, customer in enumerate(task["customers"]):
                    row = [
                        task["start_time"].strftime("%H:%M"),
                        task["end_time"].strftime("%H:%M"),
                        master_plan_date.strftime("%d/%m/%Y"),
                        task.get("activity", ""),
                        task.get("location", ""),
                        task.get("num_customers", ""),
                        customer.get("name", "") or "",
                        customer.get("contact", "") or "",
                        customer.get("biz", "") or "",
                        staff_id,
                        kh_time.strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    rows.append(row)
                print(f"🔍 DEBUG - Added task {i+1} with {len(task['customers'])} customers")

        print(f"🔍 DEBUG - Total rows to save: {len(rows)}")

        # Save to Google Sheets
        if rows:
            worksheet.append_rows(rows)
            return True
        else:
            st.warning("⚠️ No data to save")
            return False

    except Exception as e:
        st.error(f"❌ Error saving daily plan: {e}")
        # Show detailed error for debugging
        with st.expander("🔍 Error Details"):
            st.exception(e)
        return False


def display_and_submit_plan():
    """
    Combined function that displays the plan summary AND submits it
    All in one action
    """
    try:
        # First, save the plan to Google Sheets
        if not save_daily_plan_to_sheet(st.session_state.tasks):
            st.error("❌ Failed to submit plan. Please try again.")
            return False

        # If save was successful, show the summary
        gc = connect_to_google_sheets()
        current_staff = st.session_state.get("staff_id", "")
        rm_name = (
            get_rm_name_from_staff_id(gc, current_staff) if current_staff else "Unknown"
        )
        plan_date = st.session_state.get("plan_date", datetime.now().date())

        # Beautiful summary display
        #st.subheader("✅ PLAN SUBMITTED SUCCESSFULLY")
        st.success(f"📅 Plan for {plan_date.strftime('%Y-%m-%d')} has been submitted!")

        if "tasks" not in st.session_state or not st.session_state.tasks:
            st.info("No plan data available.")
            return True

        # Create beautiful HTML table
        table_html = f"""
        <style>
            .plan-table {{
                width: 100% !important;
                min-width: 100% !important;
                border-collapse: collapse;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                margin-top: 10px;
                table-layout: fixed;
            }}
            .plan-table th {{
                background-color: #2E8B57;
                color: white;
                text-align: left;
                padding: 12px 8px;
                border: 1px solid #ccc;
                white-space: nowrap;
            }}
            .plan-table td {{
                padding: 10px 8px;
                border: 1px solid #ccc;
                vertical-align: top;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }}
            .plan-table tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            .plan-table tr:hover {{
                background-color: #f1f7f2;
            }}
            .plan-table caption {{
                caption-side: top;
                font-weight: bold;
                font-size: 16px;
                margin-bottom: 10px;
                color: #2E8B57;
                text-align: center;
            }}
            .plan-table th:nth-child(1), .plan-table td:nth-child(1) {{ width: 15%; }}
            .plan-table th:nth-child(2), .plan-table td:nth-child(2) {{ width: 20%; }}
            .plan-table th:nth-child(3), .plan-table td:nth-child(3) {{ width: 20%; }}
            .plan-table th:nth-child(4), .plan-table td:nth-child(4) {{ width: 15%; }}
            .plan-table th:nth-child(5), .plan-table td:nth-child(5) {{ width: 15%; }}
            .plan-table th:nth-child(6), .plan-table td:nth-child(6) {{ width: 15%; }}
        </style>
        <table class="plan-table">
            <caption>📋 Submitted Daily Sales Plan | 📅 Date: {plan_date.strftime('%Y-%m-%d')} | 👤 RM: {rm_name}</caption>
            <tr>
                <th>🕒 Time</th>
                <th>🏷️ Activity</th>
                <th>👤 Customers</th>
                <th>🏢 Business</th>
                <th>📞 Contact</th>
                <th>📍 Location</th>
            </tr>
        """

        for task in st.session_state.tasks:
            time_str = f"{task['start_time'].strftime('%H:%M')} - {task['end_time'].strftime('%H:%M')}"
            activity = task.get("activity", "Not specified")
            location = task.get("location", "Not specified")

            customer_name = ""
            customer_biz = ""
            customer_contact = ""
            if task.get("customers"):
                for customer in task["customers"]:
                    if customer.get("name"):
                        customer_name += f"{customer['name']}<br>"
                    if customer.get("biz"):
                        customer_biz += f"{customer['biz']}<br>"
                    if customer.get("contact"):
                        customer_contact += f"{customer['contact']}<br>"

            table_html += f'<tr><td>{time_str}</td><td>{activity}</td><td>{customer_name or "-"}</td><td>{customer_biz or "-"}</td><td>{customer_contact or "-"}</td><td>{location}</td></tr>'

        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"❌ Error processing plan: {e}")
        return False


def get_rm_name_from_staff_id(_gc, staff_id):
    """Lookup RM name from Users sheet using staff_id"""
    try:
        print(f"🔍 DEBUG - Starting lookup for staff_id: '{staff_id}'")

        if not staff_id:
            print("❌ DEBUG - staff_id is empty or None")
            return "Unknown"

        # Load users data
        users_data = load_users_from_sheets(_gc, SHEET_ID, "Users")
        print(f"🔍 DEBUG - users_data type: {type(users_data)}")

        # Since load_users_from_sheets returns a dictionary
        if isinstance(users_data, dict):
            print(f"🔍 DEBUG - Dictionary keys sample: {list(users_data.keys())[:5]}")

            target_staff_id = str(staff_id).strip()
            print(f"🔍 DEBUG - Looking for key: '{target_staff_id}'")

            # Direct key lookup
            if target_staff_id in users_data:
                user_info = users_data[target_staff_id]
                print(f"✅ SUCCESS - Found user info: {user_info}")
                # Extract just the username from the dictionary
                username = user_info.get("username", "Unknown")
                print(f"✅ SUCCESS - Username: {username}")
                return username  # Return just the username string

            # Try case-insensitive lookup
            print(f"🔍 DEBUG - Trying case-insensitive lookup...")
            for key, value in users_data.items():
                clean_key = str(key).strip()
                if clean_key.lower() == target_staff_id.lower():
                    username = value.get("username", "Unknown")
                    print(f"✅ SUCCESS - Found (case-insensitive): {username}")
                    return username  # Return just the username string

            # Try partial matching (in case there are extra spaces in the sheet)
            print(f"🔍 DEBUG - Trying partial matching...")
            for key, value in users_data.items():
                clean_key = str(key).strip().replace(" ", "")
                clean_target = target_staff_id.replace(" ", "")
                if clean_key == clean_target:
                    username = value.get("username", "Unknown")
                    print(f"✅ SUCCESS - Found (whitespace-insensitive): {username}")
                    return username  # Return just the username string

            # Show all available keys for debugging
            print(f"❌ DEBUG - Staff ID '{target_staff_id}' not found in dictionary")
            print(f"🔍 DEBUG - All available keys: {list(users_data.keys())}")

        else:
            print(f"❌ DEBUG - Unexpected users_data type: {type(users_data)}")

    except Exception as e:
        print(f"❌ ERROR in get_rm_name_from_staff_id: {e}")
        import traceback
        print(f"❌ TRACEBACK: {traceback.format_exc()}")

    return "Unknown"


def debug_users_sheet_structure(_gc):
    """Debug function to check the actual structure of Users sheet"""
    try:
        print("🔍 DEBUG - Checking Users sheet structure...")

        # Directly read the sheet to see raw structure
        worksheet = _gc.open_by_key(SHEET_ID).worksheet("Users")
        raw_data = worksheet.get_all_values()

        print(f"🔍 DEBUG - Raw sheet data shape: {len(raw_data)} rows x {len(raw_data[0]) if raw_data else 0} columns")
        print(f"🔍 DEBUG - First 3 rows of raw data:")
        for i, row in enumerate(raw_data[:3]):
            print(f"Row {i}: {row}")

        if len(raw_data) > 1:
            headers = raw_data[0]
            print(f"🔍 DEBUG - Headers: {headers}")

        return raw_data
    except Exception as e:
        print(f"❌ ERROR reading raw sheet: {e}")
        return None


# Updated debug function
def debug_rm_lookup():
    """Debug function to check RM lookup"""
    gc = connect_to_google_sheets()
    current_staff = st.session_state.get("staff_id", "")

    st.write("🔍 DEBUG RM Lookup:")
    st.write(f"- Current staff_id from session: '{current_staff}'")
    st.write(f"- Type of staff_id: {type(current_staff)}")

    if current_staff:
        # First, debug the sheet structure
        raw_data = debug_users_sheet_structure(gc)

        # Then try the lookup
        rm_name = get_rm_name_from_staff_id(gc, current_staff)
        st.write(f"- RM Name found: '{rm_name}'")

        # Additional debug: show what load_users_from_sheets returns
        try:
            users_data = load_users_from_sheets(gc, SHEET_ID, "Users")
            st.write(f"- load_users_from_sheets returned type: {type(users_data)}")
            if hasattr(users_data, 'columns'):
                st.write(f"- DataFrame columns: {users_data.columns.tolist()}")
                st.write(f"- DataFrame shape: {users_data.shape}")
            elif isinstance(users_data, dict):
                st.write(f"- Dictionary keys sample: {list(users_data.keys())[:5]}")
        except Exception as e:
            st.write(f"- Error calling load_users_from_sheets: {e}")
    else:
        st.write("- No staff_id found in session state")

    return rm_name if current_staff else "Unknown"


def display_plan_summary():
    """Beautiful report-style Plan Summary table"""
    gc = connect_to_google_sheets()
    current_staff = st.session_state.get("staff_id", "")

    # Debug: Check what we're getting
    #st.write(f"🔍 DEBUG - Staff ID from session: '{current_staff}'")

    rm_name = get_rm_name_from_staff_id(gc, current_staff) if current_staff else "Unknown"

    # Debug output
    #st.write(f"🔍 DEBUG - RM Name found: '{rm_name}'")

    plan_date = st.session_state.get("plan_date", datetime.now().date())

    st.subheader("📊 PLAN SUMMARY SUMMARY")
    st.success(f"📅 Plan for {plan_date.strftime('%Y-%m-%d')} has been generated, please check plan date and click on Submit Your Plan")

    if "tasks" not in st.session_state or not st.session_state.tasks:
        st.info("No plan available.")
        return

    # Rest of your display_plan_summary function remains the same...
    # --- Styled HTML Table ---
    table_html = f"""
    <style>
        .plan-table {{
            width: 100% !important;
            min-width: 100% !important;
            border-collapse: collapse;
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-top: 10px;
            table-layout: fixed;
        }}
        .plan-table th {{
            background-color: #2E8B57;
            color: white;
            text-align: left;
            padding: 12px 8px;
            border: 1px solid #ccc;
            white-space: nowrap;
        }}
        .plan-table td {{
            padding: 10px 8px;
            border: 1px solid #ccc;
            vertical-align: top;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        .plan-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .plan-table tr:hover {{
            background-color: #f1f7f2;
        }}
        .plan-table caption {{
            caption-side: top;
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 10px;
            color: #2E8B57;
            text-align: center;
        }}
        .plan-table th:nth-child(1), .plan-table td:nth-child(1) {{ width: 15%; }}
        .plan-table th:nth-child(2), .plan-table td:nth-child(2) {{ width: 20%; }}
        .plan-table th:nth-child(3), .plan-table td:nth-child(3) {{ width: 20%; }}
        .plan-table th:nth-child(4), .plan-table td:nth-child(4) {{ width: 15%; }}
        .plan-table th:nth-child(5), .plan-table td:nth-child(5) {{ width: 15%; }}
        .plan-table th:nth-child(6), .plan-table td:nth-child(6) {{ width: 15%; }}
    </style>
    <table class="plan-table">
        <caption>📋 Daily Sales Plan Summary | 📅 Date: {plan_date.strftime('%Y-%m-%d')} | 👤 RM: {rm_name}</caption>
        <tr>
            <th>🕒 Time</th>
            <th>🏷️ Activity</th>
            <th>👤 Customers</th>
            <th>🏢 Business</th>
            <th>📞 Contact</th>
            <th>📍 Location</th>
        </tr>
    """

    for task in st.session_state.tasks:
        time_str = f"{task['start_time'].strftime('%H:%M')} - {task['end_time'].strftime('%H:%M')}"
        activity = task.get("activity", "Not specified")
        location = task.get("location", "Not specified")

        customer_name = ""
        customer_biz = ""
        customer_contact = ""
        if task.get("customers"):
            for customer in task["customers"]:
                if customer.get("name"):
                    customer_name += f"{customer['name']}<br>"
                if customer.get("biz"):
                    customer_biz += f"{customer['biz']}<br>"
                if customer.get("contact"):
                    customer_contact += f"{customer['contact']}<br>"

        table_html += f'<tr><td>{time_str}</td><td>{activity}</td><td>{customer_name or "-"}</td><td>{customer_biz or "-"}</td><td>{customer_contact or "-"}</td><td>{location}</td></tr>'

    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)


# You can also add a debug button in your main app:
#if st.sidebar.button("🔍 Debug RM Lookup"):
#    debug_rm_lookup()

def debug_sheet_structure(_gc, sheet_id):
    """Debug function to list all worksheets in the Google Sheet"""
    try:
        sheet = _gc.open_by_key(sheet_id)
        worksheets = sheet.worksheets()

        worksheet_info = []
        for ws in worksheets:
            worksheet_info.append({
                'title': ws.title,
                'row_count': ws.row_count,
                'col_count': ws.col_count,
                'id': ws.id
            })

        return worksheet_info
    except Exception as e:
        st.error(f"❌ Error accessing sheet: {e}")
        return None


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

        # Apply filters
        telegram_df = telegram_df[
            telegram_df["Name"].notna()
            & (telegram_df["Name"].str.strip() != "")
            & (telegram_df["Sender_Name"].str.strip() != "Zana MAM")
            & (telegram_df["Sender_Name"].str.strip() != "Khemra BUTH")
        ]

        return telegram_df

    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        return pd.DataFrame()


def show_branch_summary_chart(df):
    """Show vertical bar chart summarizing customer count by branch"""
    if df is None or df.empty:
        st.info("No data available for Branch summary.")
        return

    possible_branch_cols = [
        "Branch",
        "BRANCH",
        "branch",
        "Branch_Name",
        "BRANCH_NAME",
        "Actual_Branch",
        "ACTUAL_BRANCH",
        "Match",
        "MATCH",
        "Sender_Name",
    ]

    branch_col = None
    for col in possible_branch_cols:
        if col in df.columns:
            branch_col = col
            break

    if branch_col is None:
        st.warning("⚠️ No Branch column found for summarization.")
        return

    chart_df = df.copy()
    chart_df[branch_col] = chart_df[branch_col].astype(str).str.strip()
    chart_df = chart_df[chart_df[branch_col] != ""]

    if chart_df.empty:
        st.info("No valid branch data available for chart.")
        return

    branch_summary = (
        chart_df.groupby(branch_col, as_index=False)
        .size()
        .rename(columns={"size": "Total_Customers"})
        .sort_values("Total_Customers", ascending=False)
    )

    fig = px.bar(
        branch_summary,
        x=branch_col,
        y="Total_Customers",
        text="Total_Customers",
        title="Branch Summary",
    )

    fig.update_traces(
        textposition="outside",
        marker_line_width=0
    )

    fig.update_layout(
        xaxis_title="Branch",
        yaxis_title="Total Customers",
        height=500,
        showlegend=False,
        xaxis=dict(tickangle=-35),
        margin=dict(t=70, l=40, r=20, b=120),
    )

    st.plotly_chart(fig, use_container_width=True)


# Define Cambodia timezone once
CAMBODIA_TZ = pytz.timezone('Asia/Phnom_Penh')


def now_cambodia():
    """Get current datetime in Cambodia timezone"""
    return datetime.now(CAMBODIA_TZ)


def today_cambodia():
    """Get current date in Cambodia timezone"""
    return now_cambodia().date()


def init_session_state():
    if "plan_date" not in st.session_state:
        st.session_state['plan_date'] = today_cambodia()
        print(f"✅ FIX APPLIED: plan_date set to {st.session_state['plan_date']}")
    else:
        print(f"📅 plan_date already exists: {st.session_state['plan_date']}")

    if "tasks" not in st.session_state:
        st.session_state["tasks"] = [
            {
                "start_time": datetime.strptime("08:00", "%H:%M").time(),
                "end_time": datetime.strptime("12:00", "%H:%M").time(),
                "plan_date": st.session_state['plan_date'],
                "activity": "",
                "location": "",
                "num_customers": "",
                "customers": [],
            },
            {
                "start_time": datetime.strptime("12:00", "%H:%M").time(),
                "end_time": datetime.strptime("16:30", "%H:%M").time(),
                "plan_date": st.session_state['plan_date'],
                "activity": "",
                "location": "",
                "num_customers": "",
                "customers": [],
            },
            {
                "start_time": datetime.strptime("16:30", "%H:%M").time(),
                "end_time": datetime.strptime("17:00", "%H:%M").time(),
                "plan_date": st.session_state['plan_date'],
                "activity": "",
                "location": "",
                "num_customers": "",
                "customers": [],
            },
        ]

    if "needs_rerun" not in st.session_state:
        st.session_state.needs_rerun = False

    if "form_reset_needed" not in st.session_state:
        st.session_state.form_reset_needed = False


# === Streamlit App ===
def main():
    init_session_state()

    if not st.session_state.get("logged_in", False):
        login_form()
        st.stop()
    # Create three columns for the header
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
                    Customer Data Management and Analysis
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

    # Initialize session state

    # Three main functions
    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Daily Planning",
            "📍 Market Visit Customer",
            "🌍 Customer Analysis Dashboard",
            # "🧾 Daily Summary by Branch",
            # "💹 Performance Dashboard",
        ]
    )
    with tab1:
        st.markdown(
            """
        <style>
        /* Apply Segoe UI Semibold to all text in the app */
        html, body, [class*="css"]  {
            font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif !important;
            font-weight: 600 !important;
        }
        
        /* Style input fields specifically */
        .stTextInput input, .stTextInput label, .stTextInput div {
            font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif !important;
            font-weight: 600 !important;
        }
        
        /* Style date input */
        .stDateInput input, .stDateInput label {
            font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif !important;
            font-weight: 600 !important;
        }
        
        /* Style buttons */
        .stButton button, .stButton button span {
            font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif !important;
            font-weight: 600 !important;
        }
        
        /* Style form submit buttons */
        .stFormSubmitButton button, .stFormSubmitButton button span {
            font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif !important;
            font-weight: 600 !important;
        }
        
        /* Style expanders */
        .streamlit-expanderHeader {
            font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif !important;
            font-weight: 600 !important;
        }
        
        /* Style headers */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif !important;
            font-weight: 600 !important;
        }
        
        /* Style placeholders */
        ::placeholder {
            font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif !important;
            font-weight: 600 !important;
            opacity: 0.7;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
        <div class="function-card">
            <h2>📋 Daily Planning </h2>
            <p>Submit your daily plan</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Initialize form state
        if "form_data" not in st.session_state:
            st.session_state.form_data = {}

        with st.container():
            # Header section
            header_col1, header_col2, header_col3 = st.columns([30, 6, 1])
            with header_col1:
                st.subheader("📅 Daily Planning")
            with header_col2:
                master_plan_date = st.date_input(
                    "Plan Date",
                    value=st.session_state.plan_date,
                    key="master_plan_date",
                    label_visibility="collapsed"
                )
                # Only update if date changed
                if master_plan_date != st.session_state.plan_date:
                    st.session_state.plan_date = master_plan_date
                    for task in st.session_state.tasks:
                        task["plan_date"] = master_plan_date

            # At the very end of your code, after all widgets are created
            if st.session_state.get("needs_rerun", False):
                st.session_state.needs_rerun = False

            # Then modify your button to set the flag:
            with header_col3:
                if st.button("➕", help="Add New Task", use_container_width=False):
                    # Add task logic
                    if st.session_state.tasks:
                        first_row_plan_date = st.session_state.plan_date
                        last_end_time = st.session_state.tasks[-1]["end_time"]
                        new_start_time = last_end_time
                        last_end_datetime = datetime.combine(
                            first_row_plan_date,
                            last_end_time
                        )
                        new_end_datetime = last_end_datetime + timedelta(hours=1)
                        new_end_time = new_end_datetime.time()

                        if new_end_datetime.date() > first_row_plan_date:
                            new_end_time = datetime.strptime("23:59", "%H:%M").time()
                    else:
                        first_row_plan_date = st.session_state.plan_date
                        new_start_time = datetime.strptime("09:00", "%H:%M").time()
                        new_end_time = datetime.strptime("10:00", "%H:%M").time()

                    st.session_state.tasks.append({
                        "start_time": new_start_time,
                        "end_time": new_end_time,
                        "plan_date": first_row_plan_date,
                        "activity": "",
                        "location": "",
                        "num_customers": "",
                        "customers": []
                    })

                    # Set flag for rerun
                    st.session_state.needs_rerun = True

            # ========== REMOVED THE FORM WRAPPER ==========
            # Store current form data to detect changes
            current_form_data = {}

            for i, task in enumerate(st.session_state.tasks):
                time_col1, time_col2, time_col4, time_col6, time_col7 = st.columns([1, 1, 2, 2, 1])

                with time_col1:
                    start_input = st.text_input(
                        f"🕐 Start Time {i+1}",
                        value=task["start_time"].strftime("%H:%M"),
                        placeholder="8:00 or 08:00 or 8 AM",
                        help="Enter start time in any format",
                        key=f"start_{i}",
                    )
                    # Update session state immediately
                    if start_input:
                        try:
                            if "am" in start_input.lower() or "pm" in start_input.lower():
                                start_time = datetime.strptime(start_input, "%I:%M %p").time()
                            else:
                                if len(start_input.split(":")[0]) == 1:
                                    start_input = "0" + start_input
                                start_time = datetime.strptime(start_input, "%H:%M").time()
                            st.session_state.tasks[i]["start_time"] = start_time
                        except:
                            pass

                with time_col2:
                    end_input = st.text_input(
                        f"🕔 End Time {i+1}",
                        value=task["end_time"].strftime("%H:%M"),
                        placeholder="17:00 or 5:00 or 5 PM",
                        help="Enter end time in any format",
                        key=f"end_{i}",
                    )
                    # Update session state immediately
                    if end_input:
                        try:
                            if "am" in end_input.lower() or "pm" in end_input.lower():
                                end_time = datetime.strptime(end_input, "%I:%M %p").time()
                            else:
                                if len(end_input.split(":")[0]) == 1:
                                    end_input = "0" + end_input
                                end_time = datetime.strptime(end_input, "%H:%M").time()
                            st.session_state.tasks[i]["end_time"] = end_time
                        except:
                            pass

                with time_col4:
                    activity = st.text_input(
                        f"📝 Activity {i+1}",
                        value=task["activity"],
                        placeholder="Loan review, market visit, etc.",
                        key=f"activity_{i}",
                    )
                    # Update session state immediately
                    st.session_state.tasks[i]["activity"] = activity

                with time_col6:
                    location = st.text_input(
                        f"🎯 Location {i+1}",
                        value=task["location"],
                        placeholder="Customer Location",
                        key=f"location_{i}",
                    )
                    # Update session state immediately
                    st.session_state.tasks[i]["location"] = location

                with time_col7:
                    num_customers = st.text_input(
                        f"👥 Number Cus {i+1}",
                        value=task["num_customers"],
                        placeholder="0, 1, 2, etc.",
                        key=f"num_customers_{i}",
                    )
                    # Update session state immediately
                    st.session_state.tasks[i]["num_customers"] = num_customers

                # Customer details expander - NOW SHOWS IMMEDIATELY
                num_customers_val = st.session_state.tasks[i]["num_customers"]
                if num_customers_val and num_customers_val.isdigit() and int(num_customers_val) > 0:
                    with st.expander(
                        f"📋 Customer Details for Task {i+1} ({num_customers_val} customers)",
                        expanded=True,
                    ):
                        num_customers_int = int(num_customers_val)

                        # Initialize customers list for this task
                        if "customers" not in st.session_state.tasks[i]:
                            st.session_state.tasks[i]["customers"] = []

                        # Ensure we have enough customer slots
                        while len(st.session_state.tasks[i]["customers"]) < num_customers_int:
                            st.session_state.tasks[i]["customers"].append({"name": "", "contact": "", "biz": ""})

                        # Create columns for customer details
                        for customer_num in range(num_customers_int):
                            cust_col1, cust_col2, cust_col3 = st.columns(3)

                            with cust_col1:
                                customer_name = st.text_input(
                                    f"Customer Name {customer_num + 1}",
                                    value=st.session_state.tasks[i]["customers"][customer_num]["name"],
                                    placeholder="Enter customer name",
                                    key=f"cust_name_{i}_{customer_num}",
                                )
                                # Update session state immediately
                                st.session_state.tasks[i]["customers"][customer_num]["name"] = customer_name

                            with cust_col2:
                                customer_contact = st.text_input(
                                    f"Phone Number {customer_num + 1}",
                                    value=st.session_state.tasks[i]["customers"][customer_num]["contact"],
                                    placeholder="Phone or other contact",
                                    key=f"cust_contact_{i}_{customer_num}",
                                )
                                # Update session state immediately
                                st.session_state.tasks[i]["customers"][customer_num]["contact"] = customer_contact

                            with cust_col3:
                                customer_biz = st.text_input(
                                    f"Business {customer_num + 1}",
                                    value=st.session_state.tasks[i]["customers"][customer_num]["biz"],
                                    placeholder="Customer Business",
                                    key=f"cust_biz_{i}_{customer_num}",
                                )
                                # Update session state immediately
                                st.session_state.tasks[i]["customers"][customer_num]["biz"] = customer_biz

            # Submit button (now outside the form)
            st.markdown("---")
            col1, col2, col3 = st.columns([3, 2, 3])

            with col2:
                # Single button that does everything
                submit_button = st.button(
                    "🚀 Submit Daily Plan",
                    use_container_width=True,
                    type="primary",
                    help="Submit your plan and view the summary",
                )

            # Process when button is clicked
            if submit_button:
                # Validate tasks
                valid_plan = True
                error_messages = []

                for i, task in enumerate(st.session_state.tasks):
                    if task["num_customers"] and task["num_customers"].isdigit():
                        num_customers_int = int(task["num_customers"])
                        if num_customers_int > 0:
                            if (
                                "customers" not in task
                                or len(task.get("customers", []))
                                < num_customers_int
                            ):
                                error_messages.append(
                                    f"❌ Please fill in customer details for Task {i+1}"
                                )
                                valid_plan = False

                if error_messages:
                    # Show errors
                    for error in error_messages:
                        st.error(error)
                else:
                    # Show loading spinner while processing
                    with st.spinner("📤 Submitting your plan..."):
                        # Use the combined function
                        if display_and_submit_plan():
                            # Reset form after successful submission
                            st.session_state.tasks = [
                                {
                                    "start_time": datetime.strptime(
                                        "08:00", "%H:%M"
                                    ).time(),
                                    "end_time": datetime.strptime(
                                        "12:00", "%H:%M"
                                    ).time(),
                                    "plan_date": datetime.now().date(),
                                    "activity": "",
                                    "location": "",
                                    "num_customers": "",
                                    "customers": [],
                                },
                                {
                                    "start_time": datetime.strptime(
                                        "12:00", "%H:%M"
                                    ).time(),
                                    "end_time": datetime.strptime(
                                        "4:30", "%H:%M"
                                    ).time(),
                                    "plan_date": datetime.now().date(),
                                    "activity": "",
                                    "location": "",
                                    "num_customers": "",
                                    "customers": [],
                                },
                                {
                                    "start_time": datetime.strptime(
                                        "4:30", "%H:%M"
                                    ).time(),
                                    "end_time": datetime.strptime(
                                        "5:00", "%H:%M"
                                    ).time(),
                                    "plan_date": datetime.now().date(),
                                    "activity": "",
                                    "location": "",
                                    "num_customers": "",
                                    "customers": [],
                                },
                            ]

                            st.session_state.form_reset_needed = True
                            st.rerun()

            # Handle form reset
            if st.session_state.get("form_reset_needed", False):
                st.session_state.form_reset_needed = False
                st.rerun()

    # -------------------------
    # TAB 2: Customer Portfolio Presentation
    # -------------------------
    with tab2:
        st.markdown("""
            <div class="function-card">
                <h2>👥 Customer Portfolio Presentation</h2>
            </div>
        """, unsafe_allow_html=True)

        # Ensure login
        if not st.session_state.get("logged_in"):
            st.warning("🔒 Please log in to continue")
            st.stop()

        # -------------------------
        # LOAD GOOGLE SHEET DATA
        # -------------------------
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

                # 🚨 FIX 1: Fixed the filter logic (removed contradictory condition)
                telegram_df = telegram_df[
                    telegram_df["Name"].notna()
                    & (telegram_df["Name"].str.strip() != "")
                    & (telegram_df["Sender_Name"].str.strip() != "Zana MAM")
                    & (
                        telegram_df["Sender_Name"].str.strip() != "Khemra BUTH"
                    )
                ]

                # 🚨 FIX 2: Corrected the key name from "allow_sources" to "allowed_sources"
                user_data = st.session_state.get("user_data", {})
                #allowed_sources = user_data.get("allowed_sources", "all")
                if user_data.get("allowed_sources") != "all":  # Fixed typo
                    allowed_sources = user_data.get("allowed_sources", [])
                    if "Source_Channel" in telegram_df.columns and allowed_sources:
                        telegram_df = telegram_df[
                            telegram_df["Source_Channel"].isin(allowed_sources)
                        ]
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

        # Ensure Name column exists for filtering
        if "Name" not in telegram_df.columns:
            telegram_df["Name"] = ""

        # Filter out empty names
        telegram_df = telegram_df[telegram_df["Name"].str.strip() != ""]

        # -------------------------
        # DATE PROCESSING
        # -------------------------
        # Check if Message_Date exists and convert to datetime
        if "Message_Date" in telegram_df.columns:
            try:
                telegram_df["Message_Date"] = pd.to_datetime(telegram_df["Message_Date"], errors='coerce')
            except:
                telegram_df["Message_Date"] = pd.NaT
        else:
            telegram_df["Message_Date"] = pd.NaT

        # -------------------------
        # FILTER UI
        # -------------------------
        st.markdown("### 🔍 Filter Portfolio")

        col1, col2, col3 = st.columns(3)

        with col1:
            # Potential Level filter
            if "Potential_Level" in telegram_df.columns:
                potential_options = ["All"] + sorted(telegram_df["Potential_Level"].unique().tolist())
                selected_potential = st.selectbox("Potential Level", potential_options)
            else:
                selected_potential = "All"
                st.info("No Potential column")

        with col2:
            # Source Channel filter
            if "Source_Channel" in telegram_df.columns:
                source_options = ["All"] + sorted([x for x in telegram_df["Source_Channel"].unique() if x])
                selected_source = st.selectbox("Source Channel", source_options)
            else:
                selected_source = "All"
                st.info("No Source Channel")

        with col3:
            # Date Range Type
            filter_type = st.radio("Date Filter", ["All Dates", "Today", "Custom Range"], horizontal=True)

        # -------------------------
        # DATE RANGE SELECTOR
        # -------------------------
        if filter_type == "Today":
            # Set both dates to today
            start_date = end_date = datetime.now().date()
            st.info(f"📅 Showing data for today: {start_date}")

        elif filter_type == "Custom Range" and "Message_Date" in telegram_df.columns:
            # Get min and max dates from valid dates
            valid_dates = telegram_df[telegram_df["Message_Date"].notna()]["Message_Date"]
            if not valid_dates.empty:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()
            else:
                min_date = datetime.now().date()
                max_date = datetime.now().date()

            col4, col5 = st.columns(2)
            with col4:
                start_date = st.date_input("From Date", min_date, min_value=min_date, max_value=max_date)
            with col5:
                end_date = st.date_input("To Date", max_date, min_value=min_date, max_value=max_date)

            # Ensure start_date <= end_date
            if start_date > end_date:
                st.warning("⚠️ Start date cannot be after end date. Swapping dates.")
                start_date, end_date = end_date, start_date

        else:
            # All Dates option
            start_date = None
            end_date = None
            if filter_type == "All Dates":
                st.info("📅 Showing all dates")

        # -------------------------
        # APPLY FILTERS
        # -------------------------
        filtered_df = telegram_df.copy()

        # Potential Level filter
        if selected_potential != "All" and "Potential_Level" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Potential_Level"] == selected_potential]

        # Source Channel filter
        if selected_source != "All" and "Source_Channel" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Source_Channel"] == selected_source]

        # Date Range filter
        if "Message_Date" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Message_Date"].notna()]

            if filter_type == "Today":
                # Filter for today only
                today_date = datetime.now().date()
                filtered_df = filtered_df[filtered_df["Message_Date"].dt.date == today_date]

            elif filter_type == "Custom Range" and start_date and end_date:
                # Custom range filter (existing code)
                filtered_df = filtered_df[
                    (filtered_df["Message_Date"].dt.date >= start_date) &
                    (filtered_df["Message_Date"].dt.date <= end_date)
                ]

            elif filter_type == "Yesterday":
                # Filter for yesterday only
                yesterday_date = datetime.now().date() - timedelta(days=1)
                filtered_df = filtered_df[filtered_df["Message_Date"].dt.date == yesterday_date]

            elif filter_type == "Last 7 Days":
                # Filter for last 7 days
                seven_days_ago = datetime.now().date() - timedelta(days=7)
                filtered_df = filtered_df[
                    (filtered_df["Message_Date"].dt.date >= seven_days_ago) &
                    (filtered_df["Message_Date"].dt.date <= datetime.now().date())
                ]

            elif filter_type == "This Month":
                # Filter for current month
                today = datetime.now().date()
                first_day_of_month = date(today.year, today.month, 1)
                if today.month == 12:
                    last_day_of_month = date(today.year, 12, 31)
                else:
                    last_day_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)

                filtered_df = filtered_df[
                    (filtered_df["Message_Date"].dt.date >= first_day_of_month) &
                    (filtered_df["Message_Date"].dt.date <= last_day_of_month)
                ]

        # -------------------------
        # DISPLAY RESULTS
        # -------------------------
        st.markdown(f"### 👥 Showing {len(filtered_df)} Customers")

        if len(filtered_df) == 0:
            st.warning("No customers match the selected filters")
            st.stop()

        # Select columns to display
        display_columns = []
        preferred_columns = [
            "Sender_Name", "Name", "Tel", "Bank", "Business",
            "Purpose", "Amount", "Interest", "Loan_Type",
            "Tenure", "Maturity", "Potential_Level", "Potential_Product",
            "Remark", "Message_Date"
        ]

        for col in preferred_columns:
            if col in filtered_df.columns:
                display_columns.append(col)

        # Limit to reasonable number of columns
        if len(display_columns) > 15:
            display_columns = display_columns[:15]

        display_df = filtered_df[display_columns].copy()

        # Format Message_Date for display
        if "Message_Date" in display_df.columns:
            display_df["Message_Date"] = display_df["Message_Date"].dt.strftime("%Y-%m-%d %H:%M:%S").replace("NaT", "")

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
                "Remark": 50,
                "Purpose": 80,
                "Business": 60,
                "Name": 40,
                "Sender_Name": 40,
                "Tel": 15,
                "Amount": 20,
                "Interest": 10,
                "Loan_Type": 30,
                "Tenure": 10,
                "Maturity": 10,
                "Potential": 5,
                "Product": 30,
                "Message_Date": 20,
                "Source_Channel": 30,
                "Bank": 30,
            }

            # Merge with user-provided lengths
            if column_lengths:
                default_lengths.update(column_lengths)

            html = """
            <div style="overflow-x: auto; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background-color: #f2f2f2;">
            """

            # Headers
            for col in display_data.columns:
                max_len = default_lengths.get(col, 100)
                html += f'<th style="padding: 10px 8px; border: 1px solid #ddd; text-align: left; max-width: {max_len*6}px;" title="Max {max_len} chars">{col}</th>'
            html += "</tr></thead><tbody>"

            # Rows
            for _, row in display_data.iterrows():
                html += "<tr>"
                for col in display_data.columns:
                    value = str(row[col]) if str(row[col]) != "nan" else ""

                    # Get max length for this column
                    max_len = default_lengths.get(col, 100)

                    # Truncate if needed
                    if len(value) > max_len:
                        display_value = value[:max_len-3] + "..."
                        html += f'<td style="padding: 8px 6px; border: 1px solid #ddd; max-width: {max_len*6}px;" title="{value}">{display_value}</td>'
                    else:
                        html += f'<td style="padding: 8px 6px; border: 1px solid #ddd; max-width: {max_len*6}px;">{value}</td>'
                html += "</tr>"

            html += "</tbody></table></div>"

            if len(df) > max_rows:
                html += f'<p style="color: #666; margin-top: 10px;">Showing {max_rows} of {len(df)} rows</p>'

            return html

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

        if len(filtered_df) > 0:
            cols = st.columns(4)

            with cols[0]:
                st.metric("Total Customers", len(filtered_df))

            with cols[1]:
                if "Potential_Level" in filtered_df.columns:
                    high_pot = len(filtered_df[filtered_df["Potential_Level"].str.upper() == "H"])
                    st.metric("High Potential", high_pot)
                else:
                    st.metric("Data Loaded", "✓")

            with cols[2]:
                if "Amount" in filtered_df.columns:
                    # Try to extract numeric amounts
                    try:
                        amounts = filtered_df["Amount"].str.replace('$', '').str.replace(',', '').str.replace('K', '000')
                        numeric_amounts = pd.to_numeric(amounts, errors='coerce')
                        total_amount = numeric_amounts.sum()
                        if not pd.isna(total_amount):
                            st.metric("Total Amount", f"${total_amount:,.0f}")
                    except:
                        st.metric("Amount Field", "Available")
                else:
                    st.metric("Columns", len(display_df.columns))

            with cols[3]:
                if "Source_Channel" in filtered_df.columns:
                    unique_sources = filtered_df["Source_Channel"].nunique()
                    st.metric("Sources", unique_sources)
                else:
                    st.metric("Rows", len(filtered_df))

        # -------------------------
        # BRANCH SUMMARY CHART
        # -------------------------
        st.markdown("### 📍 Branch Summary")
        show_branch_summary_chart(filtered_df)

        # -------------------------
        # REFRESH BUTTON
        # -------------------------
        if st.button("🔄 Refresh Data", type="secondary"):
            st.cache_data.clear()
            st.experimental_rerun()


if __name__ == "__main__":
    main()
