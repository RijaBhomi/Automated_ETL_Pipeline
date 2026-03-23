# load.py takes the dataframe from transform.py and saces it permanenetly into a SQLite database
# SQLite is database that lives as a single file 
# load.py does 3 things:
# 1. create a table first time it runs
# 2. insert new records into the table every time it runs
# 3. prevent duplicates so if the pipeline runs twice in the same minute it doesnt save the same data twice

import logging
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

logger= logging.getLogger(__name__) 

# path to the SQLite db file
# creates file automatically if it doesnt exist
DB_PATH= "weather_air.db"
DB_URL= f"sqlite:///{DB_PATH}"
# sqlite:/// is the format SQLAlchemy expects
# three slashes means relative path, so file appears in same project folder

def get_engine():
    # engine= the connection betwn python and DB
    # like a door to DB
    # echo= False means dont print all the SQL commands to console, keeps it clean
    return create_engine(DB_URL, echo= False)

def create_table_if_not_exists():
    # this runs every time the pipeline starts
    # "IF NOT EXISTS" means it only creates the table if it doesnt already exist, so it wont throw an error if the table is already there
    engine= get_engine()

    create_sql= """
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        temperature REAL,
        humidity REAL,
        wind_speed REAL,
        weather_description TEXT,
        aqi INTEGER,
        aqi_label TEXT,
        pm25 REAL,
        pm10 REAL,
        CO REAL,
        health_risk TEXT
    )
    """
    # AUTOINCREMENT = sqLITE auto-assigns an id 
    # REAL= decimal no.,TEXT= string, INTEGER= whole no.
    # NOT NULL= all fields required

    with engine.connect() as conn:
        # 'with' block automatically closes the connection when done
        conn.execute(text(create_sql))  # execute the SQL command to create the table
        conn.commit()  # commit the changes to the database
    logger.info("Table ready")

def is_duplicate(conn, city: str, timestamp:str) -> bool:
    # before saving a row, check if city + timestamp already exisits
    # this prevents duplicates if pipeline runs twice quickly
    # COUNT(*) returns how many matching rows exist, if >0 then its a duplicate
    result= conn.execute(
        text("""
             SELECT COUNT(*) FROM readings
             WHERE city= :city AND timestamp= :timestamp
        """), 
        {"city": city, "timestamp": timestamp}
        # :city and :timestamp are placeholders in the SQL query, and we pass the actual values as a dictionary in the second argument to execute() to prevent SQL injection
    )
    return result.scalar()>0
# scalar() gets the single value returned by COUNT(*)
# if >0 duplicate exists, so return true

def save_to_db(df: pd.DataFrame) ->int:
    # takes cleaned df from transform.py
    # saves each row into DB
    # returns how many rows were actually saved

    if df.empty:
        logger.warning("Empty DataFrame, nothing to save.")
        return 0
    
    create_table_if_not_exists()
    engine= get_engine()
    saved= 0

    with engine.connect() as conn:
        for _, row in df.iterrows():
            # iterrows() loops through each row in df
            # _ is the index, row is actual data 

            if is_duplicate(conn, row["city"], row["timestamp"]):
                logger.info(f"Skipping duplicate: {row['city']} at {row['timestamp']}")
                continue # skip this row and move to next city

            # INSERT INTO is SQL for adding a new row to the table
            # :column_name are placeholders filled by row.to_dict() to prevent SQL injection
            conn.execute(text("""
                INSERT INTO readings
                    (city, timestamp, temperature, humidity, wind_speed,
                     weather_description, aqi, aqi_label, pm25, pm10, co, health_risk)
                VALUES
                    (:city, :timestamp, :temperature, :humidity, :wind_speed,
                     :weather_description, :aqi, :aqi_label, :pm25, :pm10, :co, :health_risk)
            """), row.to_dict())
            # row.to_dict() converts the row into a dict like
            # {"city": "Kathmandu", "timestamp": "2024-06-01 12:00:00", "temperature": 25.5, ...}
            # this dict is used to fill the placeholders in the SQL querys

            saved +=1
        conn.commit() # commit all the inserts to the database at once for better performance

    logger.info(f"Saved {saved} new records to the database.")
    return saved

def read_from_db() -> pd.DataFrame:
    # this is what dashboard.py will call to get all stored data
    # ORDER BY timestamp DESC = newest data first

    create_table_if_not_exists()
    engine= get_engine()
    with engine.connect() as conn:
        df= pd.read_sql(
            "SELECT * FROM readings ORDER BY timestamp DESC",
            conn
        )
    return df

if __name__ == "__main__":
    # testing with hardcoded data
    sample_data = {
        "city":         ["Kathmandu", "Pokhara"],
        "timestamp":    [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * 2,
        "temperature":  [18.12, 22.5],
        "humidity":     [63.0, 70.0],
        "wind_speed":   [7.2, 3.1],
        "weather_description": ["scattered clouds", "clear sky"],
        "aqi":          [5, 2],
        "aqi_label":    ["Very Poor", "Fair"],
        "pm25":         [80.81, 8.5],
        "pm10":         [87.07, 12.3],
        "co":           [672.42, 210.0],
        "health_risk":  ["Very High", "Low"],
    }

    df=pd.DataFrame(sample_data)

    print("---Test 1: saving to database---")
    saved= save_to_db(df)
    print(f"Saved {saved} records to the database.")

    print("\n---Test 2: reading from database---")
    result= read_from_db()
    print(result.to_string())
    print(f"Total records in database: {len(result)}")

    print("\n---Test 3: checking duplicate prevention---")
    saved_again= save_to_db(df)  # trying to save the same data again
    print(f"Saved {saved_again} records (should be 0- all duplicates)")