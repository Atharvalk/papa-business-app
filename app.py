import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import gspread
from google.oauth2.service_account import Credentials

# --- GOOGLE SHEETS SETUP ---
# Load credentials from secrets
creds = st.secrets["service_account"]
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(creds, scopes=scope)

gc = gspread.authorize(credentials)
sh = gc.open("BusinessAppData")
worksheet = sh.sheet1

# Load data from sheet
data = worksheet.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0])  # skip header row if any

# --- LOGIN SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state.logged_in = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()

# --- PAGE SETUP ---
st.set_page_config(page_title="Papa Business App", layout="centered")
st.title("📦 Business Record App")

# --- SIDEBAR INPUTS ---
st.sidebar.header("➕ Add New Entry")

party = st.sidebar.text_input("Party Name")
item = st.sidebar.number_input("Item Amount ₹", min_value=0, step=100)
payment = st.sidebar.number_input("Payment Received ₹", min_value=0, step=100)
date = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("Add Entry"):
    prev_balance = float(df[df["Party"] == party]["Balance"].iloc[-1]) if party in df["Party"].values else 0
    new_balance = item - payment  # only individual balance now
    new_row = [party, str(date), str(item), str(payment), str(new_balance)]
    worksheet.append_row(new_row)
    st.success("✅ Entry Added Successfully!")
    st.rerun()

# --- SEARCH AND DISPLAY ---
party_list = df["Party"].unique().tolist()
selected_party = st.selectbox("🔍 Search Party", options=party_list, index=None, placeholder="Type to search...")

if selected_party:
    st.subheader(f"📄 Records for {selected_party}")
    party_data = df[df["Party"] == selected_party].reset_index(drop=True)
    total_balance = party_data["Balance"].astype(float).sum()

    st.markdown(f"<h4 style='color:#1f77b4;'>🧮 Total Balance for {selected_party}: ₹{total_balance}</h4>", unsafe_allow_html=True)

    st.dataframe(party_data)

# --- PDF GENERATOR ---
def generate_pdf(party_name, party_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Party: {party_name}", ln=True, align='L')
    pdf.cell(200, 10, txt=" ", ln=True)

    pdf.cell(40, 10, "Date", 1)
    pdf.cell(40, 10, "Item Amount", 1)
    pdf.cell(40, 10, "Payment", 1)
    pdf.cell(40, 10, "Balance", 1)
    pdf.ln()

    for i, row in party_data.iterrows():
        pdf.cell(40, 10, str(row["Date"]), 1)
        pdf.cell(40, 10, f"Rs. {row['Item Amount']}", 1)
        pdf.cell(40, 10, f"Rs. {row['Payment']}", 1)
        pdf.cell(40, 10, f"Rs. {row['Balance']}", 1)
        pdf.ln()

    file_name = f"{party_name}_records.pdf"
    pdf.output(file_name)
    return file_name

if selected_party and st.button("📥 Download PDF"):
    party_data = df[df["Party"] == selected_party].reset_index(drop=True)
    file_path = generate_pdf(selected_party, party_data)
    with open(file_path, "rb") as f:
        st.download_button("⬇️ Click to Download", f, file_name=file_path)
