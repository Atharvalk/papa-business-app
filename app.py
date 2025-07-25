import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import gspread
from google.oauth2.service_account import Credentials

# --- GOOGLE SHEETS SETUP ---
creds = st.secrets["service_account"]
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(creds, scopes=scope)

gc = gspread.authorize(credentials)
sheet_key = "1HjTAeI0yCGYySs-FnTpoiN4QShdRkdKomXyHi9uuKXY"
sh = gc.open_by_key(sheet_key)
worksheet = sh.sheet1  # Business record sheet
stock_sheet = sh.worksheet("StockData")  # New sheet created for stock management

# --- LOGIN SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username == "admin" and password == "2501":
            st.session_state.logged_in = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()

# --- PAGE SETUP ---
st.set_page_config(page_title="Papa Business App", layout="centered")
tab1, tab2 = st.tabs(["📦 Business Record", "📊 Stock Manager"])

# =============== 📦 BUSINESS RECORD TAB ===============
with tab1:
    st.title("📦 Business Record System")

    # Load business records
    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])

    st.sidebar.header("➕ Add New Entry")
    party = st.sidebar.text_input("Party Name")
    item = st.sidebar.number_input("Item Amount ₹", min_value=0, step=100)
    payment = st.sidebar.number_input("Payment Received ₹", min_value=0, step=100)
    date = st.sidebar.date_input("Date", datetime.now())

    if st.sidebar.button("Add Entry"):
        prev_balance = float(df[df["Party"] == party]["Balance"].iloc[-1]) if party in df["Party"].values else 0
        new_balance = item - payment
        new_row = [party, str(date), str(item), str(payment), str(new_balance)]
        worksheet.append_row(new_row)
        st.success("✅ Entry Added Successfully!")
        st.rerun()

    party_list = df["Party"].unique().tolist()
    selected_party = st.selectbox("🔍 Search Party", options=party_list, index=None, placeholder="Type to search...")

    if selected_party:
        st.subheader(f"📄 Records for {selected_party}")
        party_data = df[df["Party"] == selected_party]
        total_balance = party_data["Balance"].astype(float).sum()

        st.markdown(f"<h4 style='color:#1f77b4;'>🧮 Total Balance for {selected_party}: ₹{total_balance}</h4>", unsafe_allow_html=True)

        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
        col1.markdown("**Date**")
        col2.markdown("**Amount**")
        col3.markdown("**Payment**")
        col4.markdown("**Balance**")
        col5.markdown("**Index**")
        col6.markdown("**❌ Delete**")

        for real_idx, row in party_data.iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 2, 2, 2, 1])
            c1.write(row["Date"])
            c2.write(row["Amount"])
            c3.write(row["Payment"])
            c4.write(row["Balance"])
            c5.write(str(real_idx))
            if c6.button("❌", key=f"del_{real_idx}"):
                worksheet.delete_rows(real_idx + 2)
                st.success("✅ Entry deleted")
                st.rerun()

        def generate_pdf(party_name, party_data):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Party: {party_name}", ln=True, align='L')
            pdf.cell(200, 10, txt=" ", ln=True)
            pdf.cell(40, 10, "Date", 1)
            pdf.cell(40, 10, "Amount", 1)
            pdf.cell(40, 10, "Payment", 1)
            pdf.cell(40, 10, "Balance", 1)
            pdf.ln()
            for i, row in party_data.iterrows():
                pdf.cell(40, 10, str(row["Date"]), 1)
                pdf.cell(40, 10, f"Rs. {row['Amount']}", 1)
                pdf.cell(40, 10, f"Rs. {row['Payment']}", 1)
                pdf.cell(40, 10, f"Rs. {row['Balance']}", 1)
                pdf.ln()
            file_name = f"{party_name}_records.pdf"
            pdf.output(file_name)
            return file_name

        if st.button("📥 Download PDF"):
            party_data = df[df["Party"] == selected_party].reset_index(drop=True)
            file_path = generate_pdf(selected_party, party_data)
            with open(file_path, "rb") as f:
                st.download_button("⬇️ Click to Download", f, file_name=file_path)

# =============== 📊 STOCK MANAGER TAB (CLEANED + WORKING) ===============
with tab2:
    st.title("📊 Stock Manager System")

    # --- Select or Create Company ---
    st.subheader("🏢 Select or Create Company")
    sheet_list = [ws.title for ws in sh.worksheets() if ws.title != worksheet.title]
    selected_company = st.selectbox("Choose Company", options=sheet_list + ["➕ Add New Company"], key="select_company_main")

    if selected_company == "➕ Add New Company":
        new_company_name = st.text_input("Enter new company name", key="new_company_input")
        if st.button("✅ Create Company", key="create_company_button"):
            if new_company_name and new_company_name not in sheet_list:
                new_ws = sh.add_worksheet(title=new_company_name, rows="1000", cols="20")
                new_ws.append_row(["item", "stock", "new", "m", "t", "w", "th", "fr", "sa", "s", "final"])
                st.success(f"✅ Company '{new_company_name}' created successfully!")
                st.rerun()
            else:
                st.warning("⚠️ Company name invalid or already exists.")
        st.stop()

    # --- Delete Company Option ---
    st.markdown("---")
    st.subheader("🗑️ Delete Company")
    delete_company = st.selectbox("Select company to delete", [s for s in sheet_list], key="delete_company_select")
    if st.button("❌ Delete Selected Company", key="delete_company_button"):
        if delete_company:
            sh.del_worksheet(sh.worksheet(delete_company))
            st.success(f"✅ Company '{delete_company}' deleted successfully!")
            st.rerun()
        else:
            st.warning("⚠️ Please select a company.")

    # --- If company is selected ---
    if selected_company and selected_company != "➕ Add New Company":
        stock_sheet = sh.worksheet(selected_company)
        stock_data = stock_sheet.get_all_values()

        if stock_data:
            stock_df = pd.DataFrame(stock_data[1:], columns=stock_data[0])
        else:
            stock_df = pd.DataFrame(columns=["item", "stock", "new", "m", "t", "w", "th", "fr", "sa", "s", "final"])
            stock_sheet.append_row(stock_df.columns.tolist())

        # --- Add or Update Stock ---
        st.subheader(f"📥 Add or Update Stock for: {selected_company}")
        item_name = st.text_input("🧾 Item Name")
        current_stock = st.number_input("📦 Current Stock", min_value=0)
        new_stock = st.number_input("➕ New Stock Arrived", min_value=0)
        daily_out = {}
        for day in ["m", "t", "w", "th", "fr", "sa", "s"]:
            daily_out[day] = st.number_input(f"📤 Out on {day.upper()}", min_value=0, key=f"{selected_company}_{day}")

        if st.button("💾 Save Stock Entry", key="save_stock_entry"):
            total_out = sum(daily_out.values())
            final_stock = current_stock + new_stock - total_out
            new_row = [item_name, current_stock, new_stock] + list(daily_out.values()) + [final_stock]
            stock_sheet.append_row([str(x) for x in new_row])
            st.success("✅ Stock Entry Added")
            st.rerun()

        # --- Show Current Stock Table ---
        st.subheader(f"📋 Current Stock Sheet for {selected_company}")
        st.dataframe(stock_df)

        # --- Delete Item Entry ---
    st.subheader("➖ Delete Item Entry")

    # Convert column names to lowercase for consistent access
    stock_df.columns = stock_df.columns.str.lower()

    if st.checkbox("Enable Delete Mode", key="delete_item_checkbox"):
        if not stock_df.empty and "item" in stock_df.columns and stock_df["item"].dropna().tolist():
            items = stock_df["item"].dropna().tolist()
            selected_item = st.selectbox("Select item to delete", items, key="delete_item_select")
            if st.button("❌ Confirm Delete", key="delete_item_button"):
                idx_to_delete = stock_df[stock_df["item"] == selected_item].index
                if not idx_to_delete.empty:
                    if not idx_to_delete.empty:
                        stock_sheet.delete_rows(int(idx_to_delete[0]) + 2)
                        st.success("✅ Item Deleted")
                        st.rerun()

                    st.success("✅ Item Deleted")
                    st.rerun()
                else:
                    st.warning("⚠️ Item not found.")
        else:
            st.warning("⚠️ No stock data available yet.")
