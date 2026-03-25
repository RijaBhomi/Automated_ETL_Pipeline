import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from load import read_from_db
from datetime import datetime
from forecast import linear_forecast, prophet_forecast

st.set_page_config(
    page_title="Nepal AQI Monitor",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp { background-color: #0f1a14; }

    .navbar {
        display: flex; align-items: center; justify-content: space-between;
        padding: 14px 32px; background: #0f1a14;
        border-bottom: 1px solid #1e3a28; margin-bottom: 0px;
    }
    .nav-brand { font-size: 20px; font-weight: 700; color: #4ade80; }
    .nav-brand span { color: #86efac; }
    .nav-links { display: flex; gap: 28px; font-size: 14px; color: #6b9e7e; }
    .nav-links b { color: #4ade80; border-bottom: 2px solid #4ade80;
                   padding-bottom: 2px; }

    .status-badge {
        background: #1a2e1f; border: 1px solid #2d5a3d;
        border-radius: 20px; padding: 6px 14px;
        font-size: 12px; font-weight: 600; color: #4ade80;
        display: inline-flex; align-items: center; gap: 6px;
    }
    .status-dot { width: 8px; height: 8px; background: #4ade80;
                  border-radius: 50%; display: inline-block;
                  animation: pulse 2s infinite; }
    @keyframes pulse {
        0%, 100% { opacity: 1; } 50% { opacity: 0.4; }
    }

    .page-header { padding: 28px 32px 8px; }
    .page-title { font-size: 32px; font-weight: 700; color: #e2f5e9; margin: 0; }
    .page-subtitle { font-size: 14px; color: #6b9e7e; margin: 4px 0 0; }

    .kpi-card {
        background: #162419; border-radius: 16px;
        padding: 20px 24px; border: 1px solid #1e3a28;
        height: 130px;
    }
    .kpi-icon {
        width: 40px; height: 40px; border-radius: 10px;
        background: #1e3a28; display: flex; align-items: center;
        justify-content: center; font-size: 18px; margin-bottom: 10px;
    }
    .kpi-label { font-size: 11px; font-weight: 600; color: #6b9e7e;
                 text-transform: uppercase; letter-spacing: 0.8px; }
    .kpi-value { font-size: 28px; font-weight: 700; color: #e2f5e9;
                 line-height: 1.1; }
    .kpi-unit  { font-size: 14px; color: #6b9e7e; font-weight: 400; }

    .city-card {
        background: #162419; border-radius: 14px;
        padding: 14px 16px; border: 1px solid #1e3a28;
        margin-bottom: 8px;
    }
    .city-name  { font-size: 15px; font-weight: 600; color: #e2f5e9; }
    .city-temp  { font-size: 22px; font-weight: 700; color: #e2f5e9; }
    .city-aqi   { font-size: 12px; font-weight: 600; padding: 3px 10px;
                  border-radius: 20px; display: inline-block; }

    .good      { background: #14532d; color: #4ade80; }
    .fair      { background: #365314; color: #a3e635; }
    .moderate  { background: #451a03; color: #fb923c; }
    .poor      { background: #450a0a; color: #f87171; }
    .verypoor  { background: #3b0764; color: #c084fc; }

    .section-card {
        background: #162419; border-radius: 16px;
        padding: 20px 24px; border: 1px solid #1e3a28;
    }
    .section-title {
        font-size: 16px; font-weight: 600; color: #e2f5e9;
        margin-bottom: 16px;
    }

    .health-rec {
        background: #1a2e1f; border-radius: 12px;
        padding: 16px 20px; border-left: 4px solid #4ade80;
        margin-top: 16px;
    }
    .health-rec-title { font-size: 12px; font-weight: 700;
                        color: #4ade80; text-transform: uppercase;
                        letter-spacing: 0.8px; margin-bottom: 6px; }
    .health-rec-text  { font-size: 13px; color: #a7c4b0; line-height: 1.6; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding: 0 !important; max-width: 100% !important; }
    section[data-testid="stSidebar"] { display: none; }
    div[data-testid="stHorizontalBlock"] { gap: 12px; padding: 0 32px; }
</style>
""", unsafe_allow_html=True)


# ── helpers ────────────────────────────────────────────────────
def aqi_class(label):
    return {
        "Good": "good", "Fair": "fair", "Moderate": "moderate",
        "Poor": "poor", "Very Poor": "verypoor"
    }.get(label, "moderate")

def health_recommendation(avg_aqi):
    if avg_aqi <= 1:
        return "Air quality is excellent. Perfect day for outdoor activities for all populations."
    elif avg_aqi <= 2:
        return "Air quality is satisfactory. Outdoor activities are fine for most people."
    elif avg_aqi <= 3:
        return "Moderate air quality. Sensitive groups should consider reducing prolonged outdoor activity."
    elif avg_aqi <= 4:
        return "Poor air quality. Sensitive groups should avoid outdoor activity. General public should reduce exposure."
    else:
        return "Very poor air quality. Everyone should avoid outdoor activities. Keep windows closed."

def risk_colour_hex(risk):
    return {
        "Low": "#2d9e5f", "Moderate": "#f59e0b",
        "High": "#ef4444", "Very High": "#8b5cf6"
    }.get(risk, "#5a7a67")

@st.cache_data(ttl=300)
def load_data():
    df = read_from_db()
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def main():
    df = load_data()

    # ── navbar ─────────────────────────────────────────────────
    last_run = df["timestamp"].max().strftime("%Y-%m-%d %H:%M") if not df.empty else "N/A"
    st.markdown(f"""
    <div class="navbar">
        <div class="nav-brand">Nepal<span>AQI</span></div>
        <div class="nav-links">
            <b>Dashboard</b>
            <span>Air Maps</span>
            <span>Trends</span>
            <span>Health Insights</span>
        </div>
        <div class="status-badge">
            <span class="status-dot"></span>
            ETL STATUS: SUCCESSFUL &nbsp;|&nbsp; LAST RUN: {last_run}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.warning("No data yet. Run `python pipeline.py --once` first.")
        st.stop()

    # latest per city
    latest = (
        df.sort_values("timestamp", ascending=False)
        .groupby("city").first().reset_index()
        .sort_values("pm25", ascending=False)
    )

    avg_aqi   = round(latest["aqi"].mean(), 1)
    avg_pm25  = round(latest["pm25"].mean(), 1)
    avg_temp  = round(latest["temperature"].mean(), 1)
    avg_hum   = round(latest["humidity"].mean(), 1)
    worst     = latest.iloc[0]
    best      = latest.iloc[-1]

    # ── page header ────────────────────────────────────────────
    st.markdown(f"""
    <div class="page-header">
        <p class="page-title">Atmospheric Pulse</p>
        <p class="page-subtitle">
            <span style="color:#2d9e5f">●</span>
            Live monitoring across 10 Nepali cities &nbsp;·&nbsp;
            {len(df)} records collected
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='padding: 0 32px'>", unsafe_allow_html=True)

    # ── KPI cards ──────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    kpis = [
        ("💨", "Air Quality Index", str(avg_aqi), "AQI"),
        ("🔬", "Particulate Matter 2.5", str(avg_pm25), "µg/m³"),
        ("🌡️", "Ambient Temperature", str(avg_temp), "°C"),
        ("💧", "Humidity Level", str(avg_hum), "%"),
    ]
    for col, (icon, label, val, unit) in zip([k1,k2,k3,k4], kpis):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{val} <span class="kpi-unit">{unit}</span></div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)


    # ── main content: map + trends ─────────────────────────────
    map_col, trend_col = st.columns([6, 4], gap="medium")

    with map_col:
        st.markdown("#### 🗺️ Interactive Air Map")

        city_coords = {
            "Kathmandu":  (27.7172, 85.3240),
            "Lalitpur":   (27.6644, 85.3188),
            "Bhaktapur":  (27.6710, 85.4298),
            "Pokhara":    (28.2096, 83.9856),
            "Biratnagar": (26.4525, 87.2718),
            "Dharan":     (26.8120, 87.2840),
            "Janakpur":   (26.7288, 85.9240),
            "Birgunj":    (27.0104, 84.8770),
            "Nepalgunj":  (28.0500, 81.6167),
            "Dhangadhi":  (28.6833, 80.6000),
        }

        map_rows = []
        for _, row in latest.iterrows():
            if row["city"] in city_coords:
                lat, lon = city_coords[row["city"]]
                map_rows.append({
                    "city": row["city"], "lat": lat, "lon": lon,
                    "pm25": row["pm25"], "aqi_label": row["aqi_label"],
                    "health_risk": row["health_risk"],
                    "temperature": row["temperature"],
                })
        map_df = pd.DataFrame(map_rows)

        fig_map = px.scatter_mapbox(
            map_df, lat="lat", lon="lon",
            color="pm25", size="pm25",
            hover_name="city",
            hover_data={
                "aqi_label": True, "health_risk": True,
                "temperature": True, "pm25": True,
                "lat": False, "lon": False,
            },
            color_continuous_scale=["#2d9e5f","#f59e0b","#ef4444","#8b5cf6"],
            size_max=50, zoom=5.5,
            center={"lat": 28.0, "lon": 84.0},
            mapbox_style="carto-darkmatter",
            height=420,
            labels={"pm25": "PM2.5"}
        )
        fig_map.update_layout(
            margin=dict(l=0,r=0,t=0,b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_colorbar=dict(
                title="PM2.5",
                tickfont=dict(color="#5a7a67"),
                title_font=dict(color="#5a7a67")
            )
        )
        st.plotly_chart(fig_map, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with trend_col:
        st.markdown("#### 📈 24h Atmospheric Trends")

        # AQI trend for top 5 most polluted cities
        top5 = latest.head(5)["city"].tolist()
        trend_df = (
            df[df["city"].isin(top5)]
            .sort_values("timestamp")
        )

        fig_trend = go.Figure()
        colours = ["#2d9e5f","#f59e0b","#ef4444","#8b5cf6","#06b6d4"]
        for i, city in enumerate(top5):
            city_data = trend_df[trend_df["city"] == city]
            fig_trend.add_trace(go.Scatter(
                x=city_data["timestamp"], y=city_data["aqi"],
                name=city, mode="lines+markers",
                line=dict(color=colours[i], width=2),
                marker=dict(size=5),
            ))

        fig_trend.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#162419",
            font_color="#a7c4b0",
            height=240,
            margin=dict(l=0,r=0,t=10,b=0),
            yaxis=dict(
                range=[0,6], gridcolor="#1e3a28",
                tickvals=[1,2,3,4,5],
                ticktext=["Good","Fair","Mod","Poor","V.Poor"]
            ),
            xaxis=dict(gridcolor="#1e3a28", showticklabels=False),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=11, color="#e2f5e9"),
                orientation="h",
                yanchor="bottom", y=-0.15,
            ),
            hovermode="x unified"
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # health recommendation box
        rec_text = health_recommendation(avg_aqi)
        st.markdown(f"""
        <div class="health-rec">
            <div class="health-rec-title">🩺 Health Recommendation</div>
            <div class="health-rec-text">{rec_text}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── bottom row: city cards + bar chart ─────────────────────
    cities_col, bar_col = st.columns([4, 6], gap="medium")

    with cities_col:
        st.markdown("#### 🏙️ City Rankings")

        for _, row in latest.iterrows():
            badge = aqi_class(row["aqi_label"])
            st.markdown(f"""
            <div class="city-card">
                <div style="display:flex; justify-content:space-between; align-items:center">
                    <div>
                        <div class="city-name">{row['city']}</div>
                        <div class="city-temp">{row['temperature']}°C</div>
                        <div style="font-size:12px; color:#5a7a67; margin-top:2px">
                            PM2.5: {row['pm25']} µg/m³ &nbsp;·&nbsp; Humidity: {row['humidity']}%
                        </div>
                    </div>
                    <div style="text-align:right">
                        <div class="city-aqi {badge}">{row['aqi_label']}</div>
                        <div style="font-size:11px; color:#5a7a67; margin-top:6px">
                            AQI {row['aqi']}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with bar_col:
        st.markdown("#### 🔬 PM2.5 Comparison")

        fig_bar = go.Figure(go.Bar(
            x=latest.sort_values("pm25")["city"],
            y=latest.sort_values("pm25")["pm25"],
            marker_color=[
                risk_colour_hex(r)
                for r in latest.sort_values("pm25")["health_risk"]
            ],
            text=latest.sort_values("pm25")["pm25"],
            texttemplate="%{text:.1f}",
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>PM2.5: %{y:.1f} µg/m³<extra></extra>"
        ))
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#162419",
            font_color="#a7c4b0",
            height=320,
            margin=dict(l=0,r=0,t=10,b=0),
            yaxis=dict(gridcolor="#1e3a28", title="PM2.5 (µg/m³)", tickfont=dict(color="#a7c4b0")),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # WHO guideline reference line annotation
        st.markdown("""
        <div style="font-size:12px; color:#5a7a67; margin-top:-10px; padding: 0 4px">
            <span style="color:#ef4444">■</span> WHO guideline: PM2.5 should be below
            <b>15 µg/m³</b> (24hr average)
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── forecast section ───────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="padding: 0 32px">
        <div class="section-card">
            <div class="section-title">AQI Forecast — next 6 hours</div>
    """, unsafe_allow_html=True)

    # city selector for forecast
    all_cities_list = sorted(df["city"].unique().tolist())

    fc_col1, fc_col2 = st.columns([3, 1])
    with fc_col1:
        selected_fc_city = st.selectbox(
            "Select city to forecast",
            options=all_cities_list,
            index=0,
            key="forecast_city"
        )
    with fc_col2:
        forecast_method = st.radio(
            "Method",
            options=["Both", "Prophet only", "Linear only"],
            index=0,
            key="forecast_method"
        )

    city_fc_df = df[df["city"] == selected_fc_city].copy()

    if len(city_fc_df) < 3:
        st.warning(f"Not enough data for {selected_fc_city} yet. "
                f"Run pipeline a few more times to collect data.")
    else:
        if forecast_method in ["Both", "Linear only"]:
            fig_lin = linear_forecast(city_fc_df, selected_fc_city)
            if fig_lin:
                st.markdown(
                    '<div style="font-size:13px; margin-bottom:6px"> '
                    'Linear trend — extends recent pattern forward</div>',
                    unsafe_allow_html=True
                )
                fc_lin_col, fc_lin_spacer = st.columns([8, 2])
                with fc_lin_col:
                    st.plotly_chart(fig_lin, use_container_width=True)

        if forecast_method in ["Both", "Prophet only"]:
            with st.spinner(f"Running Prophet model for {selected_fc_city}..."):
                fig_proph = prophet_forecast(city_fc_df, selected_fc_city)
            if fig_proph:
                st.markdown(
                    '<div style="font-size:13px; color:#6b9e7e; margin-bottom:6px">'
                    'Prophet model — finds patterns + shows 80% confidence interval</div>',
                    unsafe_allow_html=True
                )
                fc_pr_col, fc_pr_spacer = st.columns([8, 2])
                with fc_pr_col:
                    st.plotly_chart(fig_proph, use_container_width=True)

            # explanation card below the charts
            st.markdown(f"""
            <div style="background:#1a2e1f; border-radius:12px; padding:14px 18px;
                        border-left:4px solid #4ade80; margin-top:8px;">
                <div style="font-size:12px; font-weight:700; color:#4ade80;
                            text-transform:uppercase; letter-spacing:0.8px;
                            margin-bottom:6px;">
                    How to read this forecast
                </div>
                <div style="font-size:13px; color:#a7c4b0; line-height:1.7">
                    The <span style="color:#4ade80">green line</span> shows
                    historical AQI readings. The
                    <span style="color:#fb923c">orange line</span> after the
                    dotted "Now" marker is the predicted AQI for the next 6 hours.
                    The <span style="color:#fb923c; opacity:0.6">shaded orange area</span>
                    (Prophet only) is the 80% confidence interval — the model is
                    80% sure the real value will fall inside that band.
                    Prophet uses Meta's open-source forecasting library trained on
                    your {len(city_fc_df)} {selected_fc_city} readings.
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    # ── raw data expander ──────────────────────────────────────
    with st.expander("🗄️ View Raw Sensor Data — last 100 observations"):
        display_df = (
            df.sort_values("timestamp", ascending=False)
            .head(100)
            .drop(columns=["id"])
            .reset_index(drop=True)
        )

        def highlight_risk(val):
            return {
                "Low":       "background-color:#d1fae5; color:#065f46",
                "Moderate":  "background-color:#fef3c7; color:#92400e",
                "High":      "background-color:#fee2e2; color:#991b1b",
                "Very High": "background-color:#ede9fe; color:#5b21b6",
            }.get(val, "")

        st.dataframe(
            display_df.style.map(highlight_risk, subset=["health_risk"]),
            use_container_width=True,
            height=320
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── footer ─────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding: 24px; font-size:12px; color:#5a7a67;
                border-top: 1px solid #1e3a28; margin-top: 16px;">
        © 2026 NEPALAQIMONITOR · BUILT WITH PYTHON, STREAMLIT & PLOTLY
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()