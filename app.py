# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import gspread
from google.oauth2.service_account import Credentials
import time

# --- GOOGLE SHEETS SETUP ---
creds = st.secrets["service_account"]
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(creds, scopes=scope)

# --- HELPER FUNCTIONS ---
@st.cache_resource(ttl=600)
def get_sheet():
    gc = gspread.authorize(credentials)
    return gc.open_by_key("1HjTAeI0yCGYySs-FnTpoiN4QShdRkdKomXyHi9uuKXY")

def safe_append_row(worksheet, row, retries=3, delay=2):
    for _ in range(retries):
        try:
            worksheet.append_row(row)
            return True
        except gspread.exceptions.APIError:
            time.sleep(delay)
    st.error("❌ Failed to append row after retries.")
    return False

def safe_delete_row(worksheet, row_index, retries=3, delay=2):
    for _ in range(retries):
        try:
            worksheet.delete_rows(row_index)
            return True
        except gspread.exceptions.APIError:
            time.sleep(delay)
    st.error("❌ Failed to delete row after retries.")
    return False

sh = get_sheet()
worksheet = sh.sheet1

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
    # ----------------------- Title -----------------------
    st.title("📦 Business Record System")

    # ------------------ Fetch Sheet Data ------------------
    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])

    # ----------------- ➕ Add New Entry Section -----------------
    st.sidebar.header("➕ Add New Entry")
    party = st.sidebar.text_input("Party Name")
    item = st.sidebar.number_input("Item Amount ₹", min_value=0, step=100)
    payment = st.sidebar.number_input("Payment Received ₹", min_value=0, step=100)
    date = st.sidebar.date_input("Date", datetime.now())

    if st.sidebar.button("Add Entry"):
        prev_balance = float(df[df["Party"] == party]["Balance"].iloc[-1]) if party in df["Party"].values else 0
        new_balance = item - payment
        new_row = [party, str(date), str(item), str(payment), str(new_balance)]
        if safe_append_row(worksheet, new_row):
            st.success("✅ Entry Added Successfully!")
            st.rerun()

 # ------------------ 🔍 Party Search / Suggestions ------------------
party_list = df["Party"].unique().tolist()
if "selected_party" not in st.session_state:
    st.session_state.selected_party = ""

typed_party = st.text_input("🔍 Party Name", value=st.session_state.selected_party, placeholder="Type or select...")
party_suggestions = [p for p in party_list if typed_party.lower() in p.lower()]
if typed_party:
    st.markdown("### 🔍 Suggestions:")
    for s in party_suggestions[:5]:
        if st.button(s, key=f"party_suggest_{s}"):
            st.session_state.selected_party = s
            typed_party = s

selected_party = typed_party

# ------------------ 📄 Party Records Table ------------------
if selected_party:
    party_data = df[df["Party"] == selected_party]
    st.subheader(f"📄 Records for {selected_party}")
    party_data = df[df["Party"] == selected_party]
    total_balance = party_data["Balance"].astype(float).sum()

    st.markdown(
        f"<h4 style='color:#1f77b4;'>🧮 Total Balance for {selected_party}: ₹{total_balance}</h4>",
        unsafe_allow_html=True,
    )

    # --------- HTML Table ---------
    # --- Build HTML Table as string ---
html_table = """
<style>
    .responsive-table {
        width: 100%;
        overflow-x: auto;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        min-width: 600px;
    }
    th, td {
        border: 1px solid #555;
        padding: 8px;
        text-align: center;
    }
    th {
        background-color: #111;
        color: #fff;
    }
</style>

<div class="responsive-table">
    <table>
        <tr>
            <th>Date</th>
            <th>Amount</th>
            <th>Payment</th>
            <th>Balance</th>
            <th>Index</th>
        </tr>
"""

for real_idx, row in party_data.iterrows():
    html_table += f"""
        <tr>
            <td>{row['Date']}</td>
            <td>{row['Amount']}</td>
            <td>{row['Payment']}</td>
            <td>{row['Balance']}</td>
            <td>{real_idx}</td>
        </tr>
    """

html_table += "</table></div>"

# --- Properly Render HTML ---
st.markdown(html_table, unsafe_allow_html=True)

# -------- ✅ Delete Buttons Section --------
st.markdown("### 🗑️ Delete Entry")
for real_idx, row in party_data.iterrows():
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"🗓️ {row['Date']} | ₹{row['Amount']} → ₹{row['Balance']}")
    with col2:
        if st.button("❌", key=f"delete_{real_idx}"):
            if safe_delete_row(worksheet, real_idx + 2):
                st.success("✅ Entry deleted")
                st.rerun()

        # ------------------ 💾 Generate PDF Download Button ------------------
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
            for _, row in party_data.iterrows():
                pdf.cell(40, 10, str(row["Date"]), 1)
                pdf.cell(40, 10, f"Rs. {row['Amount']}", 1)
                pdf.cell(40, 10, f"Rs. {row['Payment']}", 1)
                pdf.cell(40, 10, f"Rs. {row['Balance']}", 1)
                pdf.ln()
            file_name = f"{party_name}_records.pdf"
            pdf.output(file_name)
            return file_name

        if st.button("💾Download PDF"):
            party_data = df[df["Party"] == selected_party].reset_index(drop=True)
            file_path = generate_pdf(selected_party, party_data)
            with open(file_path, "rb") as f:
                st.download_button("⬇️ Click to Download", f, file_name=file_path)






# =============== 📊 STOCK MANAGER TAB ===============
with tab2:
    # 📊 Main Tab: Stock Manager System (Date-wise)
    st.title("📊 Stock Manager System (Date-wise)")

    # 🏢 COMPANY MANAGEMENT SECTION
    with st.container():
        # 🏢 Select or Create Company
        st.subheader("🏢 Select or Create Company")
        sheet_list = [ws.title for ws in sh.worksheets() if ws.title != worksheet.title]
        selected_company = st.selectbox("Choose Company", options=sheet_list + ["➕ Add New Company"], key="select_company_main")

        if selected_company == "➕ Add New Company":
            new_company_name = st.text_input("Enter new company name", key="new_company_input")
            if st.button("✅ Create Company", key="create_company_button"):
                if new_company_name and new_company_name not in sheet_list:
                    new_ws = sh.add_worksheet(title=new_company_name, rows="1000", cols="10")
                    new_ws.append_row(["item", "date", "current_stock", "new_stock", "sold_qty", "final_stock"])
                    st.success(f"✅ Company '{new_company_name}' created successfully!")
                    st.rerun()
                else:
                    st.warning("⚠️ Company name invalid or already exists.")
            st.stop()

        # 🗑️ Delete Company
        st.divider()
        st.subheader("🗑️ Delete Company")
        delete_company = st.selectbox("Select company to delete", [s for s in sheet_list], key="delete_company_select")
        if st.button("❌ Delete Selected Company", key="delete_company_button"):
            if delete_company:
                sh.del_worksheet(sh.worksheet(delete_company))
                st.success(f"✅ Company '{delete_company}' deleted successfully!")
                st.rerun()
            else:
                st.warning("⚠️ Please select a company.")

    st.markdown("---")

    if selected_company and selected_company != "➕ Add New Company":
        # 📥 Load or Create DataFrame
        stock_sheet = sh.worksheet(selected_company)
        data = stock_sheet.get_all_values()
        if data and len(data) > 1:
            df = pd.DataFrame(data[1:], columns=[c.strip().lower() for c in data[0]])
        else:
            df = pd.DataFrame(columns=["item", "date", "current_stock", "new_stock", "sold_qty", "final_stock"])

        # 📥 Add or Update Stock Entries
        st.subheader(f"📥 Add or Update Stock for: {selected_company}")

        item_names = df["item"].dropna().unique().tolist()

        # ✅ Step 1: Session default set karo
                # ✅ Session state default
        if "selected_item" not in st.session_state:
            st.session_state.selected_item = ""

        # ✅ Text input (manual typing or suggestion result)
        typed_item = st.text_input("🧾 Item Name", value=st.session_state.selected_item, placeholder="Type to search or add")

        # ✅ Suggestions based on typed input
        suggestions = [name for name in item_names if typed_item.lower() in name.lower()]
        if typed_item:
            st.markdown("### 🔍 Suggestions:")
            for s in suggestions[:5]:
                if st.button(s, key=f"suggest_{s}"):
                    st.session_state.selected_item = s
                    typed_item = s  # Update displayed input without rerun

        # ✅ Final usable item name
        item_name = typed_item

        selected_dates = st.date_input("📅 Select up to 10 dates", [], min_value=datetime(2023, 1, 1), max_value=datetime.now(), help="Max 10 dates", key="date_input", disabled=False)
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_date, end_date = selected_dates
            selected_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        else:
            selected_dates = list(selected_dates)

        item_df = df[df["item"] == item_name]
        if not item_df.empty:
            item_df["date"] = pd.to_datetime(item_df["date"], errors="coerce")
            latest_row = item_df.sort_values("date").iloc[-1]
            autofill_stock = int(latest_row["final_stock"])
        else:
            autofill_stock = 0

        current_stock = st.number_input("📦 Current Stock", min_value=0, value=autofill_stock)
        new_stock = st.number_input("➕ New Stock Arrived", min_value=0, key="new_stock_input")

        sold_entries = {}
        for dt in selected_dates:
            sold = st.number_input(
                f"📤 Sold on {dt.strftime('%d %b %Y')}",
                min_value=0,
                key=f"sold_{dt.strftime('%Y%m%d')}"
            )
            sold_entries[str(dt)] = sold

        if st.button("💾 Save Stock Entry", key="save_stock_btn"):
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            final = current_stock

            for dt_str, sold_qty in sold_entries.items():
                dt_obj = pd.to_datetime(dt_str).strftime("%Y-%m-%d")
                mask = (df["item"] == item_name) & (df["date"].dt.strftime("%Y-%m-%d") == dt_obj)

                if mask.any():
                    row_idx = df[mask].index[0] + 2
                    old_sold = int(df.loc[mask, "sold_qty"].values[0])
                    new_sold = old_sold + sold_qty
                    final = final + new_stock - sold_qty
                    stock_sheet.update(f"C{row_idx}:F{row_idx}", [[current_stock, new_stock, new_sold, final]])
                else:
                    final = final + new_stock - sold_qty
                    new_row = [item_name, dt_obj, current_stock, new_stock, sold_qty, final]
                    stock_sheet.append_row([str(x) for x in new_row])

                current_stock = final
                new_stock = 0

            st.success("✅ Stock data saved successfully!")
            st.rerun()

        # 📊 Stock Summary Table
        st.subheader("📊 Filtered Stock Summary")

        summary_range = st.date_input("📅 Select date range (max 10 days)", [], min_value=datetime(2023,1,1), max_value=datetime.now(), help="Choose 7–10 days for summary")
        if isinstance(summary_range, tuple) and len(summary_range) == 2:
            s_date, e_date = summary_range
            summary_dates = [s_date + timedelta(days=i) for i in range((e_date - s_date).days + 1)]
        else:
            summary_dates = list(summary_range)

        if summary_dates:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            summary_data = df[df["date"].isin(summary_dates)]
            all_items = df["item"].dropna().unique()

            summary_rows = []

            for item in all_items:
                item_data = df[df["item"] == item]
                item_summary = {
                    "item": item,
                    "current stock": item_data.sort_values("date")["final_stock"].dropna().iloc[-1] if not item_data.empty else 0,
                    "new stock": int(summary_data[summary_data["item"] == item]["new_stock"].astype(float).sum())
                }
                for dt in summary_dates:
                    dt_str = dt.strftime("%d %b")
                    sold_qty = df[
                        (df["item"] == item) & (df["date"] == pd.to_datetime(dt))
                    ]["sold_qty"]

                    item_summary[dt_str] = int(float(sold_qty.sum())) if not sold_qty.empty else 0

                item_summary["total sold"] = sum(item_summary[dt.strftime("%d %b")] for dt in summary_dates)
                summary_rows.append(item_summary)

            summary_df = pd.DataFrame(summary_rows)
            st.dataframe(summary_df)

        # ❌ Delete Item Entry
        st.subheader("➖ Delete Item Entry")
        if st.checkbox("Enable Delete Mode", key="delete_mode_checkbox"):
            if not df.empty and "item" in df.columns:
                del_item = st.selectbox("Select item to delete", df["item"].unique().tolist())
                del_date = st.date_input("Select date to delete entry")
                if st.button("❌ Confirm Delete", key="delete_row_btn"):
                    mask = (df["item"] == del_item) & (df["date"] == pd.to_datetime(str(del_date)))
                    idx_to_del = df[mask].index
                    if not idx_to_del.empty:
                        stock_sheet.delete_rows(int(idx_to_del[0]) + 2)
                        st.success("✅ Entry Deleted")
                        st.rerun()
                    else:
                        st.warning("❗ Entry not found")
