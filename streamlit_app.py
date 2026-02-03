import streamlit as st
import os
import csv
import json
from datetime import datetime, timedelta
import pandas as pd

# --- Configuration ---
TRANSACTIONS_FILE = "transactions.csv"
STATE_FILE = "state.json"

st.set_page_config(page_title="Masha's DIY Money", page_icon="💰", layout="centered")

# --- Core Logic ---
def initialize_files():
    if not os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Description", "Amount", "Balance"])
            # Initialize with starting balance of 0
            writer.writerow([datetime.now().strftime("%Y-%m-%d"), "Starting Balance", 0.0, 0.0])
            
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'w') as f:
            json.dump({"last_run_date": datetime.now().strftime("%Y-%m-%d")}, f)

def get_current_balance():
    if not os.path.exists(TRANSACTIONS_FILE):
        initialize_files()
    try:
        with open(TRANSACTIONS_FILE, newline='') as file:
            reader = list(csv.reader(file))
            if len(reader) < 2:
                return 0.0
            # Last row, last column is balance
            return float(reader[-1][3])
    except (IndexError, ValueError):
        return 0.0

def add_transaction(description, amount):
    balance = get_current_balance() + amount
    with open(TRANSACTIONS_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d"), description, amount, balance])

def get_transactions():
    if not os.path.exists(TRANSACTIONS_FILE):
        initialize_files()
    with open(TRANSACTIONS_FILE, newline='') as file:
        reader = list(csv.reader(file))
        return reader

# --- Allowance Logic --- as defined in original app ---
def get_last_run_date():
    if not os.path.exists(STATE_FILE):
        return datetime.now().strftime("%Y-%m-%d")
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        return state.get("last_run_date")
    except json.JSONDecodeError:
        return datetime.now().strftime("%Y-%m-%d")

def update_last_run_date():
    with open(STATE_FILE, 'w') as f:
        json.dump({"last_run_date": datetime.now().strftime("%Y-%m-%d")}, f)

def calculate_missed_tuesdays(last_run_date_str):
    today = datetime.now().date()
    try:
        last_date = datetime.strptime(last_run_date_str, "%Y-%m-%d").date()
    except ValueError:
        last_date = today # fail safe
        
    days_passed = (today - last_date).days
    missed = 0
    for i in range(1, days_passed + 1):
        day = last_date + timedelta(days=i)
        if day.weekday() == 1:  # Tuesday
            missed += 1
    return missed

def update_weekly_allowance():
    last_run_date = get_last_run_date()
    missed_tuesdays = calculate_missed_tuesdays(last_run_date)
    if missed_tuesdays > 0:
        for _ in range(missed_tuesdays):
            add_transaction("Weekly Allowance", 50.00)
    update_last_run_date()
    return missed_tuesdays

# --- Initialization on App Load ---
if not os.path.exists(TRANSACTIONS_FILE) or not os.path.exists(STATE_FILE):
    initialize_files()

# Check and update allowance automatically
missed_count = update_weekly_allowance()
if missed_count > 0:
    st.toast(f"System: Added allowance for {missed_count} missed Tuesday(s).", icon="✅")

# --- UI Layout ---
st.title("Masha's DIY Money Tracker 💰")

# Display Balance
current_balance = get_current_balance()
st.metric(label="Current Balance", value=f"${current_balance:,.2f}")

st.markdown("---")

tab1, tab2 = st.tabs(["Add Transaction", "History"])

with tab1:
    st.subheader("Add or Subtract Money")
    with st.form("add_transaction_form", clear_on_submit=True):
        desc_input = st.text_input("Description", placeholder="Pocket money, chores, etc.")
        amount_input = st.number_input("Amount ($)", step=0.01, format="%.2f", help="Positive to add, negative to subtract.")
        
        submitted = st.form_submit_button("Submit Transaction", type="primary")
        
        if submitted:
            if not desc_input:
                st.error("Please provide a description.")
            elif amount_input == 0:
                st.warning("Amount cannot be zero.")
            else:
                add_transaction(desc_input, amount_input)
                st.success("Transaction added successfully!")
                st.rerun()

with tab2:
    st.subheader("Transaction History")
    raw_data = get_transactions()
    
    if len(raw_data) > 1:
        headers = raw_data[0]
        data = raw_data[1:]
        
        # Use Pandas for better table display
        df = pd.DataFrame(data, columns=headers)
        
        # Convert numeric columns
        try:
            df['Amount'] = pd.to_numeric(df['Amount'])
            df['Balance'] = pd.to_numeric(df['Balance'])
        except ValueError:
            pass # Handle case where CSV might be corrupted or empty strings
            
        # Sort by newest first (assuming mostly append-only, so reverse order)
        df = df.iloc[::-1]
        
        st.dataframe(
            df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Amount": st.column_config.NumberColumn(format="$%.2f"),
                "Balance": st.column_config.NumberColumn(format="$%.2f"),
                "Date": st.column_config.TextColumn("Date"),
                "Description": st.column_config.TextColumn("Description"),
            }
        )
        
        # Download button
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="transactions.csv",
            mime="text/csv",
        )
    else:
        st.info("No transactions recorded yet.")

