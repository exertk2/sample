import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.express as px
import numpy as np
import datetime
import sqlite3
import os

# --- Database Creation and Population Function ---
def create_and_populate_db(db_name='school_data.db'):
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Latitude and Longitude data for each school (used for data generation)
        geo_data_map = {
            'Chuo Elementary School': {'lat': 31.5959, 'lon': 130.5586},
            'Tenmonkan Elementary School': {'lat': 31.5901, 'lon': 130.5562},
            'Kamoike Elementary School': {'lat': 31.5650, 'lon': 130.5470},
            'Taniyama Elementary School': {'lat': 31.5000, 'lon': 130.4900},
            'Ishiki Elementary School': {'lat': 31.6200, 'lon': 130.5400},
            'Sakuragaoka Elementary School': {'lat': 31.5400, 'lon': 130.5200}
        }

        # Create school_data_table (including columns for latitude, longitude, student_count, and special_support_class_size)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS school_data_table (
                Date TEXT NOT NULL,
                School_Name TEXT NOT NULL,
                Student_Count INTEGER NOT NULL,
                Special_Support_Class_Size INTEGER NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                PRIMARY KEY (Date, School_Name)
            )
        ''')

        # Generate sample school data (student_count and special_support_class_size)
        schools = list(geo_data_map.keys())
        data = []
        current_date = datetime.date.today()

        for year in range(2015, current_date.year + 1):
            for month in range(1, 13):
                if year == current_date.year and month > current_date.month:
                    break
                date_str = f"{year}-{month:02d}"
                for school in schools:
                    initial_students = np.random.randint(300, 800)
                    yearly_student_change = np.random.randint(-20, 30)
                    monthly_student_fluctuation = np.random.randint(-50, 50)
                    
                    student_count = initial_students + (year - 2015) * yearly_student_change + monthly_student_fluctuation
                    student_count = max(100, int(student_count))

                    special_support_class_size = np.random.randint(5, 30)

                    # Get latitude and longitude
                    lat = geo_data_map[school]['lat']
                    lon = geo_data_map[school]['lon']
                    
                    data.append((date_str, school, student_count, special_support_class_size, lat, lon))

        # Insert data (use INSERT OR IGNORE to avoid duplicates)
        cursor.execute("SELECT COUNT(*) FROM school_data_table")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT OR IGNORE INTO school_data_table (Date, School_Name, Student_Count, Special_Support_Class_Size, lat, lon) VALUES (?, ?, ?, ?, ?, ?)", data)
            st.success("Student count, special support class size, and latitude/longitude data have been added to the database.")
        else:
            st.info("School data already exists in the database. Skipped.")

        conn.commit()
        
    except sqlite3.Error as e:
        st.error(f"Database creation or data insertion error: {e}")
    finally:
        if conn:
            conn.close()

# --- Data Loading Function (from SQLite) ---
@st.cache_data
def load_data_from_sqlite(db_name='school_data.db'):
    conn = None
    df = pd.DataFrame()

    try:
        conn = sqlite3.connect(db_name) 
        
        # Get data from the integrated table
        query_school_data = "SELECT Date, School_Name, Student_Count, Special_Support_Class_Size, lat, lon FROM school_data_table"
        df = pd.read_sql_query(query_school_data, conn)
        
        # Convert 'Date' to datetime type (assuming 'YYYY-MM' format)
        df['Date'] = pd.to_datetime(df['Date']).dt.to_period('M').dt.to_timestamp()
        
    except sqlite3.Error as e:
        st.error(f"Error loading data from database: {e}")
        df = pd.DataFrame() 
    finally:
        if conn:
            conn.close()
    
    return df

# --- Main application processing ---
DB_NAME = 'school_data.db'

# Create and populate the database if the file doesn't exist or is empty
if not os.path.exists(DB_NAME) or os.path.getsize(DB_NAME) == 0:
    st.info(f"'{DB_NAME}' not found or is empty. Creating database and inserting data.")
    create_and_populate_db(DB_NAME)
else:
    st.info(f"'{DB_NAME}' exists. Using existing database.")

# Load data
df = load_data_from_sqlite(DB_NAME)

# --- 2. Streamlit UI ---
st.title('Kagoshima City Student Count Dashboard')
st.write('Move the month/year slider to see changes in student count and special support class size for each school!')

# Month/Year Slider
if df.empty:
    st.error("No data loaded. Please check if the database file and table exist.")
    st.stop() 

unique_months = sorted(df['Date'].unique())

if len(unique_months) == 0:
    st.error("No available month/year data. Please check the database data.")
    st.stop()
else:
    unique_dates = [pd.Timestamp(dt).to_pydatetime().date() for dt in unique_months]
    
    min_slider_date = unique_dates[0]
    max_slider_date = unique_dates[-1]
    default_slider_date = unique_dates[-1]

    selected_date_from_slider = st.slider(
        'Select Month/Year',
        min_value=min_slider_date,
        max_value=max_slider_date,
        value=default_slider_date,
    )

selected_date = pd.to_datetime(selected_date_from_slider)

st.subheader(f'Selected Month/Year: {selected_date.strftime("%Y年%m月")}')

st.markdown("---")

# --- 3. Map Display ---
st.subheader('Student Count Change on Map')

df_filtered = df[
    (df['Date'].dt.year == selected_date.year) & 
    (df['Date'].dt.month == selected_date.month)
].copy()

df_map = df_filtered[['School_Name', 'Student_Count', 'Special_Support_Class_Size', 'lat', 'lon']]


map_center = [31.5960, 130.5580]
m = folium.Map(location=map_center, zoom_start=12)

if not df_map.empty:
    min_students = df_map['Student_Count'].min()
    max_students = df_map['Student_Count'].max()

    for idx, row in df_map.iterrows():
        normalized_students = (row['Student_Count'] - min_students) / (max_students - min_students) if (max_students - min_students) > 0 else 0.5
        
        color_val_r = int(255 * (1 - normalized_students))
        color_val_g = int(255 * (1 - normalized_students))
        color_val_b = 255
        color_hex = f'#{color_val_r:02x}{color_val_g:02x}{color_val_b:02x}'

        radius = np.log(max(row['Student_Count'], 100) / 100) * 5 + 5
        radius = max(5, radius)

        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=radius,
            color=color_hex,
            fill=True,
            fill_color=color_hex,
            fill_opacity=0.7,
            tooltip=f"{row['School_Name']}: Student Count {row['Student_Count']} students, Special Support Class Size {row['Special_Support_Class_Size']} students"
        ).add_to(m)

folium_static(m)

st.markdown("---")

# --- 4. Student Count Trend Graph ---

st.subheader('Student Count Trend for Selected School')

df_total_students_over_time = df.groupby('Date')['Student_Count'].sum().reset_index()

fig_line_students = px.line(df_total_students_over_time, 
                   x='Date', 
                   y='Student_Count', 
                   title='Overall Student Count Trend in Kagoshima City')
fig_line_students.update_layout(xaxis_title="Month/Year", yaxis_title="Student Count", hovermode="x unified")
st.plotly_chart(fig_line_students, use_container_width=True)

if not df.empty:
    selected_school = st.selectbox('Select School for Details', df['School_Name'].unique())

    if selected_school:
        df_school_data = df[df['School_Name'] == selected_school].sort_values('Date')
        
        fig_bar_students = px.bar(df_school_data, 
                        x='Date', 
                        y='Student_Count', 
                        title=f'Student Count Trend for {selected_school}',
                        labels={'Date': 'Month/Year', 'Student_Count': 'Student Count'})
        fig_bar_students.update_layout(xaxis_title="Month/Year", yaxis_title="Student Count")
        st.plotly_chart(fig_bar_students, use_container_width=True)

        fig_bar_special = px.bar(df_school_data, 
                        x='Date', 
                        y='Special_Support_Class_Size', 
                        title=f'Special Support Class Size Trend for {selected_school}',
                        labels={'Date': 'Month/Year', 'Special_Support_Class_Size': 'Special Support Class Size'})
        fig_bar_special.update_layout(xaxis_title="Month/Year", yaxis_title="Special Support Class Size")
        st.plotly_chart(fig_bar_special, use_container_width=True)

else:
    st.info("No data available to display student count trend graphs.")
