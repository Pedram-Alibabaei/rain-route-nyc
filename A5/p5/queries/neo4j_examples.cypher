MATCH (z:Zone)
RETURN z.borough AS stadtbezirk, count(*) AS zonen
ORDER BY zonen DESC;

MATCH ()-[r:TRIPS_TO]->()
RETURN r.month AS monat,
       count(r) AS routen,
       sum(r.trip_count) AS fahrten
ORDER BY monat;

MATCH (a:Zone)-[r:TRIPS_TO]->(b:Zone)
RETURN r.month AS monat,
       a.name AS startzone,
       b.name AS zielzone,
       r.weather AS wetter,
       r.time_band AS tageszeit,
       r.trip_count AS fahrten
ORDER BY fahrten DESC
LIMIT 10;

MATCH (a:Zone)-[r:TRIPS_TO]->(b:Zone)
WHERE r.weather = "rain"
  AND r.month = "2025-01"
RETURN r.month AS monat,
       a.name AS startzone,
       b.name AS zielzone,
       r.time_band AS tageszeit,
       r.trip_count AS regenfahrten,
       r.avg_duration_minutes AS durchschnittliche_dauer
ORDER BY regenfahrten DESC
LIMIT 10;

MATCH (a:Zone)-[r:TRIPS_TO]->(:Zone)
RETURN a.name AS zone,
       a.borough AS stadtbezirk,
       count(r) AS verschiedene_routengruppen,
       sum(r.trip_count) AS fahrten
ORDER BY verschiedene_routengruppen DESC
LIMIT 10;
