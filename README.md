# RainRoute NYC

A university team project exploring associations between NYC Yellow Taxi trips
and hourly weather. A Python pipeline cleans trip records, stores detailed data
in MongoDB, aggregates routes in Neo4j and presents comparisons in Streamlit.

**Stack:** Python, pandas, Polars, MongoDB, Neo4j, Docker Compose, Streamlit.

## Architecture

```text
NYC TLC trip records + taxi zones + Open-Meteo hourly weather
                            |
                        Python ETL
                            |
                 +----------+----------+
                 |                     |
              MongoDB                Neo4j
          individual trips      aggregated routes
                 |                     |
                 +----------+----------+
                            |
                    Streamlit dashboard
```

## My Contribution

Pedram Alibabaei contributed to this team project by fixing the MongoDB
aggregation used to compare trip duration, distance and fares across weather
conditions. The fix separates internal aggregation field names from the German
display labels applied in pandas. This contribution is part of the team's wider
ETL, database and dashboard implementation.

## Quick Start

Requirements: Windows, PowerShell 5 or newer, Python 3.11 or 3.12, Docker Desktop
with Linux containers and Docker Compose. Internet access is needed for the first
dependency, container and data downloads.

From the repository root:

```powershell
cd .\A5\p5
.\run-local.cmd
```

The launcher creates `.env` and a local Python environment if needed, installs the
requirements, starts Docker Desktop and the two database containers, and imports
the demo if MongoDB is empty. It then starts the dashboard and opens:

- Streamlit: <http://localhost:8501>
- Neo4j Browser: <http://localhost:7476>

The default demo uses the first 200,000 raw records from each of January, July and
December 2025. The limit applies to processing; complete monthly source Parquet
files are downloaded. Allow time and disk space for the initial downloads and
imports. Raw and processed datasets are not committed to Git.

The local Neo4j demo login is `neo4j` / `taxiweatherpass`. MongoDB has no
authentication in this development setup. Do not expose these containers to
untrusted networks or treat this configuration as a production deployment.

For a smaller first run, from `A5/p5`:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-local.ps1 -Months 1 -Limit 10000
```

That smaller run will not reproduce the recorded three-month totals below. The
launcher skips import whenever MongoDB already contains trips; it does not check
whether the selected months or limit match the existing data. See the
[technical guide](A5/p5/README.md) for explicit download/import commands.

If a local `.venv` was copied from a different folder or Windows account, recreate
it in the current project location before starting the launcher.

## Testing

From `A5/p5`, after installing the requirements:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The automated tests exercise weather classification, time bands and data cleaning
with small inputs. They do not replace a live MongoDB/Neo4j dashboard check.

## Recorded Demo and Limitations

The recorded three-month demo contains **568,963 cleaned trips** from 600,000 raw
records. The project notes also record 265 taxi zones and 36,280 aggregated route
relationships. These are demo results, not the complete NYC taxi archive.

- The first-record limit is neither random sampling nor a time-balanced sample.
  It cannot establish representative monthly taxi demand.
- Weather is joined by pickup hour using a single NYC weather location, not a
  separate measurement for every trip or zone.
- Comparisons are descriptive associations. They do not establish that weather
  causes changes in trip duration, fares or demand.
- Counts can differ with the import configuration or changed source data.

## Further Reading

- [Technical guide and manual setup, in German](A5/p5/README.md)
- [Presentation PDF](RainRoute%20NYC.pdf)
- [Presentation slides](RainRoute%20NYC.pptx)
- [MongoDB example queries](A5/p5/queries/mongo_examples.js)
- [Neo4j example queries](A5/p5/queries/neo4j_examples.cypher)

Data sources are [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
and the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api).
Consult their terms before redistributing downloaded data. AI tools were used
during development; individual contributions and team ownership are distinguished
above.
