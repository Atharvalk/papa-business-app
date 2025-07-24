import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import firebase_admin
from firebase_admin import credentials, firestore

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

# --- FIREBASE SETUP ---
if not firebase_admin._apps:
    from firebase_admin import credentials

    # ✅ Convert secrets manually to dictionary
    cred_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
        "universe_domain": st.secrets["gcp_service_account"]["universe_domain"]
    }

    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)


if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()


def generate_pdf(party_name, party_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt=f"Party: {party_name}", ln=True, align='L')
    pdf.cell(200, 10, txt=" ", ln=True)  # empty line

    # Table headers
    pdf.cell(40, 10, "Date", 1)
    pdf.cell(40, 10, "Item Amount", 1)
    pdf.cell(40, 10, "Payment", 1)
    pdf.cell(40, 10, "Balance", 1)
    pdf.ln()

    # Table rows
    for i, row in party_data.iterrows():
        pdf.cell(40, 10, str(row['Date']), 1)
        pdf.cell(40, 10, f"Rs. {row['Item Amount']}", 1)
        pdf.cell(40, 10, f"Rs. {row['Payment']}", 1)
        pdf.cell(40, 10, f"Rs. {row['Balance']}", 1)
        pdf.ln()

    # Save PDF
    file_name = f"{party_name}_records.pdf"
    pdf.output(file_name)
    return file_name

# Set page config
st.set_page_config(page_title="Papa Business App", layout="centered")

st.title("📦 Business Record App")

# Load or create data
try:
    df = pd.read_csv("data.csv")
except:
    df = pd.DataFrame(columns=["Party", "Date", "Item Amount", "Payment", "Balance"])

# Sidebar: Add new entry
st.sidebar.header("➕ Add New Entry")

party = st.sidebar.text_input("Party Name")
item = st.sidebar.number_input("Item Amount ₹", min_value=0, step=100)
payment = st.sidebar.number_input("Payment Received ₹", min_value=0, step=100)
date = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("Add Entry"):
    prev_balance = float(df[df["Party"] == party]["Balance"].iloc[-1]) if party in df["Party"].values else 0
    new_balance = item - payment  # Only individual balance now
    new_entry = {
        "Party": party,
        "Date": date,
        "Item Amount": item,
        "Payment": payment,
        "Balance": new_balance
    }
    df = df._append(new_entry, ignore_index=True)
    df.to_csv("data.csv", index=False)
    st.success("✅ Entry Added Successfully!")

# Search Party
# 🔍 Realtime Suggestion While Typing
# Realtime Autocomplete Style Search
party_list = df['Party'].unique().tolist()

if "search_input_val" not in st.session_state:
    st.session_state.search_input_val = ""

def update_search_input():
    st.session_state.search_input_val = st.session_state.search_box

selected_party = st.selectbox(
    "🔍 Search Party",
    options=party_list,
    index=None,
    placeholder="Type to search...",
)
if selected_party:
    st.subheader(f"📄 Records for {selected_party}")
    party_data = df[df["Party"] == selected_party].reset_index(drop=True)

    total_balance = party_data['Balance'].sum()
    st.markdown(f"<h4 style='color:#1f77b4;'>🧮 Total Balance for {selected_party}: ₹{total_balance}</h4>", unsafe_allow_html=True)

    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
    col1.markdown("**Date**")
    col2.markdown("**Item Amount ₹**")
    col3.markdown("**Payment Received ₹**")
    col4.markdown("**Balance ₹**")
    col5.markdown(" ")
    col6.markdown("**Delete**")

    for i, row in party_data.iterrows():
        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
        col1.write(row["Date"])
        col2.write(f"₹{row['Item Amount']}")
        col3.write(f"₹{row['Payment']}")
        col4.write(f"₹{row['Balance']}")
        col5.write("")  # Reserved for edit button
        if col6.button("🗑", key=f"del_{selected_party}_{i}"):
            row_index = df[(df["Party"] == selected_party)].index[i]
            df.drop(index=row_index, inplace=True)
            df.to_csv("data.csv", index=False)
            st.rerun()

search_input = st.session_state.search_input_val
matching_parties = [p for p in party_list if search_input.lower() in p.lower()] if search_input else []

selected_party = None
if matching_parties:
    selected_party = st.selectbox("📋 Matching Parties", matching_parties, index=0, key="live_suggestion")

if selected_party:
    st.subheader(f"📄 Records for {selected_party}")
    party_data = df[df["Party"] == selected_party].reset_index(drop=True)
    
    total_balance = party_data['Balance'].sum()
    st.markdown(f"<h4 style='color:#1f77b4;'>🧮 Total Balance for {selected_party}: ₹{total_balance}</h4>", unsafe_allow_html=True)

    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
    col1.markdown("**Date**")
    col2.markdown("**Item Amount ₹**")
    col3.markdown("**Payment Received ₹**")
    col4.markdown("**Balance ₹**")
    col5.markdown(" ")
    col6.markdown("**Delete**")

    for i, row in party_data.iterrows():
        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
        col1.write(row["Date"])
        col2.write(f"₹{row['Item Amount']}")
        col3.write(f"₹{row['Payment']}")
        col4.write(f"₹{row['Balance']}")
        col5.write("")  # Reserved for edit button
        if col6.button("🗑", key=f"del_{i}"):
            row_index = df[(df["Party"] == selected_party)].index[i]
            df.drop(index=row_index, inplace=True)
            df.to_csv("data.csv", index=False)
            st.rerun()


if st.button("📥 Download PDF"):
    party_data = df[df["Party"] == selected_party].reset_index(drop=True)
    file_path = generate_pdf(selected_party, party_data)
    with open(file_path, "rb") as f:
        st.download_button("⬇️ Click to Download", f, file_name=file_path)
        