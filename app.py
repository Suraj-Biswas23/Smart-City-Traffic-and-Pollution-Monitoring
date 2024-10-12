import streamlit as st
import requests
import folium
import os
from streamlit_folium import folium_static
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import plotly.graph_objects as go
from datetime import datetime, timedelta
from statsmodels.tsa.arima.model import ARIMA
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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

# New function to fetch weather data
def get_weather_data(city):
    api_key = OPENWEATHERMAP_API_KEY
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url).json()
    
    if response.get('cod') == 200:
        weather_data = {
            'temperature': response['main']['temp'],
            'humidity': response['main']['humidity'],
            'description': response['weather'][0]['description'],
            'icon': response['weather'][0]['icon']
        }
        return weather_data
    else:
        st.error("Failed to fetch weather data.")
        return None

# Function to forecast AQI using ARIMA
def forecast_aqi(historical_data):
    if historical_data.empty:
        return pd.DataFrame()
    
    model = ARIMA(historical_data['aqi'], order=(1,1,1))
    results = model.fit()
    
    forecast = results.forecast(steps=7)
    forecast_df = pd.DataFrame({'timestamp': pd.date_range(start=historical_data['timestamp'].iloc[-1] + timedelta(days=1), periods=7),
                                'aqi': forecast})
    return forecast_df

def create_aqi_gauge(aqi_value):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=aqi_value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Air Quality Index"},
        gauge={
            'axis': {'range': [None, 500]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "green"},
                {'range': [51, 100], 'color': "yellow"},
                {'range': [101, 150], 'color': "orange"},
                {'range': [151, 200], 'color': "red"},
                {'range': [201, 300], 'color': "purple"},
                {'range': [301, 500], 'color': "maroon"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': aqi_value
            }
        }
    ))
    fig.update_layout(height=300)
    return fig

def create_pollution_radar(components):
    categories = list(components.keys())
    values = list(components.values())
    
    fig = go.Figure(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=False,
        height=300,
        title=""
    )
    return fig

# Set page config
st.set_page_config(layout="wide", page_title="Smart City Dashboard")

# Update the custom CSS
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
    .footer {
        margin-top: 2rem;
        padding: 1.5rem 0;
        background-color: #f8f9fa;
        border-top: 1px solid #e0e0e0;
        font-size: 0.9em;
        color: #333;
    }
    .footer-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
    }
    .footer-section {
        margin: 0.5rem 1rem;
    }
    .footer-title {
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .footer-item {
        margin-bottom: 0.25rem;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar content
st.sidebar.title("Smart City Dashboard")
st.sidebar.markdown("Monitor real-time traffic, pollution, and weather data for major Indian cities.")

# City selection
indian_cities = ["Delhi", "Mumbai", "Bangalore", "Kolkata", "Chennai", "Hyderabad", "Ahmedabad", "Pune", "Jaipur", "Lucknow"]
city = st.sidebar.selectbox("Select a City", indian_cities)

# Fetch data for the selected city
current_aqi, historical_aqi_df = get_historical_aqi(city)
components, lat, lon = get_pollution_data(city)
weather_data = get_weather_data(city)

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
st.title("Smart City Traffic, Pollution, and Weather Monitoring")

if lat is not None and lon is not None:
    # Create two columns for the main content
    col1, col2 = st.columns([3, 2])

    with col1:
        # Display Map
        st.markdown("### City Map")
        m = folium.Map(location=[lat, lon], zoom_start=12)
        folium.Marker(
            location=[lat, lon],
            popup=f"AQI: {current_aqi}",
            icon=folium.Icon(color='red' if current_aqi > 100 else 'green')
        ).add_to(m)
        st.components.v1.html(folium.Figure().add_child(m).render(), height=400)

        # Add AQI Gauge
        st.markdown("### Air Quality Index (AQI) Gauge")
        aqi_gauge = create_aqi_gauge(current_aqi)
        st.plotly_chart(aqi_gauge, use_container_width=True)
        
        # Add Pollution Radar Chart
        if components:
            st.markdown("### Pollutants Concentration Radar")
            pollution_radar = create_pollution_radar(components)
            st.plotly_chart(pollution_radar, use_container_width=True)
            

    with col2:
        # Display Current AQI
        st.markdown("### Air Quality Index (AQI)")
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

        # Display Weather Information
        st.markdown("### Weather Information")
        if weather_data:
            st.markdown(f"""
                <div class="stCard">
                    <span class="metric-label">Temperature</span><br>
                    <span class="metric-value">{weather_data['temperature']}°C</span>
                </div>
                <div class="stCard">
                    <span class="metric-label">Humidity</span><br>
                    <span class="metric-value">{weather_data['humidity']}%</span>
                </div>
                <div class="stCard">
                    <span class="metric-label">Weather</span><br>
                    <span class="metric-value">{weather_data['description'].capitalize()}</span>
                    <img src="http://openweathermap.org/img/w/{weather_data['icon']}.png" alt="Weather icon">
                </div>
            """, unsafe_allow_html=True)
        else:
            st.write("Weather data not available.")

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

    # Display Historical AQI Trend and Forecast
    st.markdown("### Historical AQI Trend and Forecast")
    if historical_aqi_df is not None and not historical_aqi_df.empty:
        historical_aqi_df['timestamp'] = pd.to_datetime(historical_aqi_df['timestamp'])
        
        # Generate AQI forecast
        forecast_df = forecast_aqi(historical_aqi_df)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=historical_aqi_df['timestamp'],
            y=historical_aqi_df['aqi'],
            mode='lines+markers',
            name='Historical AQI'
        ))
        
        fig.add_trace(go.Scatter(
            x=forecast_df['timestamp'],
            y=forecast_df['aqi'],
            mode='lines+markers',
            name='AQI Forecast',
            line=dict(dash='dash')
        ))
        
        fig.update_layout(
            title=f"Historical and Forecasted PM2.5 AQI Trend for {city}",
            xaxis_title="Date",
            yaxis_title="AQI (PM2.5)",
            legend_title="Data Type",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("Historical AQI data not available.")

else:
    st.error("Unable to fetch data for the selected city. Please try again later.")

# Footer with data sources and last update time
st.markdown("""
    <div class="footer">
        <div class="footer-content">
            <div class="footer-section">
                <div class="footer-title">Data Sources</div>
                <div class="footer-item">OpenWeatherMap API</div>
                <div class="footer-item">World Air Quality Index Project</div>
                <div class="footer-item">OpenRouteService API</div>
            </div>
            <div class="footer-section">
                <div class="footer-title">Last Updated</div>
                <div class="footer-item">{}</div>
            </div>
            <div class="footer-section">
                <div class="footer-title">About</div>
                <div class="footer-item">Smart City Dashboard v1.0</div>
                <div class="footer-item">© 2024 Suraj Biswas</div>
            </div>
        </div>
    </div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)

# Run the Streamlit app
if __name__ == "__main__":
    st.write("")