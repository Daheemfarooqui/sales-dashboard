import streamlit as st
import pandas as pd
import gspread

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Finz Dashboard",
    layout="wide"
)

st.title("📊 Finz Dashboard")

# =====================================================
# GOOGLE SHEET
# =====================================================

from google.oauth2.service_account import Credentials

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

sh = gspread.authorize(creds)

sa = sh.open(
    "best Copy of Hourly -  Report Summary - Offline/Online"
)

worksheet = sa.worksheet(
    "test"
)

data = worksheet.get_all_values()

# =====================================================
# FIX DUPLICATE HEADERS
# =====================================================

df = pd.DataFrame(data[1:], columns=data[0])

# =====================================================
# CLEAN COLUMN NAMES
# =====================================================

df.columns = (
    df.columns
      .astype(str)
      .str.strip()
      .str.replace("\n", " ", regex=False)
      .str.replace("\r", " ", regex=False)
)

# =====================================================
# KEEP ONLY REQUIRED COLUMNS
# =====================================================

required_cols = [
    "RH",
    "ASM Name",
    "Centre Name",
    "FTD Overall Admissions",
    "FTD Loan Punched",
    "FTD Loan Approved",
    "FTD Loan Approved Vol."
]

missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"Missing Columns: {missing}")
    st.write("Available Columns:")
    st.write(df.columns.tolist())
    st.stop()

# =====================================================
# NUMERIC CLEANING
# =====================================================

for col in [
    "FTD Overall Admissions",
    "FTD Loan Punched",
    "FTD Loan Approved",
    "FTD Loan Approved Vol."
]:

    df[col] = (
        df[col]
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("-", "0")
        .replace("", "0")
    )

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    ).fillna(0)

# =====================================================
# FILTERS
# =====================================================

st.sidebar.header("Filters")

# RH Filter

rh_list = ["All"] + sorted(
    df["RH"].dropna().unique().tolist()
)

selected_rh = st.sidebar.selectbox(
    "Select RH",
    rh_list
)

filtered_df = df.copy()

if selected_rh != "All":

    filtered_df = filtered_df[
        filtered_df["RH"] == selected_rh
    ]

# ASM Filter

asm_list = ["All"] + sorted(
    filtered_df["ASM Name"]
    .dropna()
    .unique()
    .tolist()
)

selected_asm = st.sidebar.selectbox(
    "Select ASM",
    asm_list
)

if selected_asm != "All":

    filtered_df = filtered_df[
        filtered_df["ASM Name"] == selected_asm
    ]

# Use filtered data

df = filtered_df.copy()

# =====================================================
# LOAD RAW DATA
# =====================================================

worksheet_raw = sa.worksheet(
    "Pending_pap"
)

raw_data = worksheet_raw.get_all_values()

df2 = pd.DataFrame(
    raw_data[1:],
    columns=raw_data[0]
)

df2.columns = (
    df2.columns
      .astype(str)
      .str.strip()
      .str.replace("\n", " ", regex=False)
      .str.replace("\r", " ", regex=False)
)

# =====================================================
# APPLY SAME FILTERS TO RAW DATA
# =====================================================

raw_filtered = df2.copy()

if "RH" in raw_filtered.columns:

    if selected_rh != "All":

        raw_filtered = raw_filtered[
            raw_filtered["RH"] == selected_rh
        ]

if "ASM Name" in raw_filtered.columns:

    if selected_asm != "All":

        raw_filtered = raw_filtered[
            raw_filtered["ASM Name"] == selected_asm
        ]

# =====================================================
# REPORT
# =====================================================

# =====================================================
# GROUP BY RH + ASM
# =====================================================

summary_df = (
    df.groupby(
        ["RH", "ASM Name"],
        as_index=False
    )
    .agg({
        "Centre Name": "count",
        "FTD Overall Admissions": "sum",
        "FTD Loan Punched": "sum",
        "FTD Loan Approved": "sum",
        "FTD Loan Approved Vol.": "sum"
    })
)

summary_df.rename(
    columns={
        "Centre Name": "Number of Center"
    },
    inplace=True
)

summary_df["Admissions vs Loan Conversation %"] = (
    summary_df["FTD Loan Approved"]
    /
    summary_df["FTD Overall Admissions"].replace(0, 1)
    * 100
).round(0)

summary_df["Admissions vs Loan Conversation %"] = (
    summary_df["Admissions vs Loan Conversation %"]
    .astype(int)
    .astype(str)
    + "%"
)

summary_df["FTD Loan Approved Vol."] = (
    summary_df["FTD Loan Approved Vol."]
    .apply(lambda x: f"{x:,.0f}")
)

st.subheader("📊 RH / ASM Summary Report")

st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True
)

# =====================================================
# RAW DATA
# =====================================================

st.divider()

with st.expander(
    "📋 e-Mandate pending",
    expanded=True
):

    st.write(
        f"Total Pending Cases: {len(raw_filtered):,}"
    )

    st.dataframe(
        raw_filtered,
        use_container_width=True,
        hide_index=True
    )
