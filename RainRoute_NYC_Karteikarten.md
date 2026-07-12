# RainRoute NYC Karteikarten

## Folie 1 - Titel
RainRoute NYC ist unser NoSQL- und Big-Data-Praktikumsprojekt. Die Leitidee ist einfach: Wir verbinden New Yorker Yellow-Taxi-Fahrten mit historischen Wetterdaten und untersuchen, ob sich Nachfrage, Dauer und Routenmuster bei Regen, Schnee oder trockenem Wetter sichtbar unterscheiden.

## Folie 2 - Worum es in der Demo geht
Die Präsentation folgt einem roten Faden: Erst die Forschungsfrage, dann die Datenbasis, danach das Datenmodell mit MongoDB und Neo4j, anschließend die Live-Demo im Streamlit-Dashboard. Wichtig ist: Wir zeigen keine endgültige Kausalstudie, sondern eine reproduzierbare explorative Analyse.

## Folie 3 - Leitfrage
Die zentrale Frage lautet: Verändert Wetter die Taxinutzung in New York? Dafür betrachten wir drei Perspektiven. Erstens die Nachfrage, also wie viele Fahrten bei welcher Wetterlage auftreten. Zweitens Dauer und Geschwindigkeit. Drittens Start-Ziel-Routen, weil schlechtes Wetter nicht überall gleich wirken muss.

## Folie 4 - Datenquellen
Die Demo kombiniert drei heterogene Datenquellen. Die NYC TLC liefert die Yellow-Taxi-Fahrten als Parquet-Dateien. Open-Meteo liefert historische Wetterdaten auf Stundenebene. Die Taxi-Zonen liefern die räumliche Zuordnung, damit Pickup- und Dropoff-IDs im Dashboard verständlich werden.

## Folie 5 - Pipeline
Die Pipeline startet mit Download-Skripten, bereinigt danach unplausible Fahrten und verbindet jede Fahrt mit der passenden Wetterstunde. Danach werden Detaildaten in MongoDB geschrieben und aggregierte Routenbeziehungen nach Neo4j importiert. Das Dashboard greift anschließend auf beide Datenbanken zu.

## Folie 6 - Zwei Datenbanken
MongoDB eignet sich für flexible Dokumente: einzelne Fahrten, Wetterstunden und Zonen lassen sich gut filtern und aggregieren. Neo4j eignet sich für Beziehungen: Zonen werden zu Knoten und häufige Fahrten zwischen Zonen zu Kanten. Genau diese Trennung ist der Kern der Modellierung.

## Folie 7 - Demo-Datensatz
Für die Demo wurden je 200.000 Rohfahrten aus Januar, Juli und Dezember 2025 importiert. Nach der Bereinigung bleiben 568.963 Fahrten. Der Graph enthält 265 Zonen und 36.280 aggregierte Routenbeziehungen. Das ist groß genug für Muster, aber klein genug für eine stabile Live-Demo.

## Folie 8 - Wettermix
Die Verteilung der Wetterlagen ist für die Interpretation wichtig. Rund 70,6 Prozent der Demo-Fahrten liegen bei trockenem Wetter, 28,5 Prozent bei Regen und nur 0,9 Prozent bei Schnee. Besonders Schnee darf deshalb nicht überinterpretiert werden.

## Folie 9 - Erste Ergebnisse
Die ersten Ergebnisse zeigen Muster, aber keine bewiesenen Ursachen. Regen verändert die Vergleichsbasis und muss deshalb nach Monat und Tageszeit betrachtet werden. Für Routen ist wichtig, gleiche Start- und Zielzonen zu vergleichen. Der Wert des Projekts liegt darin, diese Filter live sichtbar zu machen.

## Folie 10 - Live-Demo
In der Live-Demo öffne ich zuerst die Übersicht mit Gesamtzahlen. Danach wechsle ich zwischen trockenem Wetter und Regen. Dann zeige ich die Routentabelle und den Neo4j-Teil. Am Ende vergleiche ich zwei Szenarien nebeneinander, zum Beispiel Monat, Wetterlage und Tageszeit.

## Folie 11 - Learnings
Die größten Learnings kamen aus der Datenarbeit. Zeitstempel müssen sauber behandelt werden, sonst passt Wetter nicht zur Fahrt. Ausreißer bei Dauer, Distanz oder Preis verzerren Auswertungen. Außerdem ist Neo4j erst dann sinnvoll, wenn man Einzelfahrten zu stabilen Routenbeziehungen aggregiert.

## Folie 12 - Erfüllung der Aufgabenstellung
Die Kernanforderungen sind erfüllt: zwei NoSQL-Datenbanken, heterogene Datenquellen, reproduzierbarer Import, Dashboard, Tests und Dokumentation. Für die finale Abgabe sollte die LLM-Nutzung noch einmal vollständig dokumentiert werden.

## Folie 13 - Fazit
RainRoute NYC zeigt, wie Wetterdaten und Taxi-Fahrten gemeinsam ausgewertet werden können. MongoDB übernimmt die flexible Detailanalyse, Neo4j macht Routenbeziehungen sichtbar. Der nächste sinnvolle Schritt wäre ein vollständiger Monatsimport und eine noch stärkere visuelle Auswertung im Dashboard.
