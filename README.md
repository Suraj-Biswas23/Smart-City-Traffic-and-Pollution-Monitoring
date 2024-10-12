# Smart City Dashboard

This project is a Smart City Traffic, Pollution, and Weather Monitoring Dashboard that provides real-time data for major Indian cities. It integrates traffic information, air quality index (AQI), pollutants concentration, and weather data using APIs like OpenWeatherMap, OpenRouteService, and World Air Quality Index (WAQI).

## Features

- Real-Time Air Quality Index (AQI): Displays the current AQI for the selected city.
- Pollutants Concentration Radar: A radar chart showcasing the levels of pollutants like PM2.5, PM10, CO, and more.
- Traffic Data: Provides traffic congestion data based on real-time traffic information.
- Weather Information: Shows the current weather data (temperature, humidity, weather conditions).
- Historical AQI Trend and Forecast: Displays the historical AQI trends and predicts future AQI values using ARIMA forecasting.
- Interactive Maps: Uses Folium maps to display the city location with AQI markers.

# Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Suraj-Biswas23/Smart-City-Traffic-and-Pollution-Monitoring.git
   ```

2. **Install required libraries: Make sure you have Python installed. Then, install the dependencies:**

  ```bash
  pip install -r requirements.txt
  ```

3. **Set up API Keys: Create a .env file in the project root directory with the following structure:**

  ```bash
  OPENWEATHERMAP_API_KEY=your_openweathermap_api_key
  OPENROUTESERVICE_API_KEY=your_openrouteservice_api_key
  WAQI_API_TOKEN=your_waqi_api_token
  ```

You can obtain the API keys from:

- OpenWeatherMap
- OpenRouteService
- World Air Quality Index (WAQI)

4. **Run the Streamlit app: Start the application using the following command:**

  ```bash
  streamlit run app.py
  ```
Open your browser at http://localhost:8501 to view the dashboard.

## Project Overview

The Smart City Dashboard provides a comprehensive real-time monitoring system that helps users stay updated on air quality, traffic conditions, and weather in their selected city. By combining data from various sources and presenting them in an interactive way, it offers valuable insights for better city management and environmental awareness.

## Tech Stack

- Python: The core language for developing the backend logic.
- Streamlit: Used for creating the interactive dashboard.
- Plotly: For generating graphs and charts (AQI trends, radar charts).
- Folium: For generating the map interface.
- OpenWeatherMap API: For retrieving weather and air pollution data.
- OpenRouteService API: For real-time traffic information.
- WAQI API: For historical and forecasted AQI data.
