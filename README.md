# 🌿 Nepal Air Quality & Weather ETL Pipeline

> An automated data engineering pipeline that fetches live weather and air quality data for 10 Nepali cities every hour, stores it in a SQLite database, and serves an interactive dashboard with real-time analytics and AQI forecasting.

**🔴 Live Demo:** [automatedetlpipeline-ckijbgjzcegubycxnqsl2e.streamlit.app](https://automatedetlpipeline-ckijbgjzcegubycxnqsl2e.streamlit.app)

---

## What It Does

This project is a full end-to-end data pipeline — not just a notebook. Every hour it automatically:

1. **Extracts** live data from two public REST APIs (OpenWeatherMap + OpenAQ) for 10 Nepali cities
2. **Transforms** the raw JSON into clean, merged records with computed health risk classifications based on WHO PM2.5 guidelines
3. **Loads** the processed data into a local SQLite database with duplicate prevention
4. **Serves** everything through a Streamlit dashboard with maps, charts, and a 6-hour AQI forecast using Meta's Prophet model

---

## Architecture

```
OpenWeatherMap API ──┐
                     ├──▶ extract.py ──▶ transform.py ──▶ load.py ──▶ weather_air.db
OpenAQ API ──────────┘                                                      │
                                                                             │
pipeline.py (scheduler — runs every hour) ───────────────────────────────── ┘
                                                                             │
dashboard.py (Streamlit) ◀───────────────────────────────────────────────── ┘
forecast.py (Prophet + Linear forecasting)
```

---

## Features

### Pipeline
- Fetches data for **10 Nepali cities**: Kathmandu, Lalitpur, Bhaktapur, Pokhara, Biratnagar, Dharan, Janakpur, Birgunj, Nepalgunj, Dhangadhi
- Classifies **health risk** per reading (Low / Moderate / High / Very High) based on WHO PM2.5 thresholds
- Structured **logging** to `logs/pipeline.log` with timestamps for every run
- Automatic **duplicate prevention** — won't re-insert data if the pipeline runs twice at the same time
- Run once with `--once` flag or start the hourly scheduler

### Dashboard
- **KPI cards** — average AQI, PM2.5, temperature, humidity across all cities
- **Interactive map** — Nepal bubble map coloured by pollution level
- **Atmospheric trends** — 24h AQI line chart for top 5 most polluted cities
- **City rankings** — all 10 cities with latest readings and health risk badges
- **PM2.5 comparison** — horizontal bar chart with WHO reference line (15 µg/m³)
- **AQI forecast** — 6-hour prediction using both linear trend and Meta's Prophet model with 80% confidence intervals
- **Raw data table** — last 100 readings with colour-coded health risk

---

## Project Structure

```
etl_pipeline/
├── extract.py        # Fetches data from OpenWeatherMap and OpenAQ APIs
├── transform.py      # Cleans, merges, and classifies the raw data
├── load.py           # Saves to SQLite, reads back for dashboard
├── pipeline.py       # Orchestrator — runs ETL + hourly scheduler
├── dashboard.py      # Streamlit dashboard app
├── forecast.py       # Prophet and linear AQI forecasting
├── requirements.txt  # All dependencies
├── runtime.txt       # Python version pin for Streamlit Cloud
├── weather_air.db    # SQLite database (auto-created on first run)
├── logs/
│   └── pipeline.log  # Timestamped run history
└── .env              # API keys (never committed — see setup below)
```

---

## Setup & Installation

### 1. Clone the repo
```bash
git clone https://github.com/RijaBhomi/Automated_ETL_Pipeline.git
cd Automated_ETL_Pipeline
```

### 2. Create a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your API key

Create a `.env` file in the project root:
```
OPENWEATHER_API_KEY="your_key_here"
```

Get a free key at [openweathermap.org/api](https://openweathermap.org/api) — it activates in ~10 minutes.

---

## Usage

### Run the pipeline once (for testing)
```bash
python pipeline.py --once
```

### Start the hourly scheduler
```bash
python pipeline.py
```
This runs immediately, then repeats every hour. Press `Ctrl+C` to stop.

### Launch the dashboard
```bash
streamlit run dashboard.py
```
Opens at `http://localhost:8501`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data extraction | `requests`, OpenWeatherMap API, OpenAQ API |
| Transformation | `pandas`, `numpy` |
| Storage | `SQLite` via `SQLAlchemy` |
| Scheduling | `schedule` library |
| Dashboard | `Streamlit`, `Plotly` |
| Forecasting | `Prophet` (Meta), `numpy` linear regression |
| Deployment | Streamlit Cloud |
| Version control | Git + GitHub |

---

## Cities Tracked

| City | Province |
|---|---|
| Kathmandu | Bagmati |
| Lalitpur | Bagmati |
| Bhaktapur | Bagmati |
| Pokhara | Gandaki |
| Biratnagar | Koshi |
| Dharan | Koshi |
| Janakpur | Madhesh |
| Birgunj | Madhesh |
| Nepalgunj | Lumbini |
| Dhangadhi | Sudurpashchim |

---

## Health Risk Classification

Based on WHO PM2.5 guidelines (24hr average):

| PM2.5 (µg/m³) | Health Risk |
|---|---|
| 0 – 12 | Low |
| 12 – 35 | Moderate |
| 35 – 55 | High |
| 55+ | Very High |

WHO recommended limit: **15 µg/m³**

---

## AQI Scale (OpenWeatherMap)

| Index | Label |
|---|---|
| 1 | Good |
| 2 | Fair |
| 3 | Moderate |
| 4 | Poor |
| 5 | Very Poor |

---

## Deployment

The dashboard is deployed on [Streamlit Cloud](https://share.streamlit.io). To deploy your own fork:

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Set `dashboard.py` as the main file
4. Add your API key under **Advanced settings → Secrets**:
   ```
   OPENWEATHER_API_KEY = "your_key_here"
   ```
5. Click Deploy

---

## What I Learned

- Building a production-style ETL pipeline with proper separation of concerns (extract / transform / load)
- Designing a SQLite schema with duplicate prevention and structured logging
- Working with REST APIs and handling failures gracefully
- Time-series forecasting with Meta's Prophet library
- Deploying a live data application to Streamlit Cloud

---

## Author

**Rija Bhomi**
[GitHub](https://github.com/RijaBhomi) · [LinkedIn](https://linkedin.com/in/rijabhomi) · rijabhomi9@gmail.com

---

*Built with Python, Streamlit, and real data from Nepal 🇳🇵*