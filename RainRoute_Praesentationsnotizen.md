# RainRoute NYC: Präsentationsnotizen nach Folien

## Folie 1: Titel

- Projekt: **RainRoute NYC**
- Thema: Wetter, Yellow-Taxi-Fahrten und NoSQL-Auswertung
- Datenanalyse mit MongoDB und Neo4j
- Leitidee: Taxi-Nutzung mit Wetterdaten verbinden

## Folie 2: Vortragsstruktur

- Leitfrage vorstellen
- Datenquellen erklären
- Datenmodell und Pipeline zeigen
- Dashboard live demonstrieren
- Ergebnisse und Fazit zusammenfassen

## Folie 3: Datenquellen

- NYC TLC: Yellow-Taxi-Fahrten als Parquet-Dateien
- Open-Meteo: historische Wetterdaten pro Stunde
- Taxi-Zonen: Pickup- und Dropoff-Zonen mit Borough
- Betrachtete Monate: Januar, Juli, Dezember 2025
- Insgesamt: 2.232 Wetterstunden

## Folie 4: Pipeline

- Download: Parquet, CSV und JSON
- Cleaning: unrealistische Fahrten entfernen
- Join: Fahrt wird mit Wetterstunde verbunden
- Import: MongoDB und Neo4j
- Dashboard: Filter, Diagramme und Graph-Auswertung

## Folie 5: Datenmodell

- MongoDB: einzelne Fahrten, Wetterstunden und Zonen
- Neo4j: Zonen und aggregierte Routen
- MongoDB ist gut für Detaildaten und flexible Filter
- Neo4j ist gut für Beziehungen und Routenanalyse
- Modellregel: Details bleiben in MongoDB, Beziehungen werden in Neo4j aggregiert

## Folie 6: Demo-Datensatz

- 600.000 Rohfahrten
- 568.963 bereinigte Fahrten
- 36.280 aggregierte Routen
- 265 Taxi-Zonen
- Januar: 190.442 bereinigte Fahrten
- Juli: 188.013 bereinigte Fahrten
- Dezember: 190.508 bereinigte Fahrten
- Monatswerte sind fast gleich groß

## Folie 7: Wettermix

- Trocken: 70,6 %
- Regen: 28,5 %
- Schnee: 0,9 %
- Regen ist im Datensatz gut sichtbar
- Schnee kommt selten vor
- Schnee deshalb nicht überinterpretieren

## Folie 8: Datenbereinigung / Qualitätssicherung

- Nur Fahrten im gewählten Monat
- Dauer: 1 bis 180 Minuten
- Distanz: 0,1 bis 80 Meilen
- Keine negativen Preise
- Pickup- und Dropoff-Zone müssen vorhanden sein
- Ziel: realistische und vergleichbare Fahrten

## Folie 9: Live-Demo

- Fester Ablauf, damit die Demo ruhig bleibt
- Übersicht: Gesamtzahlen und Wetterverteilung
- Wetteranalyse: Trocken, Regen und Schnee vergleichen
- Routen & Tabelle: Top-Routen und Detaildaten zeigen
- Vergleich: zwei Szenarien nebeneinander
- Beispielvergleich: Trocken vs. Regen

## Folie 10: Aufgabenstellung

- Zwei NoSQL-Datenbanken: MongoDB und Neo4j
- Beide laufen im Docker-Setup
- Heterogene Daten: Taxi, Wetter, Zonen und Zeitreihen
- Reproduzierbare Demo durch Startskript
- README, Tests und Query-Dateien vorhanden
- Kernanforderungen sind abgedeckt

## Folie 11: Fazit

- RainRoute zeigt Wettereffekte explorativ
- MongoDB macht Detaildaten flexibel auswertbar
- Neo4j macht aus Fahrten einen Routengraphen
- Regenfahrten sind im Schnitt kürzer, dauern aber länger
- Interpretation: mehr kurze Innenstadtfahrten, aber langsamere Fahrten durch Verkehr/Stau
- Top-Routen bleiben stark Manhattan-lastig
- Keine komplett andere Routenstruktur, eher stärkere Nutzung bestimmter Routen
- Nächste Schritte: vollständige Monatsdaten und stärkere Kartenansicht

## Folie 12: Quellen & Tools

- Wetterdaten: Open-Meteo Historical Weather API
- Taxidaten: NYC TLC Trip Record Data
- Zonen-Daten: NYC TLC Taxi Zone Data
- Docker für lokale Datenbanken
- MongoDB für Fahrtdaten
- Neo4j für Routengraph
- Streamlit für Dashboard
- LLM-Nutzung dokumentieren
