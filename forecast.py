import pandas as pd
import numpy as np
import plotly.graph_objects as go
from load import read_from_db
import logging

logger = logging.getLogger(__name__)

# how many hours ahead to forecast
FORECAST_HOURS = 6


# ── APPROACH A: Linear Trend ───────────────────────────────────
# fits a straight line through recent readings and extends forward
# works with as few as 3 data points
# good for showing short-term direction

def linear_forecast(city_df: pd.DataFrame, city: str) -> go.Figure:
    # sort by time and take last 15 readings for this city
    city_df = city_df.sort_values("timestamp").tail(15).copy()

    if len(city_df) < 3:
        # not enough data to fit a line
        return None

    # convert timestamps to numbers (hours since first reading)
    # numpy can't work with datetime objects directly
    t0 = city_df["timestamp"].iloc[0]
    city_df["hours"] = (city_df["timestamp"] - t0).dt.total_seconds() / 3600

    x = city_df["hours"].values
    y = city_df["aqi"].values

    # np.polyfit fits a polynomial — degree 1 = straight line
    # returns [slope, intercept] of best fit line
    coeffs = np.polyfit(x, y, deg=1)
    slope, intercept = coeffs

    # generate future time points (every hour for FORECAST_HOURS)
    last_hour = x[-1]
    future_hours = np.arange(last_hour + 1, last_hour + FORECAST_HOURS + 1)

    # apply the line equation: y = slope * x + intercept
    future_aqi = slope * future_hours + intercept

    # clip to valid AQI range 1-5 (can't go below 1 or above 5)
    future_aqi = np.clip(future_aqi, 1, 5)

    # convert future hours back to real timestamps for the x axis
    future_timestamps = [
        t0 + pd.Timedelta(hours=float(h))
        for h in future_hours
    ]

    # ── build the plotly chart ──────────────────────────────────
    fig = go.Figure()

    # actual historical data — solid line
    fig.add_trace(go.Scatter(
        x=city_df["timestamp"],
        y=city_df["aqi"],
        mode="lines+markers",
        name="Historical AQI",
        line=dict(color="#4ade80", width=2),
        marker=dict(size=6, color="#4ade80"),
    ))

    # forecast line — dashed
    fig.add_trace(go.Scatter(
        x=future_timestamps,
        y=future_aqi,
        mode="lines+markers",
        name=f"Linear forecast (+{FORECAST_HOURS}h)",
        line=dict(color="#fb923c", width=2, dash="dash"),
        marker=dict(size=6, color="#fb923c", symbol="diamond"),
    ))

    # vertical line at the boundary between history and forecast
    # vertical line using a scatter trace instead
    now_x = city_df["timestamp"].iloc[-1]
    fig.add_trace(go.Scatter(
        x=[now_x, now_x],
        y=[0, 6],
        mode="lines",
        line=dict(color="#6b9e7e", width=1, dash="dot"),
        name="Now",
        showlegend=False,
        hoverinfo="skip"
    ))

    fig.update_layout(
        title=dict(
            text=f"{city} — Linear AQI Trend Forecast",
            font=dict(color="#e2f5e9", size=15)
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(22,36,25,0.8)",
        font_color="#6b9e7e",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(
            range=[0, 6], gridcolor="#1e3a28",
            tickvals=[1, 2, 3, 4, 5],
            ticktext=["Good", "Fair", "Moderate", "Poor", "Very Poor"],
            tickfont=dict(color="#6b9e7e")
        ),
        xaxis=dict(gridcolor="#1e3a28", tickfont=dict(color="#6b9e7e")),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2f5e9", size=11)
        ),
        hovermode="x unified"
    )

    return fig


# ── APPROACH B: Prophet Forecast ──────────────────────────────
# Meta's open source time series forecasting library
# finds patterns in your data and projects them forward
# gives confidence intervals (shaded area = uncertainty range)

def prophet_forecast(city_df: pd.DataFrame, city: str) -> go.Figure:
    try:
        from prophet import Prophet
    except ImportError:
        logger.error("Prophet not installed. Run: pip install prophet")
        return None

    city_df = city_df.sort_values("timestamp").copy()

    if len(city_df) < 5:
        # prophet needs at least 5 data points
        logger.warning(f"Not enough data for Prophet forecast for {city}")
        return None

    # prophet requires exactly two columns named 'ds' and 'y'
    # ds = datestamp, y = the value to forecast
    prophet_df = pd.DataFrame({
        "ds": city_df["timestamp"],
        "y":  city_df["aqi"].clip(1, 5)
        # clip keeps values in valid AQI range during training
    })

    # create and fit the model
    # daily_seasonality=True means it looks for patterns within a day
    # yearly_seasonality=False because we don't have a year of data
    model = Prophet(
        daily_seasonality=True,
        weekly_seasonality=False,
        yearly_seasonality=False,
        changepoint_prior_scale=0.3,
        # changepoint_prior_scale controls how flexible the trend is
        # 0.3 = medium flexibility, won't overfit to noise
        interval_width=0.80,
        # 80% confidence interval — shaded area means
        # "we're 80% sure the real value will be in this band"
        seasonality_mode="additive"
    )

    # suppress prophet's verbose logging so it doesn't spam console
    import logging as _logging
    _logging.getLogger("prophet").setLevel(_logging.WARNING)
    _logging.getLogger("cmdstanpy").setLevel(_logging.WARNING)

    model.fit(prophet_df)

    # create future dataframe — hourly intervals for next 6 hours
    future = model.make_future_dataframe(
        periods=FORECAST_HOURS,
        freq="h",
        include_history=True
        # include_history=True means chart shows both past fit + future
    )

    # generate predictions
    forecast = model.predict(future)

    # clip forecasted values to valid range
    forecast["yhat"]       = forecast["yhat"].clip(1, 5)
    forecast["yhat_lower"] = forecast["yhat_lower"].clip(1, 5)
    forecast["yhat_upper"] = forecast["yhat_upper"].clip(1, 5)

    # split into historical fit and future forecast
    cutoff   = prophet_df["ds"].max()
    hist_fc  = forecast[forecast["ds"] <= cutoff]
    future_fc = forecast[forecast["ds"] > cutoff]

    # ── build the plotly chart ──────────────────────────────────
    fig = go.Figure()

    # confidence interval band for future — filled area
    fig.add_trace(go.Scatter(
        x=pd.concat([future_fc["ds"], future_fc["ds"].iloc[::-1]]),
        y=pd.concat([future_fc["yhat_upper"], future_fc["yhat_lower"].iloc[::-1]]),
        fill="toself",
        fillcolor="rgba(251,146,60,0.15)",  # semi-transparent orange
        line=dict(color="rgba(0,0,0,0)"),   # invisible border
        name="80% confidence interval",
        showlegend=True,
        hoverinfo="skip"
    ))

    # actual observed data points
    fig.add_trace(go.Scatter(
        x=prophet_df["ds"],
        y=prophet_df["y"],
        mode="markers",
        name="Actual AQI",
        marker=dict(color="#4ade80", size=7, symbol="circle"),
    ))

    # prophet's fitted line on historical data
    fig.add_trace(go.Scatter(
        x=hist_fc["ds"],
        y=hist_fc["yhat"],
        mode="lines",
        name="Model fit",
        line=dict(color="#4ade80", width=1.5, dash="dot"),
    ))

    # forecast line
    fig.add_trace(go.Scatter(
        x=future_fc["ds"],
        y=future_fc["yhat"],
        mode="lines+markers",
        name=f"Prophet forecast (+{FORECAST_HOURS}h)",
        line=dict(color="#fb923c", width=2.5),
        marker=dict(size=7, color="#fb923c", symbol="diamond"),
    ))

    # vertical boundary line
    fig.add_trace(go.Scatter(
        x=[cutoff, cutoff],
        y=[0, 6],
        mode="lines",
        line=dict(color="#6b9e7e", width=1.5, dash="dot"),
        name="Now",
        showlegend=False,
        hoverinfo="skip"
    ))

    fig.update_layout(
        title=dict(
            text=f"{city} — Prophet AQI Forecast (80% CI)",
            font=dict(color="#e2f5e9", size=15)
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(22,36,25,0.8)",
        font_color="#6b9e7e",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(
            range=[0, 6], gridcolor="#1e3a28",
            tickvals=[1, 2, 3, 4, 5],
            ticktext=["Good", "Fair", "Moderate", "Poor", "Very Poor"],
            tickfont=dict(color="#6b9e7e")
        ),
        xaxis=dict(gridcolor="#1e3a28", tickfont=dict(color="#6b9e7e")),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2f5e9", size=11),
            orientation="h",
            yanchor="bottom", y=-0.25
        ),
        hovermode="x unified"
    )

    return fig


# ── test ───────────────────────────────────────────────────────
if __name__ == "__main__":
    df = read_from_db()
    if df.empty:
        print("No data. Run pipeline first.")
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        kathmandu = df[df["city"] == "Kathmandu"]

        print(f"Testing with {len(kathmandu)} Kathmandu readings...")

        fig_linear = linear_forecast(kathmandu, "Kathmandu")
        if fig_linear:
            print("Linear forecast: OK")
            fig_linear.write_html("test_linear_forecast.html")
            print("Saved to test_linear_forecast.html — open in browser to preview")

        fig_prophet = prophet_forecast(kathmandu, "Kathmandu")
        if fig_prophet:
            print("Prophet forecast: OK")
            fig_prophet.write_html("test_prophet_forecast.html")
            print("Saved to test_prophet_forecast.html — open in browser to preview")