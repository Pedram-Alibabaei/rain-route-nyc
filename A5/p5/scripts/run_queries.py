from neo4j import GraphDatabase
from pymongo import MongoClient

from settings import MONGO_DB, MONGO_URI, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


WEATHER_LABELS = {
    "dry": "Trocken",
    "rain": "Regen",
    "snow": "Schnee",
    "other": "Sonstige",
    "unknown": "Unbekannt",
}

TIME_LABELS = {
    "morning": "Morgen",
    "day": "Tag",
    "evening": "Abend",
    "night": "Nacht",
}


def print_mongo_results():
    db = MongoClient(MONGO_URI)[MONGO_DB]
    print("\nMongoDB")
    print("-------")
    print("Fahrten:", db.trips.count_documents({}))
    print("Wetterstunden:", db.weather_hourly.count_documents({}))
    print("Monate:", ", ".join(db.trips.distinct("month")))

    print("\nFahrten pro Monat:")
    for row in db.trips.aggregate([
        {"$group": {"_id": "$month", "fahrten": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]):
        print(row)

    pipeline = [
        {
            "$group": {
                "_id": "$weather_condition",
                "fahrten": {"$sum": 1},
                "durchschnittliche_dauer": {"$avg": "$duration_minutes"},
                "durchschnittlicher_fahrpreis": {"$avg": "$fare_amount"},
                "durchschnittliches_trinkgeld": {"$avg": "$tip_amount"},
            }
        },
        {"$sort": {"fahrten": -1}},
    ]
    for row in db.trips.aggregate(pipeline):
        row["_id"] = WEATHER_LABELS.get(row["_id"], row["_id"])
        print(row)


def print_neo4j_results():
    print("\nNeo4j")
    print("-----")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        for record in session.run("MATCH (z:Zone) RETURN count(z) AS zones"):
            print("Zonen:", record["zones"])
        for record in session.run("MATCH ()-[r:TRIPS_TO]->() RETURN count(r) AS routes"):
            print("Aggregierte Routen:", record["routes"])
        for record in session.run("""
            MATCH ()-[r:TRIPS_TO]->()
            RETURN r.month AS monat, count(r) AS routen, sum(r.trip_count) AS fahrten
            ORDER BY monat
        """):
            print(dict(record))

        query = """
        MATCH (a:Zone)-[r:TRIPS_TO]->(b:Zone)
        RETURN r.month AS monat,
               a.name AS startzone,
               b.name AS zielzone,
               r.weather AS wetter,
               r.time_band AS tageszeit,
               r.trip_count AS fahrten
        ORDER BY fahrten DESC
        LIMIT 10
        """
        for record in session.run(query):
            row = dict(record)
            row["wetter"] = WEATHER_LABELS.get(row["wetter"], row["wetter"])
            row["tageszeit"] = TIME_LABELS.get(row["tageszeit"], row["tageszeit"])
            print(row)
    driver.close()


if __name__ == "__main__":
    print_mongo_results()
    print_neo4j_results()
