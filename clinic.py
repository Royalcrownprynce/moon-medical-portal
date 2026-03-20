import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from twilio.rest import Client

# --- 1. TWILIO CONFIG (Put your SID and Token here) ---
TWILIO_ACCOUNT_SID = 'AC6073343f2eac751e9b431b6c5e83292b'
TWILIO_AUTH_TOKEN = '4d7c9cb23113d7f41bc9b3f5a3f92d91'
TWILIO_PHONE_NUMBER = '+13503055066'

def send_automated_sms(to_phone, message_body):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=message_body, from_=TWILIO_PHONE_NUMBER, to=to_phone)
        return True
    except:
        return False

# --- 2. SETUP & BRANDING ---
st.set_page_config(page_title="Moon Medical Portal", page_icon="🌙", layout="wide")
if not os.path.exists("insurance_cards"):
    os.makedirs("insurance_cards")

st.image("logo.png", width=500) 
st.markdown("---")

# --- 3. DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect('moon_medical.db')
    c = conn.cursor()
    # Added 'pharmacy' column here
    c.execute('''CREATE TABLE IF NOT EXISTS appointments
                 (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, date TEXT, time TEXT, 
                  symptoms TEXT, urgency TEXT, check_in_time TEXT, 
                  insurance_path TEXT, pharmacy TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 4. APP TABS ---
tab1, tab2, tab3 = st.tabs(["🏥 Booking & Refills", "📍 Patient Check-In", "📋 Doctor Dashboard"])

with tab1:
    st.header("Schedule Your Visit or Request Refill")
    with st.form("booking_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Patient Name")
            phone = st.text_input("Mobile Phone (Include +1, e.g., +17576106107)")
            date = st.date_input("Select Date", min_value=datetime.today())
            
            # --- THIS IS THE NEW PHARMACY SELECTION BOX ---
            pharmacy = st.selectbox("Select Pharmacy for Refills", 
                                    ["N/A - New Appointment", 
                                     "Walgreens - High St, Portsmouth", 
                                     "CVS - Frederick Blvd, Portsmouth", 
                                     "Sentara Pharmacy", 
                                     "Walmart Pharmacy - Tidewater Dr"])
        with col2:
            time = st.selectbox("Available Slots", ["9:00 AM", "10:30 AM", "1:00 PM", "3:30 PM"])
            symptoms = st.text_area("Describe Symptoms or Refill Details")
            uploaded_file = st.file_uploader("Upload Insurance Photo", type=['png', 'jpg', 'jpeg'])
        
        submit = st.form_submit_button("Confirm & Send Request")

        if submit:
            if name and phone and symptoms:
                # Handle Image
                img_path = "None"
                if uploaded_file:
                    img_path = f"insurance_cards/{name.replace(' ', '_')}.png"
                    with open(img_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                # Triage & Save
                urgency = "🔴 URGENT" if any(x in symptoms.lower() for x in ["chest", "breath", "fever", "pain"]) else "Routine"
                conn = sqlite3.connect('moon_medical.db')
                conn.execute("INSERT INTO appointments (name, phone, date, time, symptoms, urgency, insurance_path, pharmacy) VALUES (?,?,?,?,?,?,?,?)",
                             (name, phone, str(date), time, symptoms, urgency, img_path, pharmacy))
                conn.commit()
                conn.close()

                # Trigger SMS
                send_automated_sms(phone, f"Moon Medical: Hi {name}, request received for {pharmacy}. We will text you once approved.")
                
                st.success(f"Success! {name}, request sent.")
                st.balloons()
            else:
                st.error("Please enter Name, Phone, and Symptoms.")

# --- TAB 3: DOCTOR DASHBOARD (With Refill Approval) ---
with tab3:
    st.header("Daily Patient Overview")
    conn = sqlite3.connect('moon_medical.db')
    df = pd.read_sql_query("SELECT id, urgency, name, phone, time, pharmacy, symptoms FROM appointments ORDER BY id DESC", conn)
    
    if not df.empty:
        st.dataframe(df, width='stretch')
        st.markdown("---")
        st.subheader("Manage Refills")
        
        # Select patient to approve
        patient_id = st.selectbox("Select Patient to Approve/Notify:", df['id'])
        # Get specific row for that patient
        p_data = df[df['id'] == patient_id].iloc[0]
        
        if st.button(f"✅ Approve Refill for {p_data['name']}"):
            msg = f"Moon Medical: Your refill has been approved and sent to {p_data['pharmacy']}."
            send_automated_sms(p_data['phone'], msg)
            st.success(f"Notification sent to {p_data['name']}!")
    else:
        st.info("No data yet.")
    conn.close()
