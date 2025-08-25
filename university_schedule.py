
import re
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st


DAY_TOKENS = {
    "mon": ["понеділок", "понедiлок", "monday", "mon"],
    "tue": ["вівторок", "вiвторок", "tuesday", "tue"],
    "wed": ["середа", "wednesday", "wed"],
    "thu": ["четвер", "thursday", "thu"],
    "fri": ["п’ятниця", "п'ятниця", "пятниця", "friday", "fri"],
    "sat": ["субота", "saturday", "sat"],
}
DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat"]
DAY_LABELS = {"mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu", "fri": "Fri", "sat": "Sat"}


def read_csv_any(path_or_buffer):
    try:
        return pd.read_csv(path_or_buffer)
    except UnicodeDecodeError:
        return pd.read_csv(path_or_buffer, encoding="cp1251")


def find_day_in_text(text):
    t = str(text).strip().lower()
    for k, tokens in DAY_TOKENS.items():
        for tok in tokens:
            if tok in t:
                return k
    return None


def first_int(text):
    m = re.search(r"\d+", str(text))
    return int(m.group()) if m else None


def parse_time(text):
    s = str(text).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def map_columns_to_days(df):
    col_to_day = {}
    current_day = None
    for col in df.columns[1:]:
        day = find_day_in_text(col)
        if day:
            current_day = day
        col_to_day[col] = current_day
    # keep only columns that belong to a known day
    return {c: d for c, d in col_to_day.items() if d in DAY_ORDER}


def extract_weeks(df):
    weeks = {}
    col_day = map_columns_to_days(df)

    start_week = first_int(df.columns[0]) if "тиж" in str(df.columns[0]).lower() else 1
    current_week = start_week or 1

    for _, row in df.iterrows():
        first = str(row.iloc[0]).strip()
        if "тиж" in first.lower():
            wk = first_int(first)
            if wk:
                current_week = wk
            continue

        t = parse_time(first)
        if not t:
            continue

        start_dt = datetime.combine(datetime(2000, 1, 1), t)
        end_dt = start_dt + timedelta(minutes=80)
        slot = (start_dt.time(), end_dt.time())

        for col, day in col_day.items():
            val = row.get(col)
            if pd.isna(val):
                continue
            s = str(val).strip()
            if not s:
                continue
            weeks.setdefault(current_week, []).append(
                {
                    "week": current_week,
                    "day": day,
                    "start": slot[0],
                    "end": slot[1],
                    "subject": s,
                    "slot_label": f"{slot[0].strftime('%H:%M')}–{slot[1].strftime('%H:%M')}",
                }
            )
    # Keep all detected weeks
    return weeks


def build_table(week_items, selected_subjects=None):
    selected_subjects = set(selected_subjects or [])
    times = sorted({(i["start"], i["end"]) for i in week_items})
    idx = [f"{s.strftime('%H:%M')}–{e.strftime('%H:%M')}" for s, e in times]
    cols = [DAY_LABELS[d] for d in DAY_ORDER]
    table = pd.DataFrame("", index=idx, columns=cols)

    for i in week_items:
        if selected_subjects and i["subject"] not in selected_subjects:
            continue
        r = f"{i['start'].strftime('%H:%M')}–{i['end'].strftime('%H:%M')}"
        c = DAY_LABELS[i["day"]]
        existing = table.at[r, c]
        table.at[r, c] = f"{existing} | {i['subject']}" if existing else i["subject"]

    return table


def style_table(df):
    def fmt(val):
        s = str(val)
        if " | " in s:
            return "background-color:#d60000;color:white;font-weight:600"
        if s and s != "":
            return "background-color:#c7f7c0;color:#454545"  # custom green text
        return ""
    return df.style.applymap(fmt)


# -------------------- Streamlit app --------------------
st.set_page_config(page_title="University Timetable (Table View)", page_icon="📅", layout="wide")
st.title("📅 University Timetable — Table View")

uploaded = st.file_uploader("Upload your CSV", type=["csv"])

if not uploaded:
    st.info("Upload the exported CSV with weeks, days Mon–Sat, and time in 24‑hour format.")
    st.stop()

df = read_csv_any(uploaded)
weeks = extract_weeks(df)

if not weeks:
    st.error("No weeks detected. Ensure the first column contains time rows and week markers like '1тижд.', '2тижд.'")
    st.stop()

# All distinct subjects from all weeks
all_subjects = sorted({i["subject"] for items in weeks.values() for i in items})

# Initialize session_state for selected subjects if not present
if "selected_subjects" not in st.session_state:
    st.session_state.selected_subjects = []

# Use key parameter to persist selection across reruns
sel_subjects = st.multiselect(
    "Filter by subject",
    all_subjects,
    default=st.session_state.selected_subjects,
    key="selected_subjects"
)

available_weeks = sorted(weeks.keys())
week_sel = st.selectbox("Week", available_weeks, index=0)

week_items = weeks.get(week_sel, [])
if not week_items:
    st.warning("No entries for this week.")
    st.stop()

table = build_table(week_items, sel_subjects)
st.subheader(f"Week {week_sel}")
st.dataframe(
    style_table(table),
    use_container_width=True,
    height=min(680, 56 + 36 * max(1, len(table)))
)
st.caption("Green = single class; Red = overlap in the same time slot & day.")