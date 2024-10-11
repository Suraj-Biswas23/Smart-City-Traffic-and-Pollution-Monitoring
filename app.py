import streamlit as st
import requests
import folium
import os
from streamlit_folium import folium_static
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import plotly.graph_objects as go

# Load environment variables from .env file
load_dotenv()

# Function to get API keys, with fallback to Streamlit secrets for deployment
def get_api_key(key_name):
    return os.getenv(key_name) or st.secrets.get("api_keys", {}).get(key_name)

# Use these lines to get your API keys
OPENWEATHERMAP_API_KEY = get_api_key("OPENWEATHERMAP_API_KEY")
OPENROUTESERVICE_API_KEY = get_api_key("OPENROUTESERVICE_API_KEY")
WAQI_API_TOKEN = get_api_key("WAQI_API_TOKEN")

# Function to fetch pollution data
def get_pollution_data(city):
    api_key = OPENWEATHERMAP_API_KEY
    
    # Get latitude and longitude for the city
    city_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
    city_response = requests.get(city_url).json()
    
    # Check if the city_response contains 'coord' (i.e., valid data)
    if 'coord' in city_response:
        lat = city_response['coord']['lat']
        lon = city_response['coord']['lon']

        # Get air pollution data using latitude and longitude
        pollution_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"
        pollution_response = requests.get(pollution_url).json()

        if 'list' in pollution_response and pollution_response['list']:
            components = pollution_response['list'][0]['components']  # Contains pollutants (PM2.5, PM10, CO, etc.)
            return components, lat, lon
        else:
            st.error("Pollution data not available for the selected city.")
            return None, None, None
    else:
        st.error("City not found or invalid API key.")
        return None, None, None

def get_traffic_data(lat, lon):
    ors_api_key = OPENROUTESERVICE_API_KEY
    origin = f"{lon},{lat}"  # Note: ORS expects (lon, lat) format
    destination = f"{lon + 0.01},{lat + 0.01}"  # Slightly different destination for demonstration

    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    params = {
        'api_key': ors_api_key,
        'start': origin,
        'end': destination
    }
    
    try:
        response = requests.get(url, params=params).json()
        
        if 'features' in response and response['features']:
            properties = response['features'][0]['properties']
            summary = properties['summary']
            
            duration = summary['duration']  # Duration in seconds
            distance = summary['distance']  # Distance in meters
            
            # Calculate expected duration based on average speed of 50 km/h
            expected_duration = (distance / 1000) / 50 * 3600  # Convert to seconds
            
            congestion_percentage = (duration - expected_duration) / expected_duration * 100
            
            return {
                'duration': duration,
                'distance': distance,
                'expected_duration': expected_duration,
                'congestion': congestion_percentage
            }
        else:
            st.error("No route found in the API response.")
            return None
    except Exception as e:
        st.error(f"Failed to retrieve traffic data: {str(e)}")
        return None

# Function to fetch historical AQI data from WAQI API
def get_historical_aqi(city):
    token = WAQI_API_TOKEN
    url = f"https://api.waqi.info/feed/{city}/?token={token}"
    response = requests.get(url).json()
    
    if response['status'] == 'ok':
        current_aqi = response['data']['aqi']  # Current AQI
        historical_data = response['data']['forecast']['daily']['pm25']  # Adjusted to get daily PM2.5 data
        
        aqi_data = []
        for entry in historical_data:
            timestamp = entry['day']  # This will be the date string
            aqi_value = entry['avg']  # Average PM2.5 for the day
            aqi_data.append({'timestamp': timestamp, 'aqi': aqi_value})
        
        # Return both current AQI and historical AQI data as a DataFrame
        return current_aqi, pd.DataFrame(aqi_data)
    else:
        st.error("Failed to fetch historical AQI data.")
        return None, pd.DataFrame()  # Return None for current AQI and empty DataFrame

# Set page config
st.set_page_config(layout="wide", page_title="Smart City Dashboard")

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem 3rem;
    }
    .stCard {
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #3498db;
    }
    .metric-label {
        font-size: 1rem;
        color: #7f8c8d;
    }
    .sidebar .stRadio > label {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .sidebar .stRadio > label:hover {
        background-color: #e0e0e0;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar content
st.sidebar.title("Smart City Dashboard")
st.sidebar.markdown("Monitor real-time traffic and pollution data for major Indian cities.")

# City selection
indian_cities = ["Delhi", "Mumbai", "Bangalore", "Kolkata", "Chennai", "Hyderabad", "Ahmedabad", "Pune", "Jaipur", "Lucknow"]
city = st.sidebar.selectbox("Select a City", indian_cities)

# Fetch data for the selected city
current_aqi, historical_aqi_df = get_historical_aqi(city)
components, lat, lon = get_pollution_data(city)

# Display key statistics in the sidebar
st.sidebar.markdown("### Key Statistics")
if current_aqi is not None:
    st.sidebar.metric("Current AQI", current_aqi, delta=None)

if components:
    pm25 = components.get('pm2_5', 'N/A')
    st.sidebar.metric("PM2.5 Level", f"{pm25} μg/m³", delta=None)

# Add a mini chart to the sidebar
if historical_aqi_df is not None and not historical_aqi_df.empty:
    st.sidebar.markdown("### AQI Trend (Last 7 Days)")
    historical_aqi_df['timestamp'] = pd.to_datetime(historical_aqi_df['timestamp'])
    last_7_days = historical_aqi_df.iloc[-7:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=last_7_days['timestamp'], y=last_7_days['aqi'], mode='lines+markers'))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=200,
        xaxis_title="",
        yaxis_title="AQI"
    )
    st.sidebar.plotly_chart(fig, use_container_width=True)

# Add information about AQI levels
st.sidebar.markdown("### AQI Levels")
aqi_levels = {
    "Good (0-50)": "Air quality is satisfactory, and air pollution poses little or no risk.",
    "Moderate (51-100)": "Air quality is acceptable. However, there may be a risk for some people.",
    "Unhealthy for Sensitive Groups (101-150)": "Members of sensitive groups may experience health effects.",
    "Unhealthy (151-200)": "Everyone may begin to experience health effects.",
    "Very Unhealthy (201-300)": "Health alert: The risk of health effects is increased for everyone.",
    "Hazardous (301+)": "Health warning of emergency conditions. The entire population is likely to be affected."
}

selected_level = st.sidebar.radio("AQI Information", list(aqi_levels.keys()))
st.sidebar.info(aqi_levels[selected_level])

# Main content
st.title("Smart City Traffic and Pollution Monitoring")

if lat is not None and lon is not None:
    # Create two columns for layout
    col1, col2 = st.columns(2)

    with col1:
        # Display Current AQI
        st.markdown(f"### Air Quality Index (AQI)")
        aqi_color = 'red' if current_aqi > 100 else 'green'
        st.markdown(f"""
            <div class="stCard">
                <span class="metric-label">Current AQI</span><br>
                <span class="metric-value" style="color: {aqi_color};">{current_aqi}</span>
            </div>
        """, unsafe_allow_html=True)

        # Display Traffic Information
        st.markdown("### Traffic Information")
        traffic_info = get_traffic_data(lat, lon)
        if traffic_info:
            st.markdown(f"""
                <div class="stCard">
                    <span class="metric-label">Traffic Duration</span><br>
                    <span class="metric-value">{traffic_info['duration']:.2f} s</span>
                </div>
                <div class="stCard">
                    <span class="metric-label">Expected Duration (no traffic)</span><br>
                    <span class="metric-value">{traffic_info['expected_duration']:.2f} s</span>
                </div>
                <div class="stCard">
                    <span class="metric-label">Estimated Congestion</span><br>
                    <span class="metric-value">{traffic_info['congestion']:.2f}%</span>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.write("Traffic data not available.")

    with col2:
        # Display Map
        st.markdown("### City Map")
        m = folium.Map(location=[lat, lon], zoom_start=12)
        folium.Marker(
            location=[lat, lon],
            popup=f"AQI: {current_aqi}",
            icon=folium.Icon(color='red' if current_aqi > 100 else 'green')
        ).add_to(m)
        folium_static(m)

    # Display Pollution Information
    st.markdown("### Pollutants Concentration")
    if components:
        fig = px.bar(
            x=list(components.keys()),
            y=list(components.values()),
            labels={'x': 'Pollutants', 'y': 'Concentration (μg/m³)'},
            title='Concentration of Pollutants in Air'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # Display Historical AQI Trend
    st.markdown("### Historical AQI Trend")
    if historical_aqi_df is not None and not historical_aqi_df.empty:
        historical_aqi_df['timestamp'] = pd.to_datetime(historical_aqi_df['timestamp'])
        fig = px.line(
            historical_aqi_df,
            x='timestamp',
            y='aqi',
            title=f"Historical PM2.5 AQI Trend for {city}",
            labels={'timestamp': 'Date', 'aqi': 'AQI (PM2.5)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("Historical AQI data not available.")
else:
    st.error("Unable to fetch data for the selected city. Please try again later.")