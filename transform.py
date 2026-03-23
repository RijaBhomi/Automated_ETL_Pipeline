import pandas as pd
import logging
from datetime import datetime

# instead of using print statement everywhere, logger will be used to log the messages. This way we can control the level of logging and also redirect the logs to a file if needed.
logger= logging.getLogger(__name__) # create a logger for this module

AQI_LABELS= {1: "Good", 2:"Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}  # mapping of AQI index to labels

# health risk based on pm25 levels 
# this function takes pm25 value as float or None and returns a string representing the health risk level
# like if pm25=80, then output Very high
def classify_health_risk(pm25: float| None) -> str:
    if pm25 is None:
        return "Unknown"
    elif pm25 <=12:
        return "Low"
    elif pm25 <= 35.4:
        return "Moderate"
    elif pm25 <= 55.4:
        return "High"
    else:
        return "Very High"

# Transform data function
# combines weather data and air quality data into one record
def transform_data(weather_data: dict | None, aqi_data: dict | None) -> dict| None: 
    # if either fetch failed, skip this city
    if weather_data is None or aqi_data is None:
        logger.error("Missing weather or air quality data for transformation.")
        return None
    
    # merge both weather and air quality data into a single record with a timestamp
    try:
        record= {
            "city": weather_data["city"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": weather_data["temperature"],
            "humidity": weather_data["humidity"],
            "wind_speed": weather_data["wind_speed"],
            "weather_description": weather_data["weather_description"],
            "aqi": aqi_data["aqi"],
            "aqi_label": aqi_data["aqi_label"], 
            "pm25": aqi_data["pm25"],
            "pm10": aqi_data["pm10"],
            "health_risk": classify_health_risk(aqi_data["pm25"]) , # classify health risk based on pm25 levels
            "co": aqi_data["co"]
        }
        return record
    except KeyError as e:
        logger.error(f"Key error during transformation: {e}")
        return None

# Transform all record functions
# takes a list of weather data and a list of air quality data and returns a pandas DataFrame with all the transformed records    
def transform_all(weather_list: list, aqi_list: list) -> pd.DataFrame: 
    records= []   # list to store all transformed records

    # zip pairs items together like (Kathmandu, AQI1) and (Pokhara, AQI2) and so on, then transform each pair and add to records list
    for weather, aqi in zip(weather_list, aqi_list):
        record= transform_data(weather, aqi)     # calls the earlier function
        if record is not None:
            records.append(record)
    if not records:
        logger.error("No valid records to transform")
        return pd.DataFrame()  # return an empty DataFrame if no valid records
    
    df= pd.DataFrame(records)  # convert the list of records into a pandas DataFrame

    # drop any rows where critical fields are missing
    df.dropna(subset= ["city", "timestamp", "temperature", "aqi"], inplace= True)

    # round floats to 2 decimal places for cleaniness
    float_cols= ["temperature", "humidity", "wind_speed", "pm25", "pm10", "co"]
    df[float_cols]= df[float_cols].round(2)

    logger.info(f"Transformed {len(df)} records successfully.")
    return df

if __name__ == "__main__":
    # simulate what pipeline.py will pass in
    sample_weather = [
        {"city": "Kathmandu", "temperature": 18.12, "humidity": 63,
         "wind_speed": 7.2, "weather_description": "scattered clouds"},
        {"city": "Pokhara", "temperature": 22.5, "humidity": 70,
         "wind_speed": 3.1, "weather_description": "clear sky"},
        None,  # simulate a failed fetch
    ]
    sample_aqi = [
        {"city": "Kathmandu", "aqi": 5, "aqi_label": "Very Poor",
         "pm25": 80.81, "pm10": 87.07, "co": 672.42},
        {"city": "Pokhara", "aqi": 2, "aqi_label": "Fair",
         "pm25": 8.5, "pm10": 12.3, "co": 210.0},
        {"city": "Bhaktapur", "aqi": 5, "aqi_label": "Very Poor",
         "pm25": 86.82, "pm10": 95.59, "co": 737.25},
    ]

    df = transform_all(sample_weather, sample_aqi)
    print(df.to_string())
    print("\nColumns:", list(df.columns))
    print("Shape:", df.shape)
    print("Health risks:\n", df[["city", "pm25", "health_risk"]])