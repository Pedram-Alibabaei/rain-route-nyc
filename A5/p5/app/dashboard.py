import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
from settings import MONGO_DB, MONGO_URI, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


st.set_page_config(page_title="RainRoute NYC", layout="wide")

WEATHER_LABELS = {
    "all": "Alle Wetterlagen",
    "dry": "Trocken",
    "rain": "Regen",
    "snow": "Schnee",
    "other": "Sonstige",
    "unknown": "Unbekannt",
}

TIME_LABELS = {
    "all": "Alle Tageszeiten",
    "morning": "Morgen",
    "day": "Tag",
    "evening": "Abend",
    "night": "Nacht",
}

TIME_RANGE_TEXT = (
    "Zeitfenster: Morgen 05:00-09:59, Tag 10:00-15:59, "
    "Abend 16:00-20:59, Nacht 21:00-04:59."
)

ROUTE_COLUMN_LABELS = {
    "month": "Monat",
    "from_zone": "Startzone",
    "from_borough": "Start-Bezirk",
    "to_zone": "Zielzone",
    "to_borough": "Ziel-Bezirk",
    "weather": "Wetter",
    "time_band": "Tageszeit",
    "trips": "Fahrten",
    "avg_duration": "Durchschn. Dauer (min)",
}

TRIP_COLUMN_LABELS = {
    "pickup_at": "Abholzeit",
    "month": "Monat",
    "pickup_zone": "Startzone",
    "dropoff_zone": "Zielzone",
    "weather_condition": "Wetter",
    "time_band": "Tageszeit",
    "distance_miles": "Distanz (mi)",
    "duration_minutes": "Dauer (min)",
    "fare_amount": "Fahrpreis ($)",
    "tip_amount": "Trinkgeld ($)",
    "total_amount": "Gesamt ($)",
}

PLOT_COLORS = {
    "Trocken": "#2F6F5E",
    "Regen": "#2F80ED",
    "Schnee": "#7A8DA8",
    "Sonstige": "#9A6B2F",
    "Unbekannt": "#737373",
}

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.85rem 1rem;
    }
    div[data-testid="stMetricLabel"] {
        color: #475569;
    }
    div[data-testid="stMetricValue"] {
        color: #0f172a;
        font-size: 1.65rem;
    }
    .rr-note {
        border-left: 4px solid #2f80ed;
        background: #f8fafc;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        color: #334155;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def label_value(value, labels):
    return labels.get(value, value)


def clean_distinct(collection, field):
    values = [value for value in collection.distinct(field) if value is not None]
    return sorted(values)


def build_trip_filter(selected_month, selected_weather, selected_time):
    query = {}
    if selected_month != "all":
        query["month"] = selected_month
    if selected_weather != "all":
        query["weather_condition"] = selected_weather
    if selected_time != "all":
        query["time_band"] = selected_time
    return query


def build_route_params(selected_month, selected_weather, selected_time):
    filters = []
    params = {}
    if selected_month != "all":
        filters.append("r.month = $month")
        params["month"] = selected_month
    if selected_weather != "all":
        filters.append("r.weather = $weather")
        params["weather"] = selected_weather
    if selected_time != "all":
        filters.append("r.time_band = $time_band")
        params["time_band"] = selected_time
    return filters, params


def format_int(value):
    return f"{int(value or 0):,}".replace(",", ".")


def format_money(value):
    return f"${float(value or 0):.2f}"


def dataframe_from_rows(rows, rename_map):
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.rename(columns=rename_map)


@st.cache_resource
def mongo_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    return client[MONGO_DB]


@st.cache_resource
def neo4j_driver():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    return driver


def mongo_aggregate(db, pipeline):
    try:
        return list(db.trips.aggregate(pipeline))
    except PyMongoError as exc:
        st.error(f"MongoDB-Abfrage fehlgeschlagen: {exc}")
        return []


def run_neo4j(driver, query, params=None):
    if driver is None:
        return []
    try:
        with driver.session() as session:
            return [dict(record) for record in session.run(query, **(params or {}))]
    except (Neo4jError, ServiceUnavailable) as exc:
        st.warning(f"Neo4j-Abfrage fehlgeschlagen: {exc}")
        return []


def trip_summary(db, query):
    rows = mongo_aggregate(
        db,
        [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "trips": {"$sum": 1},
                    "avg_duration": {"$avg": "$duration_minutes"},
                    "avg_fare": {"$avg": "$fare_amount"},
                    "avg_tip": {"$avg": "$tip_amount"},
                    "avg_distance": {"$avg": "$distance_miles"},
                }
            },
        ],
    )
    return rows[0] if rows else {
        "trips": 0,
        "avg_duration": 0,
        "avg_fare": 0,
        "avg_tip": 0,
        "avg_distance": 0,
    }


def render_summary_metrics(summary):
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Fahrten", format_int(summary.get("trips", 0)))
    col2.metric("Dauer", f"{summary.get('avg_duration', 0):.1f} min")
    col3.metric("Strecke", f"{summary.get('avg_distance', 0):.1f} mi")
    col4.metric("Fahrpreis", format_money(summary.get("avg_fare", 0)))
    col5.metric("Trinkgeld", format_money(summary.get("avg_tip", 0)))


def weather_distribution(db, query):
    query_without_weather = {key: value for key, value in query.items() if key != "weather_condition"}
    rows = mongo_aggregate(
        db,
        [
            {"$match": query_without_weather},
            {"$group": {"_id": "$weather_condition", "Fahrten": {"$sum": 1}}},
            {"$sort": {"Fahrten": -1}},
        ],
    )
    df = pd.DataFrame(rows).rename(columns={"_id": "Wetter"})
    if not df.empty:
        df["Wetter"] = df["Wetter"].map(lambda value: label_value(value, WEATHER_LABELS))
    return df


def time_distribution(db, query):
    rows = mongo_aggregate(
        db,
        [
            {"$match": query},
            {"$group": {"_id": "$time_band", "Fahrten": {"$sum": 1}}},
            {"$sort": {"Fahrten": -1}},
        ],
    )
    df = pd.DataFrame(rows).rename(columns={"_id": "Tageszeit"})
    if not df.empty:
        df["Tageszeit"] = df["Tageszeit"].map(lambda value: label_value(value, TIME_LABELS))
    return df


def top_routes(driver, selected_month, selected_weather, selected_time, limit=25):
    neo4j_filter, params = build_route_params(selected_month, selected_weather, selected_time)
    params["limit"] = limit
    where_clause = "WHERE " + " AND ".join(neo4j_filter) if neo4j_filter else ""
    query = f"""
    MATCH (a:Zone)-[r:TRIPS_TO]->(b:Zone)
    {where_clause}
    RETURN r.month AS month,
           a.name AS from_zone,
           a.borough AS from_borough,
           b.name AS to_zone,
           b.borough AS to_borough,
           r.weather AS weather,
           r.time_band AS time_band,
           r.trip_count AS trips,
           r.avg_duration_minutes AS avg_duration
    ORDER BY trips DESC
    LIMIT $limit
    """
    df = dataframe_from_rows(run_neo4j(driver, query, params), ROUTE_COLUMN_LABELS)
    if not df.empty:
        df["Wetter"] = df["Wetter"].map(lambda value: label_value(value, WEATHER_LABELS))
        df["Tageszeit"] = df["Tageszeit"].map(lambda value: label_value(value, TIME_LABELS))
        df["Durchschn. Dauer (min)"] = df["Durchschn. Dauer (min)"].round(2)
    return df


def route_table_config():
    return {
        "Fahrten": st.column_config.NumberColumn("Fahrten", format="%d"),
        "Durchschn. Dauer (min)": st.column_config.NumberColumn("Durchschn. Dauer (min)", format="%.2f"),
        "Startzone": st.column_config.TextColumn("Startzone", width="medium"),
        "Zielzone": st.column_config.TextColumn("Zielzone", width="medium"),
        "Start-Bezirk": st.column_config.TextColumn("Start-Bezirk", width="small"),
        "Ziel-Bezirk": st.column_config.TextColumn("Ziel-Bezirk", width="small"),
    }


def render_routes_table(df, height=430):
    if df.empty:
        st.info("Neo4j enthält noch keine passenden Routen.")
        return
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=height,
        column_config=route_table_config(),
    )


def render_route_chart(df, title):
    if df.empty:
        st.info("Für diese Auswahl gibt es keine passenden Routen.")
        return
    chart_df = df.head(10).copy()
    chart_df["Route"] = chart_df["Startzone"] + " -> " + chart_df["Zielzone"]
    fig = px.bar(
        chart_df.sort_values("Fahrten"),
        x="Fahrten",
        y="Route",
        orientation="h",
        title=title,
        color="Wetter",
        color_discrete_map=PLOT_COLORS,
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=48, b=10), yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)


def zone_lookup(db):
    return {doc["location_id"]: doc.get("zone", str(doc["location_id"])) for doc in db.zones.find({})}


def trip_sample(db, query, zones, limit):
    projection = {
        "_id": 0,
        "pickup_at": 1,
        "month": 1,
        "pickup_zone_id": 1,
        "dropoff_zone_id": 1,
        "weather_condition": 1,
        "time_band": 1,
        "distance_miles": 1,
        "duration_minutes": 1,
        "fare_amount": 1,
        "tip_amount": 1,
        "total_amount": 1,
    }
    docs = list(db.trips.find(query, projection).sort("pickup_at", -1).limit(limit))
    df = pd.DataFrame(docs)
    if df.empty:
        return df
    df["pickup_at"] = pd.to_datetime(df["pickup_at"])
    df["pickup_zone"] = df["pickup_zone_id"].map(lambda value: zones.get(value, value))
    df["dropoff_zone"] = df["dropoff_zone_id"].map(lambda value: zones.get(value, value))
    df["weather_condition"] = df["weather_condition"].map(lambda value: label_value(value, WEATHER_LABELS))
    df["time_band"] = df["time_band"].map(lambda value: label_value(value, TIME_LABELS))
    df = df[
        [
            "pickup_at",
            "month",
            "pickup_zone",
            "dropoff_zone",
            "weather_condition",
            "time_band",
            "distance_miles",
            "duration_minutes",
            "fare_amount",
            "tip_amount",
            "total_amount",
        ]
    ]
    return df.rename(columns=TRIP_COLUMN_LABELS)


def trip_table_config():
    return {
        "Abholzeit": st.column_config.DatetimeColumn("Abholzeit", format="YYYY-MM-DD HH:mm"),
        "Startzone": st.column_config.TextColumn("Startzone", width="medium"),
        "Zielzone": st.column_config.TextColumn("Zielzone", width="medium"),
        "Distanz (mi)": st.column_config.NumberColumn("Distanz (mi)", format="%.2f"),
        "Dauer (min)": st.column_config.NumberColumn("Dauer (min)", format="%.2f"),
        "Fahrpreis ($)": st.column_config.NumberColumn("Fahrpreis ($)", format="$%.2f"),
        "Trinkgeld ($)": st.column_config.NumberColumn("Trinkgeld ($)", format="$%.2f"),
        "Gesamt ($)": st.column_config.NumberColumn("Gesamt ($)", format="$%.2f"),
    }


def render_trip_table(df):
    if df.empty:
        st.info("Für diese Filter gibt es keine passenden Fahrten.")
        return
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=460,
        column_config=trip_table_config(),
    )


def compare_label(selected_month, selected_weather, selected_time):
    return " | ".join(
        [
            "Alle Monate" if selected_month == "all" else selected_month,
            label_value(selected_weather, WEATHER_LABELS),
            label_value(selected_time, TIME_LABELS),
        ]
    )


def comparison_controls(prefix, month_options, weather_options, time_options):
    month_index = min(1, len(month_options) - 1) if prefix == "left" else min(2, len(month_options) - 1)
    weather_default = "dry" if prefix == "left" else "rain"
    weather_index = weather_options.index(weather_default) if weather_default in weather_options else 0
    time_index = time_options.index("evening") if "evening" in time_options else 0

    selected_month = st.selectbox(
        "Monat",
        month_options,
        index=month_index,
        format_func=lambda value: "Alle Monate" if value == "all" else value,
        key=f"{prefix}_month",
    )
    selected_weather = st.selectbox(
        "Wetterlage",
        weather_options,
        index=weather_index,
        format_func=lambda value: label_value(value, WEATHER_LABELS),
        key=f"{prefix}_weather",
    )
    selected_time = st.selectbox(
        "Tageszeit",
        time_options,
        index=time_index,
        format_func=lambda value: label_value(value, TIME_LABELS),
        key=f"{prefix}_time",
    )
    return selected_month, selected_weather, selected_time


try:
    db = mongo_db()
except ServerSelectionTimeoutError:
    st.error("MongoDB ist nicht erreichbar.")
    st.code("docker compose up -d", language="powershell")
    st.stop()
except PyMongoError as exc:
    st.error(f"MongoDB ist nicht erreichbar: {exc}")
    st.stop()

try:
    driver = neo4j_driver()
except (Neo4jError, ServiceUnavailable) as exc:
    driver = None
    st.warning(f"Neo4j ist nicht erreichbar. MongoDB-Auswertungen bleiben verfügbar. Details: {exc}")

try:
    total_trips = db.trips.count_documents({})
except PyMongoError as exc:
    st.error(f"MongoDB-Abfrage fehlgeschlagen: {exc}")
    st.stop()

if total_trips == 0:
    st.info("Es sind noch keine Fahrten importiert.")
    st.code(
        "python .\\scripts\\download_data.py --year 2025 --month 1\n"
        "python .\\scripts\\import_data.py --year 2025 --month 1 --limit 200000",
        language="powershell",
    )
    st.stop()

month_options = ["all"] + clean_distinct(db.trips, "month")
weather_options = ["all"] + clean_distinct(db.trips, "weather_condition")
time_options = ["all"] + clean_distinct(db.trips, "time_band")
zones = zone_lookup(db)

st.title("RainRoute NYC")
st.caption("Interaktive Analyse von Wetter, Tageszeit und Routenmustern bei NYC Yellow Taxis")

with st.sidebar:
    st.header("Globale Filter")
    month = st.selectbox(
        "Monat",
        month_options,
        format_func=lambda value: "Alle Monate" if value == "all" else value,
    )
    weather = st.selectbox(
        "Wetterlage",
        weather_options,
        format_func=lambda value: label_value(value, WEATHER_LABELS),
    )
    time_band = st.selectbox(
        "Tageszeit",
        time_options,
        format_func=lambda value: label_value(value, TIME_LABELS),
        help=TIME_RANGE_TEXT,
    )
    st.divider()
    st.caption(TIME_RANGE_TEXT)

match_filter = build_trip_filter(month, weather, time_band)
time_only_filter = build_trip_filter(month, "all", time_band)
summary = trip_summary(db, match_filter)

st.markdown(
    f"""
    <div class="rr-note">
    Aktuelle Auswahl: <strong>{compare_label(month, weather, time_band)}</strong>.
    Die Kennzahlen kommen aus MongoDB; Routen-Tabellen und Top-Verbindungen kommen aus Neo4j.
    </div>
    """,
    unsafe_allow_html=True,
)

overview_tab, weather_tab, routes_tab, compare_tab = st.tabs(
    ["Übersicht", "Wetteranalyse", "Routen & Tabelle", "Vergleich"]
)

with overview_tab:
    render_summary_metrics(summary)

    left, right = st.columns(2)
    with left:
        st.subheader("Fahrten nach Wetterlage")
        weather_df = weather_distribution(db, match_filter)
        if not weather_df.empty:
            fig = px.bar(
                weather_df,
                x="Wetter",
                y="Fahrten",
                color="Wetter",
                color_discrete_map=PLOT_COLORS,
            )
            fig.update_layout(showlegend=False, height=380, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Fahrten nach Tageszeit")
        time_df = time_distribution(db, match_filter)
        if not time_df.empty:
            fig = px.bar(time_df, x="Tageszeit", y="Fahrten", color="Tageszeit")
            fig.update_layout(showlegend=False, height=380, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

with weather_tab:
    st.subheader("Trocken, Regen und Schnee im Vergleich")
    comparison_rows = mongo_aggregate(
        db,
        [
            {"$match": time_only_filter},
            {
                "$group": {
                    "_id": "$weather_condition",
                    "Fahrten": {"$sum": 1},
                    "Durchschn. Dauer (min)": {"$avg": "$duration_minutes"},
                    "Durchschn. Strecke (mi)": {"$avg": "$distance_miles"},
                    "Durchschn. Fahrpreis ($)": {"$avg": "$fare_amount"},
                    "Durchschn. Trinkgeld ($)": {"$avg": "$tip_amount"},
                }
            },
            {"$match": {"_id": {"$in": ["dry", "rain", "snow"]}}},
            {"$sort": {"Fahrten": -1}},
        ],
    )
    comparison_df = pd.DataFrame(comparison_rows).rename(columns={"_id": "Wetter"})
    if comparison_df.empty:
        st.info("Für den Wettervergleich wurden noch keine passenden Daten gefunden.")
    else:
        comparison_df["Wetter"] = comparison_df["Wetter"].map(lambda value: label_value(value, WEATHER_LABELS))
        for column in comparison_df.columns:
            if column not in {"Wetter", "Fahrten"}:
                comparison_df[column] = comparison_df[column].round(2)

        metric_columns = [
            "Durchschn. Dauer (min)",
            "Durchschn. Strecke (mi)",
            "Durchschn. Fahrpreis ($)",
            "Durchschn. Trinkgeld ($)",
        ]
        fig = px.bar(
            comparison_df,
            x="Wetter",
            y=metric_columns,
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            comparison_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Fahrten": st.column_config.NumberColumn("Fahrten", format="%d"),
                "Durchschn. Dauer (min)": st.column_config.NumberColumn("Durchschn. Dauer (min)", format="%.2f"),
                "Durchschn. Strecke (mi)": st.column_config.NumberColumn("Durchschn. Strecke (mi)", format="%.2f"),
                "Durchschn. Fahrpreis ($)": st.column_config.NumberColumn("Durchschn. Fahrpreis ($)", format="$%.2f"),
                "Durchschn. Trinkgeld ($)": st.column_config.NumberColumn("Durchschn. Trinkgeld ($)", format="$%.2f"),
            },
        )

with routes_tab:
    st.subheader("Top-Routen aus Neo4j")
    route_limit = st.slider("Anzahl Routen", min_value=10, max_value=50, value=25, step=5)
    routes_df = top_routes(driver, month, weather, time_band, route_limit)
    render_routes_table(routes_df)

    st.subheader("Routen, die bei Regen stärker werden")
    rain_params = {}
    rain_filters = ["dry.trip_count > 0", "rain.time_band = dry.time_band", "rain.month = dry.month"]
    if month != "all":
        rain_filters.append("rain.month = $month")
        rain_params["month"] = month
    if time_band != "all":
        rain_filters.append("rain.time_band = $time_band")
        rain_params["time_band"] = time_band
    rain_where_clause = " AND ".join(rain_filters)

    rain_routes_query = f"""
    MATCH (a:Zone)-[rain:TRIPS_TO {{weather: "rain"}}]->(b:Zone)
    MATCH (a)-[dry:TRIPS_TO {{weather: "dry"}}]->(b)
    WHERE {rain_where_clause}
    RETURN rain.month AS Monat,
           a.name AS Startzone,
           b.name AS Zielzone,
           rain.time_band AS Tageszeit,
           rain.trip_count AS Regenfahrten,
           dry.trip_count AS Trockenfahrten,
           round(toFloat(rain.trip_count) / dry.trip_count, 2) AS Faktor
    ORDER BY Faktor DESC, Regenfahrten DESC
    LIMIT 20
    """
    rain_routes_df = pd.DataFrame(run_neo4j(driver, rain_routes_query, rain_params))
    if not rain_routes_df.empty:
        rain_routes_df["Tageszeit"] = rain_routes_df["Tageszeit"].map(lambda value: label_value(value, TIME_LABELS))
        st.dataframe(
            rain_routes_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Regenfahrten": st.column_config.NumberColumn("Regenfahrten", format="%d"),
                "Trockenfahrten": st.column_config.NumberColumn("Trockenfahrten", format="%d"),
                "Faktor": st.column_config.NumberColumn("Faktor", format="%.2f"),
            },
        )
    else:
        st.info("Für Regen-vs.-Trocken-Routen gibt es noch keine gemeinsamen Vergleichsrouten.")

    st.subheader("Bereinigte Einzelfahrten aus MongoDB")
    sample_limit = st.select_slider("Tabellenzeilen", options=[25, 50, 100, 200], value=50)
    render_trip_table(trip_sample(db, match_filter, zones, sample_limit))

with compare_tab:
    st.subheader("Zwei Szenarien direkt vergleichen")
    st.caption("Jede Seite hat eigene Filter für Monat, Wetterlage und Tageszeit.")

    left_controls, right_controls = st.columns(2)
    with left_controls:
        st.markdown("**Szenario A**")
        left_month, left_weather, left_time = comparison_controls("left", month_options, weather_options, time_options)
    with right_controls:
        st.markdown("**Szenario B**")
        right_month, right_weather, right_time = comparison_controls("right", month_options, weather_options, time_options)

    left_filter = build_trip_filter(left_month, left_weather, left_time)
    right_filter = build_trip_filter(right_month, right_weather, right_time)
    left_summary = trip_summary(db, left_filter)
    right_summary = trip_summary(db, right_filter)

    comparison_metrics = pd.DataFrame(
        [
            {
                "Szenario": "A",
                "Auswahl": compare_label(left_month, left_weather, left_time),
                "Fahrten": left_summary.get("trips", 0),
                "Dauer": left_summary.get("avg_duration", 0),
                "Strecke": left_summary.get("avg_distance", 0),
                "Fahrpreis": left_summary.get("avg_fare", 0),
                "Trinkgeld": left_summary.get("avg_tip", 0),
            },
            {
                "Szenario": "B",
                "Auswahl": compare_label(right_month, right_weather, right_time),
                "Fahrten": right_summary.get("trips", 0),
                "Dauer": right_summary.get("avg_duration", 0),
                "Strecke": right_summary.get("avg_distance", 0),
                "Fahrpreis": right_summary.get("avg_fare", 0),
                "Trinkgeld": right_summary.get("avg_tip", 0),
            },
        ]
    )

    metric_left, metric_right = st.columns(2)
    with metric_left:
        st.markdown("**Szenario A**")
        render_summary_metrics(left_summary)
    with metric_right:
        st.markdown("**Szenario B**")
        render_summary_metrics(right_summary)

    chart_a, chart_b = st.columns([1, 1])
    with chart_a:
        fig = px.bar(
            comparison_metrics,
            x="Szenario",
            y="Fahrten",
            color="Szenario",
            text="Fahrten",
            title="Fahrtenzahl",
        )
        fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig.update_layout(showlegend=False, height=360, margin=dict(l=10, r=10, t=48, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with chart_b:
        metric_long = comparison_metrics.melt(
            id_vars=["Szenario"],
            value_vars=["Dauer", "Strecke", "Fahrpreis", "Trinkgeld"],
            var_name="Kennzahl",
            value_name="Wert",
        )
        fig = px.bar(metric_long, x="Kennzahl", y="Wert", color="Szenario", barmode="group", title="Durchschnittswerte")
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=48, b=10))
        st.plotly_chart(fig, use_container_width=True)

    route_left, route_right = st.columns(2)
    with route_left:
        render_route_chart(top_routes(driver, left_month, left_weather, left_time, 10), "Top-Routen Szenario A")
    with route_right:
        render_route_chart(top_routes(driver, right_month, right_weather, right_time, 10), "Top-Routen Szenario B")
