# pipeline.py- imports all three stages of ETL pipeline in correct order for every city in lisy
# its like a manager telling each worker what to do and when
# also adds 2 things: 
# logging to a file so record of every run is saved in logs  
# and scheduler so it runs automatically every hours

# HOW THE FLOW WORKS:
# 1. for each city in cities list, fetch weather and air quality data using extract.py functions
# 2. transform the data using transform.py functions and create df
# 3. load the df into SQLite database using load.py functions

import logging
import os
import schedule
import time
from datetime import datetime

# import functions from other modules
from extract import fetch_weather, fetch_air_quality, cities
from transform import transform_all
from load import save_to_db, read_from_db

# logging setup
# logging writes msg both to console and to a log file
# this means u have a permanent record of pipeline run even after u close terminal

os.makedirs("logs", exist_ok=True)  # create logs folder if it doesnt exist
logging.basicConfig(
    level= logging.INFO,
    # INFO means log everything from INFO level or above
    # levels in order: DEBUG -> INFO -> WARNING -> ERROR -> CRITICAL

    format= "%(asctime)s | %(levelname)s | %(message)s", 
    # asctime= timestamp of log, levelname= log level, message= log message
    # eg: 2024-06-01 12:00:00 | INFO | Pipeline started

    handlers= [
        logging.FileHandler("logs/pipeline.log"),  # write logs to file
        logging.StreamHandler()  # also print logs to console
    ]
)
logger= logging.getLogger(__name__)  # create a logger for this module

# core pipeline function
def run_pipeline():
    # this is the main function that gets called every hour
    # it runs the full extract -> transform -> load process for all cities

    logger.info("=" * 50)  # print a separator line in logs for better readability
    logger.info(f"Pipeline started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Fetching data for {len(cities)} cities: {cities}")

    # ── EXTRACT ────────────────────────────────────────────────
    # fetch weather and AQI for every city
    # we collect results into two lists, one per API
    weather_list = []
    aqi_list = []

    for city in cities:
        logger.info(f"Fetching data for {city}...")

        weather = fetch_weather(city)
        # returns a dict if successful, None if API call failed
        aqi = fetch_air_quality(city)

        weather_list.append(weather)
        aqi_list.append(aqi)
        # we append even if None — transform_all handles skipping None values

    logger.info(f"Extract complete: {len(cities)} cities attempted")

    # ── TRANSFORM ──────────────────────────────────────────────
    # merge weather + AQI lists into one clean DataFrame
    # any city where either fetch returned None gets skipped here
    df = transform_all(weather_list, aqi_list)

    if df.empty:
        # if ALL cities failed (e.g. no internet) stop here
        logger.error("Transform returned empty DataFrame — skipping load")
        return

    logger.info(f"Transform complete: {len(df)} valid records")

    # ── LOAD ───────────────────────────────────────────────────
    # save the DataFrame to SQLite
    saved = save_to_db(df)
    logger.info(f"Load complete: {saved} new records saved to database")

    # ── SUMMARY ────────────────────────────────────────────────
    # read back total records so you can see the DB growing over time
    all_data = read_from_db()
    logger.info(f"Database now has {len(all_data)} total records")
    logger.info("Pipeline finished successfully")
    logger.info("=" * 50)


# ── scheduler setup ────────────────────────────────────────────
def start_scheduler():
    # schedule the pipeline to run every hour automatically
    schedule.every(1).hours.do(run_pipeline)
    # other options you could use instead:
    # schedule.every(30).minutes.do(run_pipeline)
    # schedule.every().day.at("08:00").do(run_pipeline)

    logger.info("Scheduler started — pipeline will run every 1 hour")
    logger.info("Running pipeline once immediately on startup...")

    run_pipeline()
    # run once immediately when you start it
    # so you don't have to wait an hour for the first data

    while True:
        # infinite loop that keeps the scheduler alive
        schedule.run_pending()
        # run_pending() checks — is there a job due to run right now?
        # if yes it runs it, if no it does nothing

        time.sleep(60)
        # sleep for 60 seconds before checking again
        # this prevents the loop from eating 100% of your CPU


# ── entry point ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # if you run: python pipeline.py --once
        # it runs the pipeline exactly one time and exits
        # useful for testing without starting the scheduler
        logger.info("Running pipeline once (--once flag detected)")
        run_pipeline()
    else:
        # if you run: python pipeline.py
        # it starts the scheduler and runs forever
        start_scheduler()
