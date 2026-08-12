import os
import csv
from rdflib import Graph, Namespace, Literal, XSD, URIRef, RDF

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
kg_path = os.path.join(BASE_DIR, "hiv_kg.ttl")
if not os.path.exists(kg_path):
    kg_path = os.path.join(BASE_DIR, "..", "2-construction", "hiv_kg.ttl")

HIV = Namespace("http://example.org/hiv-kg#")
g = Graph()
g.parse(kg_path, format="turtle")
g.bind("hiv", HIV)

print("="*70)
print("Q1 - BASIC PATTERN QUERY: HIV deaths reported for Kenya, all years")
print("="*70)
q1 = """
PREFIX hiv: <http://example.org/hiv-kg#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?year ?count WHERE {
  ?c a hiv:Country ; rdfs:label "Kenya" .
  ?obs a hiv:DeathObservation ; hiv:ofCountry ?c ; hiv:inYear ?y ; hiv:count ?count .
  ?y hiv:yearValue ?year .
} ORDER BY ?year
"""
for row in g.query(q1):
    print(row.year, int(float(row["count"])))

print()
print("="*70)
print("Q2 - AGGREGATION: total & mean HIV deaths per WHO Region, per year")
print("="*70)
q2 = """
PREFIX hiv: <http://example.org/hiv-kg#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?regionLabel ?year (SUM(?count) AS ?totalDeaths) (AVG(?count) AS ?meanDeaths) (COUNT(?obs) AS ?nCountries) WHERE {
  ?obs a hiv:DeathObservation ; hiv:ofCountry ?c ; hiv:inYear ?y ; hiv:count ?count .
  ?c hiv:locatedIn ?region .
  ?region rdfs:label ?regionLabel .
  ?y hiv:yearValue ?year .
} GROUP BY ?regionLabel ?year ORDER BY ?regionLabel ?year
"""
rows2 = list(g.query(q2))
region_year_csv = os.path.join(BASE_DIR, "region_year_totals.csv")
with open(region_year_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Region","Year","TotalDeaths","MeanDeaths","NCountries"])
    for row in rows2:
        w.writerow([row.regionLabel, row.year, int(float(row.totalDeaths)), round(float(row.meanDeaths),1), int(float(row.nCountries))])
        print(row.regionLabel, row.year, int(float(row.totalDeaths)), round(float(row.meanDeaths),1))

print()
print("="*70)
print("Q3 - RECURSIVE PROPERTY PATH: everything a Country transitively belongs to")
print("     (Country -[locatedIn|partOf]+-> ... -> Global)")
print("="*70)
q3 = """
PREFIX hiv: <http://example.org/hiv-kg#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?countryLabel ?ancestor WHERE {
  ?c a hiv:Country ; rdfs:label ?countryLabel .
  FILTER(?countryLabel = "Rwanda")
  ?c (hiv:locatedIn|hiv:partOf)+ ?anc .
  OPTIONAL { ?anc rdfs:label ?lbl }
  BIND(COALESCE(?lbl, STR(?anc)) AS ?ancestor)
}
"""
for row in g.query(q3):
    print(row.countryLabel, "->", row.ancestor)

print()
print("="*70)
print("Q4 - CONSTRUCT (rule): classify countries by death-rate trend 2000->2018")
print("     creates new hiv:hasTrend edges + hiv:TrendClassification nodes")
print("="*70)
def deaths_for_year(year_str):
    q = f"""
    PREFIX hiv: <http://example.org/hiv-kg#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?c ?label ?d WHERE {{
      ?o a hiv:DeathObservation ; hiv:ofCountry ?c ; hiv:inYear ?y ; hiv:count ?d .
      ?y hiv:yearValue "{year_str}"^^<http://www.w3.org/2001/XMLSchema#gYear> .
      ?c rdfs:label ?label .
    }}
    """
    return {str(r.label): (r.c, float(r.d)) for r in g.query(q)}

d2000_map = deaths_for_year("2000")
d2018_map = deaths_for_year("2018")

results = []
for label, (c_uri, d0) in list(d2000_map.items()):
    if label not in d2018_map:
        continue
    row_c, d18 = d2018_map[label]
    class R: pass
    row = R(); row.c = c_uri; row.label = label; row.d2000 = d0; row.d2018 = d18
    d0, d18 = float(row.d2000), float(row.d2018)
    if d0 == 0: continue
    pct = (d18 - d0) / d0 * 100
    if pct <= -30:
        trend = "StronglyImproved"
    elif pct < 0:
        trend = "Improved"
    elif pct <= 30:
        trend = "Stable"
    else:
        trend = "Worsened"
    results.append((str(row.label), d0, d18, pct, trend))
    # materialize the new triples into the graph (this is the "rule" firing)
    c_uri = row.c
    g.add((c_uri, HIV.hasTrend, HIV[trend]))
    g.add((HIV[trend], RDF.type, HIV.TrendClassification))

results.sort(key=lambda r: r[3])
print(f"{'Country':25s} {'2000':>8s} {'2018':>8s} {'%chg':>8s}  trend")
for label, d0, d18, pct, trend in results:
    print(f"{label:25s} {d0:8.0f} {d18:8.0f} {pct:8.1f}  {trend}")

country_trends_csv = os.path.join(BASE_DIR, "country_trends.csv")
with open(country_trends_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Country","Deaths2000","Deaths2018","PercentChange","Trend"])
    for label, d0, d18, pct, trend in results:
        w.writerow([label, d0, d18, round(pct,1), trend])

# Verify new triples actually exist in the graph now
q4_check = """
PREFIX hiv: <http://example.org/hiv-kg#>
SELECT (COUNT(*) AS ?n) WHERE { ?c hiv:hasTrend ?t }
"""
print("\nNew hasTrend edges materialized in graph:", int(list(g.query(q4_check))[0].n))
out_ttl_trends = os.path.join(BASE_DIR, "hiv_kg_with_trends.ttl")
g.serialize(destination=out_ttl_trends, format="turtle")

print()
print("="*70)
print("Q5 - ASK/verification: does ART coverage correlate with fewer deaths?")
print("     (quick check used narratively in Reflection)")
print("="*70)
q5 = """
PREFIX hiv: <http://example.org/hiv-kg#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?label ?art WHERE {
  ?c a hiv:Country ; rdfs:label ?label .
  ?c hiv:hasTrend hiv:StronglyImproved .
  ?a a hiv:ARTCoverageObservation ; hiv:ofCountry ?c ; hiv:count ?art .
} ORDER BY DESC(?art)
"""
art_vals = [float(r.art) for r in g.query(q5)]
if art_vals:
    print(f"Mean ART coverage among 'StronglyImproved' countries: {sum(art_vals)/len(art_vals):.1f}%  (n={len(art_vals)})")

q5b = """
PREFIX hiv: <http://example.org/hiv-kg#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?label ?art WHERE {
  ?c a hiv:Country ; rdfs:label ?label .
  ?c hiv:hasTrend hiv:Worsened .
  ?a a hiv:ARTCoverageObservation ; hiv:ofCountry ?c ; hiv:count ?art .
}
"""
art_vals_w = [float(r.art) for r in g.query(q5b)]
if art_vals_w:
    print(f"Mean ART coverage among 'Worsened' countries: {sum(art_vals_w)/len(art_vals_w):.1f}%  (n={len(art_vals_w)})")

