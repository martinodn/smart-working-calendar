import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def connect_to_gsheets():
    """Connects to Google Sheets using credentials from st.secrets."""
    try:
        # Create a dictionary from the secrets object
        credentials_dict = dict(st.secrets["gcp_service_account"])
        
        creds = Credentials.from_service_account_info(
            credentials_dict, scopes=SCOPES
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Errore nella connessione a Google Sheets: {e}")
        return None

def load_data(sheet_url):
    """Loads data from the first worksheet of the given Google Sheet URL."""
    client = connect_to_gsheets()
    if not client:
        return None
    
    try:
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.get_worksheet(0)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Errore nel caricamento dei dati: {e}")
        return None
