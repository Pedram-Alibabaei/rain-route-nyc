# RainRoute NYC

RainRoute NYC is a NoSQL and Big Data practicum project that combines NYC Yellow Taxi trips with historical weather data.

The runnable project is in:

```text
A5/p5
```

Main deliverables:

- `A5/p5`: Python ETL, MongoDB/Neo4j Docker setup, Streamlit dashboard, tests and queries
- `RainRoute-NYC-Vortrag.pptx`: presentation deck
- `RainRoute-NYC-Vortrag.pdf`: exported presentation PDF

Large generated data files are intentionally not included in Git. The project downloads and imports the data through the scripts in `A5/p5`.

Quick start on Windows PowerShell:

```powershell
cd .\A5\p5
.\run-local.cmd
```

This starts Docker Desktop if needed, starts MongoDB and Neo4j, starts the Streamlit dashboard and opens both `http://localhost:8501` and `http://localhost:7476` in the browser.

PowerShell alternative:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-local.ps1
```

See `A5/p5/README.md` for the full setup, data model, import commands and presentation notes.
