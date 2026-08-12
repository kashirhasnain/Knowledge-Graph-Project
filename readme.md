# HIV/AIDS Death-Rate Knowledge Graph

## How to run
1. `pip install rdflib pandas matplotlib`
2. `cd "2-construction" && python3 build_kg.py`  -> builds hiv_kg.ttl from the 6 source CSVs
3. `cd ../4-logic && python3 queries.py`         -> runs the 5 SPARQL queries/rules, writes region_year_totals.csv, country_trends.csv, hiv_kg_with_trends.ttl
4. `cd ../5-reflection && python3 make_chart.py` -> generates the two charts used in Section 4.1 of the report

## Folders
- `2-construction/` — source CSVs, ontology + ETL script (build_kg.py), resulting hiv_kg.ttl
- `4-logic/` — SPARQL queries/rules (queries.py) and their outputs
- `5-reflection/` — chart generation script and output PNGs

## Data source
WHO/UNAIDS HIV/AIDS statistics, cleaned CSVs via Kaggle:
https://www.kaggle.com/datasets/imdevskp/hiv-aids-dataset
(raw source: UNICEF DATA)
