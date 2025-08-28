# -*- coding: utf-8 -*-
"""
Created on Thu Aug 28 12:59:37 2025

@author: rarbo
"""

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- App title ---
st.title("Google Sheets AI Scheduler - Conflict Checker")

# --- Upload Google Service Account JSON ---
st.info("Upload your Google Service Account JSON credentials")
creds_file = st.file_uploader("Choose credentials JSON", type=["json"])

if creds_file is not None:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.experimental_get_query_params() or creds_file, scope)
    client = gspread.authorize(creds)

    # --- Input Google Sheet name ---
    sheet_name = st.text_input("Enter Google Sheet name:", "")

    if sheet_name:
        try:
            spreadsheet = client.open(sheet_name)
            st.success(f"✅ Opened spreadsheet: {sheet_name}")

            # --- Choose worksheet ---
            ws_names = [ws.title for ws in spreadsheet.worksheets()]
            selected_ws = st.selectbox("Select worksheet to check:", ws_names)

            if selected_ws:
                ws = spreadsheet.worksheet(selected_ws)
                data = ws.get_all_values()

                # --- Find headers ---
                header_row_idx = None
                day_col = date_col = time_col = None
                first_field_col = None

                def find_first_field_col(header_row):
                    lower = [c.strip().lower() for c in header_row]
                    for j, name in enumerate(lower):
                        if "field" in name:
                            return j
                    return None

                for i, row in enumerate(data[:10]):
                    lower = [c.strip().lower() for c in row]
                    if "day" in lower and "date" in lower:
                        header_row_idx = i
                        day_col = lower.index("day")
                        date_col = lower.index("date")
                        time_col = lower.index("time") if "time" in lower else None
                        first_field_col = find_first_field_col(row)
                        break

                if header_row_idx is None or first_field_col is None:
                    st.error("Could not find header row or first field column")
                else:
                    headers = data[header_row_idx]

                    # --- Detect conflicts ---
                    conflicts = []
                    last_day = ""
                    last_date = ""
                    last_time = ""

                    def get_cell(row, idx):
                        return row[idx].strip() if (idx is not None and idx < len(row)) else ""

                    for row_idx in range(header_row_idx + 1, len(data)):
                        row = data[row_idx]
                        if not row:
                            continue
                        day = get_cell(row, day_col) or last_day
                        date = get_cell(row, date_col) or last_date
                        time_val = get_cell(row, time_col) if time_col is not None else ""
                        if not time_val and last_time:
                            time_val = last_time

                        if day: last_day = day
                        if date: last_date = date
                        if time_val: last_time = time_val

                        seen_teams = {}
                        for col_idx in range(first_field_col, len(headers)):
                            if col_idx >= len(row):
                                continue
                            team = row[col_idx].strip()
                            if not team:
                                continue
                            if team in seen_teams:
                                conflicts.append([team, date, day, headers[col_idx], time_val])
                            else:
                                seen_teams[team] = col_idx

                    if conflicts:
                        st.write(f"⚠️ Found {len(conflicts)} conflicts")
                        st.table(conflicts)
                    else:
                        st.success("✅ No conflicts found!")

        except Exception as e:
            st.error(f"Error: {e}")