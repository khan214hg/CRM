# 🚨 MISSING MODULE HANDLING
try:
    import streamlit as st
    import sqlite3
    import pandas as pd
    import plotly.express as px
    from datetime import datetime
except ModuleNotFoundError as e:
    missing_module = str(e).split("'")[1]
    print(f"Missing module: {missing_module}. Please install it using: pip install {missing_module}")
    raise

# ✅ Installation instructions in app UI
st.sidebar.info("ℹ If you see a ModuleNotFoundError, install dependencies:")
st.sidebar.code("pip install -r requirements.txt")

with open("requirements.txt", "w") as f:
    f.write("streamlit\npandas\nplotly\n")

st.sidebar.success("requirements.txt generated in current directory")

# -----------------------------
# DB SETUP
# -----------------------------
conn = sqlite3.connect('crm.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                phone TEXT,
                company TEXT,
                tags TEXT,
                created_at TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER,
                title TEXT,
                value REAL,
                stage TEXT,
                close_date TEXT,
                FOREIGN KEY(contact_id) REFERENCES contacts(id)
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER,
                note TEXT,
                created_at TEXT,
                FOREIGN KEY(contact_id) REFERENCES contacts(id)
            )''')

conn.commit()

# -----------------------------
# DB FUNCTIONS
# -----------------------------
def add_contact(name, email, phone, company, tags):
    c.execute("INSERT INTO contacts (name, email, phone, company, tags, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (name, email, phone, company, tags, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def get_contacts():
    return pd.read_sql("SELECT * FROM contacts", conn)

def add_opportunity(contact_id, title, value, stage, close_date):
    c.execute("INSERT INTO opportunities (contact_id, title, value, stage, close_date) VALUES (?, ?, ?, ?, ?)",
              (contact_id, title, value, stage, close_date))
    conn.commit()

def get_opportunities():
    return pd.read_sql("SELECT o.id, c.name as contact_name, o.title, o.value, o.stage, o.close_date FROM opportunities o JOIN contacts c ON o.contact_id = c.id", conn)

def add_note(contact_id, note):
    c.execute("INSERT INTO notes (contact_id, note, created_at) VALUES (?, ?, ?)",
              (contact_id, note, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def get_notes(contact_id):
    return pd.read_sql(f"SELECT * FROM notes WHERE contact_id={contact_id}", conn)

# -----------------------------
# SIDEBAR NAVIGATION
# -----------------------------
st.sidebar.title("CRM Navigation")
page = st.sidebar.radio("Go to:", ["Dashboard", "Contacts", "Opportunities", "Settings"])

# -----------------------------
# MAIN PAGES LOGIC
# -----------------------------
if page == "Dashboard":
    st.title("📊 CRM Dashboard")
    contacts = get_contacts()
    opps = get_opportunities()
    st.metric("Total Contacts", len(contacts))
    st.metric("Total Opportunities", len(opps))
    st.metric("Total Pipeline Value", f"${opps['value'].sum():,.2f}")
    if not opps.empty:
        fig = px.histogram(opps, x='stage', y='value', histfunc='sum', title='Pipeline Value by Stage')
        st.plotly_chart(fig)
        opps['close_month'] = pd.to_datetime(opps['close_date']).dt.to_period('M').astype(str)
        fig2 = px.bar(opps.groupby('close_month')['value'].sum().reset_index(), x='close_month', y='value', title='Revenue by Month')
        st.plotly_chart(fig2)

elif page == "Contacts":
    st.title("👤 Manage Contacts")
    if st.button("Add New Contact"):
        with st.form("add_contact"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            company = st.text_input("Company")
            tags = st.text_input("Tags (comma separated)")
            submitted = st.form_submit_button("Save")
            if submitted:
                add_contact(name, email, phone, company, tags)
                st.success("Contact added.")
    contacts_df = get_contacts()
    search = st.text_input("Search Contacts")
    if search:
        contacts_df = contacts_df[contacts_df['name'].str.contains(search, case=False, na=False)]
    st.dataframe(contacts_df)
    selected_id = st.selectbox("Select Contact to View Notes", contacts_df['id'] if not contacts_df.empty else [None])
    if selected_id:
        notes_df = get_notes(selected_id)
        st.subheader("Notes")
        st.table(notes_df)
        with st.form("add_note"):
            note = st.text_area("Add Note")
            submitted_note = st.form_submit_button("Add Note")
            if submitted_note:
                add_note(selected_id, note)
                st.success("Note added.")

elif page == "Opportunities":
    st.title("💼 Manage Opportunities")
    contacts = get_contacts()
    with st.form("add_opp"):
        contact = st.selectbox("Contact", contacts['name'] if not contacts.empty else [])
        title = st.text_input("Opportunity Title")
        value = st.number_input("Value", min_value=0.0)
        stage = st.selectbox("Stage", ["Prospecting", "Proposal", "Negotiation", "Won", "Lost"])
        close_date = st.date_input("Expected Close Date")
        submitted = st.form_submit_button("Add Opportunity")
        if submitted and contact:
            contact_id = contacts[contacts['name'] == contact]['id'].values[0]
            add_opportunity(contact_id, title, value, stage, close_date.strftime('%Y-%m-%d'))
            st.success("Opportunity added.")
    st.subheader("Opportunities List")
    opps_df = get_opportunities()
    st.dataframe(opps_df)

elif page == "Settings":
    st.title("⚙ Settings")
    contacts_df = get_contacts()
    st.download_button("Download Contacts CSV", contacts_df.to_csv(index=False), "contacts.csv")
    uploaded = st.file_uploader("Upload contacts CSV", type="csv")
    if uploaded:
        new_df = pd.read_csv(uploaded)
        for _, row in new_df.iterrows():
            add_contact(row['name'], row['email'], row['phone'], row['company'], str(row.get('tags', '')))
        st.success("Contacts imported.")
    opps_df = get_opportunities()
    st.download_button("Download Opportunities CSV", opps_df.to_csv(index=False), "opportunities.csv")
