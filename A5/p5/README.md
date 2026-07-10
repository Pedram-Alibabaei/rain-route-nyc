# RainRoute NYC

RainRoute NYC untersucht, wie Wetterlagen die Nachfrage, Dauer und Routen von New Yorker Yellow-Taxi-Fahrten beeinflussen. Der aktuelle Demo-Stand nutzt drei Monate aus 2025: Januar, Juli und Dezember.

Das Projekt nutzt zwei NoSQL-Datenbanken:

- **MongoDB** speichert einzelne Taxifahrten, stündliche Wetterdaten und Taxi-Zonen.
- **Neo4j** speichert einen aggregierten Graphen aus Taxi-Zonen und häufigen Routen.

Datenquellen:

- NYC TLC Trip Record Data: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api

## Architektur

```text
NYC TLC Parquet + Taxi-Zonen CSV + Open-Meteo JSON
                    |
                  Python ETL
                    |
          +---------+---------+
          |                   |
       MongoDB              Neo4j
 einzelne Fahrten     aggregierte Routen
          |                   |
          +---------+---------+
                    |
              Streamlit-Dashboard
```

## Schnellstart

Die Rohdaten und bereinigten Parquet-Dateien sind nicht im Git-Repository enthalten.
Sie werden bei Bedarf mit den Skripten heruntergeladen und neu erzeugt.

Ein-Klick-Start auf Windows:

```powershell
.\run-local.cmd
```

Das Script startet Docker Desktop, MongoDB, Neo4j und das Streamlit-Dashboard.
Danach öffnet es automatisch `http://localhost:8501` und `http://localhost:7476` im Browser.
Wenn MongoDB leer ist, importiert es automatisch den Demo-Datensatz für Januar, Juli und Dezember 2025 mit 200.000 Rohfahrten pro Monat.

PowerShell-Variante:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-local.ps1
```

Aus diesem Ordner starten:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d
```

Docker Desktop muss vor `docker compose up -d` laufen. `run-local.ps1` übernimmt diesen Schritt automatisch.

Alternativ kann der Starthelfer genutzt werden. Er erstellt bei Bedarf `.env` und `.venv`, installiert die Python-Pakete, startet MongoDB und Neo4j, importiert standardmäßig Januar, Juli und Dezember 2025 und öffnet danach das Streamlit-Dashboard:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Wenn die Daten bereits importiert sind:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1 -SkipImport
```

Nur einen einzelnen Monat importieren:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1 -Month 7
```

Falls PowerShell das Ausführen lokaler Skripte blockiert:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Einen Monat Daten herunterladen:

```powershell
python .\scripts\download_data.py --year 2025 --month 1
```

ETL ohne Datenbankimport testen:

```powershell
python .\scripts\import_data.py --year 2025 --month 1 --limit 10000 --dry-run
```

Schnellen Demo-Datensatz für einen Monat importieren:

```powershell
python .\scripts\import_data.py --year 2025 --month 1 --limit 200000
```

Aktueller Drei-Monats-Demo-Import:

```powershell
python .\scripts\download_data.py --year 2025 --month 1
python .\scripts\import_data.py --year 2025 --month 1 --limit 200000
python .\scripts\download_data.py --year 2025 --month 7
python .\scripts\import_data.py --year 2025 --month 7 --limit 200000
python .\scripts\download_data.py --year 2025 --month 12
python .\scripts\import_data.py --year 2025 --month 12 --limit 200000
```

Verifikationsabfragen ausführen:

```powershell
python .\scripts\run_queries.py
```

Dashboard starten:

```powershell
streamlit run .\app\dashboard.py
```

Adressen:

- Streamlit: http://localhost:8501
- MongoDB: mongodb://localhost:27018
- Neo4j Browser: http://localhost:7476
- Neo4j Bolt URI: `bolt://localhost:7689`
- Neo4j Login: `neo4j` / `taxiweatherpass`

Dashboard-Tabs fuer die Live-Demo:

- `Uebersicht`: Gesamtzahlen, Wetterverteilung und Tageszeiten.
- `Wetteranalyse`: Vergleich von Trocken, Regen und Schnee.
- `Routen & Tabelle`: Neo4j-Top-Routen und bereinigte Einzelfahrten aus MongoDB.
- `Vergleich`: zwei Szenarien mit Monat, Wetter und Tageszeit direkt nebeneinander.

## Lokale Voraussetzungen

Empfohlen wird **Visual Studio Code** mit den Erweiterungen Python, Docker und PowerShell.

Installiert sein sollten:

- Python 3.11 oder 3.12
- Docker Desktop
- Git
- PowerShell 5 oder neuer

Ein JDK ist lokal nicht notwendig. Neo4j läuft im Docker-Container und bringt seine Java-Laufzeit dort selbst mit.

## Tests

Tests ausführen:

```powershell
python -m pytest
```

## Aktueller Demo-Stand

Nach dem Import von jeweils 200.000 Rohfahrten pro Monat:

- Monate: `2025-01`, `2025-07`, `2025-12`
- Rohfahrten im Demo-Import: `600.000`
- bereinigte Fahrten in MongoDB: `568.963`
- Wetterstunden: `2.232`
- Taxi-Zonen in Neo4j: `265`
- aggregierte `TRIPS_TO`-Routen in Neo4j: `36.280`

Bereinigte Fahrten pro Monat:

- Januar 2025: `190.442`
- Juli 2025: `188.013`
- Dezember 2025: `190.508`

## Vollständiger Import

Der Demo-Import nutzt 200.000 Rohfahrten pro Monat, damit die Pipeline schnell getestet werden kann.
Für vollständige Monatsdatensätze:

```powershell
python .\scripts\import_data.py --year 2025 --month 1 --limit 0
python .\scripts\import_data.py --year 2025 --month 7 --limit 0
python .\scripts\import_data.py --year 2025 --month 12 --limit 0
```

## Forschungsfragen

- Steigt die Taxinachfrage bei Regen?
- Welche Routen sind nachts besonders beliebt?
- Welche Startzonen sind die wichtigsten Verkehrsknoten?
- Werden Fahrten bei Regen oder Schnee langsamer oder teurer?
- Verändert schlechtes Wetter das Trinkgeldverhalten?
- Unterscheiden sich Januar, Juli und Dezember im Nachfrageprofil?

## Datenmodell

### MongoDB

MongoDB enthält dokumentorientierte Detaildaten:

- `trips`: einzelne Fahrten mit Startzeit, Zielzeit, Strecke, Preis, Trinkgeld und Wetterlage
- `weather_hourly`: stündliche Wetterdaten für New York City
- `zones`: Taxi-Zonen mit Borough und Service-Zone

MongoDB eignet sich hier besonders für flexible Filter und Aggregationen nach Zeit, Wetterlage und Zonen.

### Neo4j

Neo4j enthält einen aggregierten Routengraphen:

```text
(:Zone)-[:TRIPS_TO {weather, time_band, trip_count, avg_duration_minutes}]->(:Zone)
```

Damit lassen sich zentrale Zonen, starke Verbindungen und wetterabhängige Routenmuster gut analysieren.

## Datenbereinigung

Der ETL entfernt Fahrten mit:

- Startzeit außerhalb des gewählten Monats
- Dauer unter 1 Minute oder über 180 Minuten
- Strecke unter 0,1 Meilen oder über 80 Meilen
- negativem Fahrpreis oder negativer Gesamtsumme
- fehlender Start- oder Zielzone

## Präsentationsstruktur

Vorschlag für 15 Minuten:

1. Problem und Projektidee
2. Datenquellen und Datenmenge
3. Architektur mit MongoDB und Neo4j
4. Datenbereinigung und ETL
5. Erste Ergebnisse und vorsichtige Interpretation
6. Live-Demo des Dashboards
7. MongoDB-Aggregationen und Tabellenansicht
8. Neo4j-Routen und Vergleichs-Tab
9. Ergebnisse, Probleme und Grenzen

## LLM-Deklaration

Dieses Projektgerüst wurde mit Unterstützung von OpenAI Codex erstellt. Weitere LLM-Nutzung sollte in der finalen Abgabe dokumentiert werden.
