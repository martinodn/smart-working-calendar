import streamlit as st
import pandas as pd
from utils.gsheets import load_data
from utils.email_sender import send_email

# Page configuration
st.set_page_config(page_title="Calendario - Smart working", page_icon="📅", layout="wide")

# Secrets
MAGIC_WORD = st.secrets.get("MAGIC_WORD", "password")
# You can put the sheet URL in secrets or hardcode it here if it's constant
# For now, let's try to get it from secrets, or ask user input if missing
SHEET_URL = st.secrets.get("SHEET_URL", "")

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == MAGIC_WORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Parola Magica", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Parola Magica", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Parola magica errata")
        return False
    else:
        # Password correct.
        return True

import datetime

def format_month_name(ym_str):
    """Formats 'YYYY-MM' string to 'Month Year' in Italian."""
    if not ym_str:
        return ""
    try:
        from datetime import datetime
        month_obj = datetime.strptime(ym_str, "%Y-%m")
        month_name = month_obj.strftime("%B %Y")
        month_names_it = {
            "January": "Gennaio", "February": "Febbraio", "March": "Marzo",
            "April": "Aprile", "May": "Maggio", "June": "Giugno",
            "July": "Luglio", "August": "Agosto", "September": "Settembre",
            "October": "Ottobre", "November": "Novembre", "December": "Dicembre"
        }
        for en, it in month_names_it.items():
            month_name = month_name.replace(en, it)
        return month_name
    except:
        return ym_str

# ... (imports)

if check_password():
    st.title("📅 Calendario - Smart working")
    
    if not SHEET_URL:
        st.warning("URL del foglio Google non trovato nei secrets. Inseriscilo qui sotto:")
        SHEET_URL = st.text_input("Google Sheet URL")
    
    if SHEET_URL:
        with st.spinner("Caricamento calendario..."):
            df = load_data(SHEET_URL)
        
        if df is not None:
            st.toast("Calendario caricato!", icon="✅")
            
            # --- Month Filtering Logic ---
            # Assume the column containing 'yyyy-mm' is named 'mese' based on user context.
            # If not found, try to guess or fallback.
            month_col = 'mese'
            if month_col not in df.columns:
                # Fallback: try to find a column that looks like a date or 'month'
                potential_cols = [c for c in df.columns if 'mese' in c.lower() or 'month' in c.lower() or 'date' in c.lower()]
                if potential_cols:
                    month_col = potential_cols[0]
                else:
                    st.error(f"Colonna '{month_col}' non trovata nel foglio. Colonne disponibili: {list(df.columns)}")
                    month_col = None

            if month_col:
                # Get current year-month
                now = datetime.datetime.now()
                current_ym = now.strftime("%Y-%m")
                
                # Get unique months from dataframe
                # Ensure they are strings and sort them
                available_months = sorted([str(m) for m in df[month_col].unique() if pd.notna(m)])
                
                # Filter for future months only (>= current_ym)
                future_months = [m for m in available_months if m >= current_ym]
                
                if not future_months:
                    st.warning(f"Nessun mese futuro trovato (>= {current_ym}). Mostro tutti i mesi disponibili.")
                    future_months = available_months

                # Dropdown for selection
                selected_month = st.selectbox("Seleziona il mese", future_months, format_func=format_month_name)
                
                # Filter DataFrame
                filtered_df = df[df[month_col] == selected_month]
            else:
                filtered_df = df # Fallback if column not found

            # Styling
            # Color all columns except 'persona' and 'mese' with unique colors for each value
            columns_to_color = [col for col in filtered_df.columns if col.lower() not in ['persona', 'mese']]
            
            # Get all unique values from these columns to assign a consistent color map
            unique_values = pd.unique(filtered_df[columns_to_color].values.ravel('K'))
            
            # Generate a color palette with fixed colors for specific values
            def get_color_for_value(val):
                if pd.isna(val) or str(val).strip() == "" or str(val).strip().upper() == "X":
                    return ""
                
                # Fixed colors for specific values
                color_map_fixed = {
                    "Ferie": "background-color: #90EE90",  # Verde chiaro
                    "Casa": "background-color: #ADD8E6",   # Blu chiaro
                    "Ufficio": "background-color: #FFA500", # Arancione
                    "Offsite": "background-color: #DAA520",  # Giallo scuro (goldenrod)
                    "Trasferta": "background-color: #FF6B6B"  # Rosso chiaro
                }
                
                val_stripped = str(val).strip()
                if val_stripped in color_map_fixed:
                    return color_map_fixed[val_stripped]
                
                # For other values, use hash-based colors
                import hashlib
                hash_object = hashlib.md5(str(val).encode())
                hex_hash = hash_object.hexdigest()
                hue = (int(hex_hash[0:8], 16) * 137) % 360
                saturation = 60 + (int(hex_hash[8:10], 16) % 20)
                lightness = 70 + (int(hex_hash[10:12], 16) % 10)
                return f'background-color: hsl({hue}, {saturation}%, {lightness}%)'

            # Create a map of value -> style string
            color_map = {val: get_color_for_value(val) for val in unique_values}

            def apply_color(val):
                return color_map.get(val, "")

            styled_df = filtered_df.style.map(apply_color, subset=columns_to_color)
            
            # Configure columns to hide headers for 'persona' and 'mese'/'data'
            # We try to match 'persona' and the identified month column
            col_config = {}
            
            # Hide 'persona' header if it exists
            if 'persona' in df.columns:
                col_config['persona'] = st.column_config.Column(label="")
            
            # Hide month column header
            if month_col:
                col_config[month_col] = st.column_config.Column(label="")
            
            # Also check for 'data' just in case user calls it that
            if 'data' in df.columns:
                col_config['data'] = st.column_config.Column(label="")

            st.dataframe(
                styled_df, 
                width='stretch', 
                hide_index=True,
                column_config=col_config
            )
            
            # --- Overlap Warning ---
            # Check for days where ALL present values are in the target set
            target_values = {"Trasferta", "Offsite", "Ufficio"}
            overlap_days = []
            
            for col in columns_to_color:
                # Get values for this column (day)
                col_values = filtered_df[col].dropna().astype(str).values
                
                # Check if we have values and if ALL of them are in the target set
                # We use strip() to handle potential whitespace
                if len(col_values) > 0 and all(val.strip() in target_values for val in col_values):
                    overlap_days.append(col)
            
            # Manual overlap addition
            st.write("**Gestione Sovrapposizioni**")
            manual_overlap_input = st.text_input(
                "Aggiungi manualmente giorni di sovrapposizione (separati da virgola, es. 5, 12)",
                help="Inserisci i giorni che vuoi segnalare come sovrapposizione, oltre a quelli rilevati automaticamente."
            )
            
            if manual_overlap_input:
                manual_days = [d.strip() for d in manual_overlap_input.split(',') if d.strip()]
                # Merge with automatic, avoiding duplicates
                # We use a set to avoid duplicates, then convert back to list
                current_overlaps = set(overlap_days)
                current_overlaps.update(manual_days)
                overlap_days = list(current_overlaps)
            
            if overlap_days:
                # Try to convert to integers for sorting and clean display (no decimals)
                try:
                    # Convert to int (handling potential floats like '1.0')
                    int_days = sorted([int(float(x)) for x in overlap_days])
                    # Join with comma
                    days_str = ", ".join(map(str, int_days))
                except ValueError:
                    # Fallback if conversion fails
                    days_str = ", ".join(sorted(overlap_days))
                
                st.warning(f"⚠️ Attenzione! Dog-sitting rahelistico necessario nei giorni: {days_str}.")
            # --- Smart Working Statistics ---
            st.subheader("📊 Statistiche Smart Working")
            
            # Option to choose calculation mode
            stats_mode = st.radio(
                "Modalità calcolo", 
                ["Mese Selezionato", "Intervallo Personalizzato"], 
                horizontal=True,
                label_visibility="collapsed"
            )
            
            stats_df_source = None
            
            if stats_mode == "Mese Selezionato":
                stats_df_source = filtered_df
                current_range_label = f"Mese: {format_month_name(selected_month)}" if month_col else "Tutti i dati"
            else:
                # Cumulative mode
                if month_col:
                    # Get all available months sorted
                    all_months = sorted([str(m) for m in df[month_col].unique() if pd.notna(m)])
                    
                    if all_months:
                        c1, c2 = st.columns(2)
                        with c1:
                            start_month = st.selectbox("Da", all_months, index=0, format_func=format_month_name)
                        with c2:
                            # Default to last month
                            end_month = st.selectbox("A", all_months, index=len(all_months)-1, format_func=format_month_name)
                        
                        if start_month > end_month:
                            st.error("Il mese di inizio deve essere precedente o uguale al mese di fine.")
                            stats_df_source = None
                        else:
                            # Filter by range
                            stats_df_source = df[(df[month_col] >= start_month) & (df[month_col] <= end_month)]
                            current_range_label = f"Intervallo: {format_month_name(start_month)} - {format_month_name(end_month)}"
                    else:
                        st.warning("Nessun dato sui mesi trovato.")
                        stats_df_source = df
                else:
                    st.info("Colonna mese non trovata, uso tutti i dati.")
                    stats_df_source = df
                    current_range_label = "Tutti i dati"

            if stats_df_source is not None:
                # Accumulate counts per person
                person_stats = {}
                
                for index, row in stats_df_source.iterrows():
                    person_name = row.get('persona', f"Persona {index+1}")
                    
                    # Get values for this row (excluding metadata columns)
                    # We re-evaluate columns to exclude for every row to be safe, or just use the list we defined earlier
                    # But columns_to_color was based on filtered_df which might have different columns if structure varies (unlikely)
                    # Let's use a robust exclusion list
                    exclude_cols = ['persona', 'mese', 'data']
                    if month_col:
                        exclude_cols.append(month_col)
                        
                    person_values = [str(val).strip() for col, val in row.items() 
                                   if col.lower() not in [c.lower() for c in exclude_cols] and pd.notna(val) and str(val).strip() != ""]
                    
                    casa_count = person_values.count("Casa")
                    ufficio_count = person_values.count("Ufficio")
                    
                    if person_name not in person_stats:
                        person_stats[person_name] = {'casa': 0, 'ufficio': 0}
                    
                    person_stats[person_name]['casa'] += casa_count
                    person_stats[person_name]['ufficio'] += ufficio_count
                
                # Build final stats list
                stats_data = []
                for person, counts in person_stats.items():
                    total_relevant = counts['casa'] + counts['ufficio']
                    if total_relevant > 0:
                        sw_percentage = (counts['casa'] / total_relevant) * 100
                    else:
                        sw_percentage = 0.0
                        
                    stats_data.append({
                        "Persona": person,
                        "Giorni Casa": counts['casa'],
                        "Giorni Ufficio": counts['ufficio'],
                        "% Smart Working": sw_percentage  # Use 0-100 scale
                    })
                
                if stats_data:
                    stats_df = pd.DataFrame(stats_data)
                    st.caption(f"Statistiche calcolate su: **{current_range_label}**")
                    st.dataframe(
                        stats_df,
                        width='stretch',
                        hide_index=True,
                        column_config={
                            "% Smart Working": st.column_config.ProgressColumn(
                                "% Smart Working",
                                help="Percentuale di giorni in Smart Working (Casa / (Casa + Ufficio))",
                                format="%.1f%%",
                                min_value=0,
                                max_value=100,
                            )
                        }
                    )
                else:
                    st.info("Nessun dato rilevante trovato per il calcolo delle statistiche.")

            st.divider()
            st.subheader("Invia Calendario")
            
            # Get predefined recipients from secrets
            predefined_recipients = {}
            if "recipient_emails" in st.secrets:
                predefined_recipients = dict(st.secrets["recipient_emails"])
            
            selected_recipients = []
            
            # Multiselect for predefined recipients
            if predefined_recipients:
                st.write("**Seleziona destinatari dalla lista:**")
                selected_names = st.multiselect(
                    "Destinatari predefiniti",
                    options=list(predefined_recipients.keys()),
                    label_visibility="collapsed"
                )
                selected_recipients = [predefined_recipients[name] for name in selected_names]
            
            # Text input for additional recipients
            manual_input = st.text_input("Aggiungi altri indirizzi email (separati da virgola)")
            
            if manual_input:
                manual_recipients = [email.strip() for email in manual_input.split(",") if email.strip()]
                selected_recipients.extend(manual_recipients)
            
            # Show selected recipients
            if selected_recipients:
                st.info(f"📧 Invierò a: {', '.join(selected_recipients)}")
            
            if st.button("Invia Email"):
                if selected_recipients:
                    # Format month name for email (e.g., "2025-12" -> "Dicembre 2025")
                    try:
                        from datetime import datetime
                        month_obj = datetime.strptime(selected_month if month_col else "", "%Y-%m")
                        month_name = month_obj.strftime("%B %Y")  # e.g., "December 2025"
                        # Translate to Italian
                        month_names_it = {
                            "January": "Gennaio", "February": "Febbraio", "March": "Marzo",
                            "April": "Aprile", "May": "Maggio", "June": "Giugno",
                            "July": "Luglio", "August": "Agosto", "September": "Settembre",
                            "October": "Ottobre", "November": "Novembre", "December": "Dicembre"
                        }
                        for en, it in month_names_it.items():
                            month_name = month_name.replace(en, it)
                    except:
                        month_name = selected_month if month_col else "questo mese"
                    
                    # Build overlap message if any
                    overlap_message = ""
                    if overlap_days:
                        try:
                            int_days = sorted([int(float(x)) for x in overlap_days])
                            days_str = ", ".join(map(str, int_days))
                        except:
                            days_str = ", ".join(sorted(overlap_days))
                        overlap_message = f"<p><strong>⚠️ Attenzione:</strong> Sono state rilevate delle sovrapposizioni nei giorni: {days_str}.</p>"
                    
                    # Create HTML table from dataframe
                    # Remove 'persona' and 'mese' column names for email/CSV
                    email_df = filtered_df.copy()
                    rename_map = {}
                    if 'persona' in email_df.columns:
                        rename_map['persona'] = ''
                    if month_col and month_col in email_df.columns:
                        rename_map[month_col] = ''
                    if rename_map:
                        email_df = email_df.rename(columns=rename_map)
                    
                    html_table = email_df.to_html(index=False, border=1)
                    
                    # Build personalized email body
                    body_html = f"""
                    <html>
                    <body style="font-family: Tahoma, Geneva, sans-serif; font-size: 20px; line-height: 1.6; color: #333;">
                        <p>Gentile {{recipient_name}},</p>
                        
                        <p>Di seguito puoi trovare il calendario di smart working aggiornato per il mese di <strong>{month_name}</strong>.</p>
                        
                        {overlap_message}
                        
                        <br>
                        {html_table}
                        
                        <br>
                        <p>In allegato anche il relativo file CSV.</p>
            
                        <p>Grazie mille,<br>
                        Martino</p>
                    </body>
                    </html>
                    """
                    
                    # Create a mapping of email -> name from predefined recipients
                    recipient_names_map = {}
                    if predefined_recipients:
                        # Reverse the mapping: email -> name
                        for name, email in predefined_recipients.items():
                            recipient_names_map[email] = name
                    
                    with st.spinner("Invio email in corso..."):
                        success, message, results = send_email(
                            selected_recipients, 
                            f"Calendario {month_name} - Smart Working", 
                            body_html, 
                            attachment_df=email_df,
                            recipient_names=recipient_names_map
                        )
                    
                    if success:
                        st.balloons()
                        st.success(message)
                        
                        # Show detailed results if there were any issues
                        if results.get("failed") or results.get("invalid"):
                            with st.expander("📋 Dettagli invio"):
                                if results.get("successful"):
                                    st.write("✅ **Inviate con successo:**")
                                    for email in results["successful"]:
                                        st.write(f"  - {email}")
                                
                                if results.get("failed"):
                                    st.write("❌ **Invio fallito:**")
                                    for email, error in results["failed"]:
                                        st.write(f"  - {email}: {error}")
                                
                                if results.get("invalid"):
                                    st.write("⚠️ **Indirizzi non validi:**")
                                    for email in results["invalid"]:
                                        st.write(f"  - {email}")
                    else:
                        st.error(f"Errore durante l'invio: {message}")
                        
                        # Show what went wrong
                        if results.get("invalid"):
                            st.warning(f"Indirizzi non validi: {', '.join(results['invalid'])}")
                else:
                    st.warning("Seleziona o inserisci almeno un indirizzo email.")
