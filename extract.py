import requests   # makes HTTPS calls to APIs
import logging    # python's built-in way to print status msg
import os         # reads environment variables from .env file
from dotenv import load_dotenv


# loading API key
load_dotenv()
API_KEY= os.getenv("OPENWEATHER_API_KEY")

cities= ['Kathmandu', 'Lalitpur', 'Bhaktapur', 'Pokhara', 'Biratnagar', 'Dharan', 'Janakpur', 'Birgunj', 'Nepalgunj', 'Dhangadhi']

# fetch_weather - takes city name as input and returns weather data
def fetch_weather(city: str) -> dict | None:   #takes city name as string and returns dict of weather data or None if something goes wrong
    url= "https://api.openweathermap.org/data/2.5/weather"
    params= {
        "q": city,         # city name
        "appid": API_KEY,  # API key for authentication
        "units": "metric"  # to get temperature in Celsius
    }

    try:
        response= requests.get(url, params=params, timeout= 10)  # make the API call
        response.raise_for_status() # raise an error if the API call fails
        data= response.json()  # parse the JSON response

        return {
                "city": city,
                "temperature": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "weather_description": data["weather"][0]["description"]
            }
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching weather data for {city}: {e}")
        return None

# fetch_air_quality - takes city name as input and returns air quality data
def fetch_air_quality(city: str) -> dict | None:
    geo_url= "https://api.openweathermap.org/data/2.5/weather"
    params= {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }
    
    try:
        geo_response= requests.get(geo_url, params=params, timeout= 10)  # make the API call to get the coordinates of the city
        geo_response.raise_for_status()   # raise an error if the API call fails
        geo_data= geo_response.json()     # parse the JSON response to get the coordinates of the city
        lat= geo_data['coord']['lat']     # extract latitude from the response
        lon= geo_data['coord']['lon']     # extract longitude from the response

        aqi_url= "https://api.openweathermap.org/data/2.5/air_pollution"
        aqi_params= {"lat": lat, "lon": lon, "appid": API_KEY}  # parameters for the air quality API call

        aqi_response= requests.get(aqi_url, params=aqi_params, timeout= 10)  # make the API call to get the air quality data
        aqi_response.raise_for_status()  # raise an error if the API call fails
        aqi_data= aqi_response.json()    # parse the JSON response to get the air quality data  

        components= aqi_data['list'][0]['components']  # extract the components of the air quality data
        aqi_index= aqi_data['list'][0]['main']['aqi']  # extract the air quality index from the response

        aqi_labels= {1: "Good", 2:"Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}  # mapping of AQI index to labels

        return{
            "city": city,
            "aqi": aqi_index,
            "aqi_label": aqi_labels.get(aqi_index, "Unknown"),
            "pm25": components.get("pm2_5"),
            "pm10": components.get("pm10"),
            "co": components.get("co"),
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching air quality data for {city}: {e}")
        return None 
    
if __name__ == "__main__":
    print("Testing extract for Kathmandu")

    weather= fetch_weather("Bhaktapur")
    print("Weather data:", weather)

    air_quality= fetch_air_quality("Bhaktapur")
    print("Air quality data:", air_quality)
