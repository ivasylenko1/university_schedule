import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
#8300016640:AAHTImEQNnVAiPGUkkF6riK2IlR2M_D4XJw
# -------------------
# Helpers (same as before)
# -------------------
def load_schedule(path):
    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp1251")
    return df

def parse_schedule(df):
    weeks = {}
    current_week = None

    for i, row in df.iterrows():
        first_col = str(row.iloc[0]).strip()

        if "тижд" in first_col:
            current_week = int("".join([c for c in first_col if c.isdigit()]))
            weeks[current_week] = []
            continue

        if current_week is None or ":" not in first_col:
            continue

        start_time = datetime.strptime(first_col, "%H:%M:%S").time()
        end_time = (datetime.combine(datetime.today(), start_time) + timedelta(minutes=80)).time()

        for day_idx, subject in enumerate(row[1:7], start=0):
            if pd.notna(subject):
                weeks[current_week].append({
                    "Week": current_week,
                    "Day": ["Mon","Tue","Wed","Thu","Fri","Sat"][day_idx],
                    "Start": datetime.combine(datetime.today(), start_time),
                    "End": datetime.combine(datetime.today(), end_time),
                    "Subject": subject
                })

    return weeks

# -------------------
# Streamlit App
# -------------------
st.title("📅 University Timetable (Calendar View)")

uploaded = st.file_uploader("Upload CSV", type=["csv"])
if uploaded:
    df = load_schedule(uploaded)
    weeks = parse_schedule(df)

    week_choice = st.selectbox("Select Week", sorted(weeks.keys()))
    week_data = weeks[week_choice]

    subjects = sorted({x["Subject"] for x in week_data})
    selected_subjects = st.multiselect("Filter by Subject", subjects)

    if selected_subjects:
        week_data = [x for x in week_data if x["Subject"] in selected_subjects]

    week_df = pd.DataFrame(week_data)

    if not week_df.empty:
        fig = px.timeline(
            week_df,
            x_start="Start",
            x_end="End",
            y="Day",
            color="Subject",
            text="Subject",
        )
        fig.update_yaxes(categoryorder="array", categoryarray=["Mon","Tue","Wed","Thu","Fri","Sat"])
        fig.update_layout(xaxis=dict(tickformat="%H:%M"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No subjects match your filter for this week.")