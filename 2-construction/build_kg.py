
import os
import pandas as pd
import re
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, XSD

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HIV = Namespace("http://example.org/hiv-kg#")

def slug(s):
    return re.sub(r'[^A-Za-z0-9]+', '_', s.strip()).strip('_')

def parse_bracket(val):
    """'500[200-610]' -> median 500 (fallback to Count_median col instead)."""
    if pd.isna(val):
        return None
    val = str(val).strip()
    if val.lower() in ('na', 'nodata', 'no data', ''):
        return None
    m = re.match(r'^([\d.]+)', val)
    return float(m.group(1)) if m else None

g = Graph()
g.bind("hiv", HIV)

GLOBAL = HIV["Global"]
g.add((GLOBAL, RDF.type, HIV.Entity))
g.add((GLOBAL, RDFS.label, Literal("Global")))

country_uri = {}
region_uri = {}

def get_region(region_name):
    if region_name not in region_uri:
        u = HIV[f"region_{slug(region_name)}"]
        g.add((u, RDF.type, HIV.WHORegion))
        g.add((u, RDFS.label, Literal(region_name)))
        g.add((u, HIV.partOf, GLOBAL))
        region_uri[region_name] = u
    return region_uri[region_name]

def get_country(country_name, region_name):
    if country_name not in country_uri:
        u = HIV[f"country_{slug(country_name)}"]
        g.add((u, RDF.type, HIV.Country))
        g.add((u, RDFS.label, Literal(country_name)))
        r = get_region(region_name)
        g.add((u, HIV.locatedIn, r))
        country_uri[country_name] = u
    return country_uri[country_name]

def get_year(y):
    u = HIV[f"year_{y}"]
    g.add((u, RDF.type, HIV.Year))
    g.add((u, HIV.yearValue, Literal(int(y), datatype=XSD.gYear)))
    return u

# --- 1. Deaths (core dataset: Country, Year, Count, Count_median/min/max, WHO Region) ---
deaths_path = os.path.join(BASE_DIR, "no_of_deaths_by_country_clean.csv")
deaths = pd.read_csv(deaths_path)
deaths.columns = [c.strip() for c in deaths.columns]
deaths["Year"] = deaths["Year"].astype(str).str.strip()
n_death_obs = 0
for _, row in deaths.iterrows():
    if pd.isna(row["Count_median"]):
        continue
    c = get_country(row["Country"], row["WHO Region"])
    y = get_year(row["Year"])
    obs = HIV[f"deathobs_{slug(row['Country'])}_{row['Year']}"]
    g.add((obs, RDF.type, HIV.DeathObservation))
    g.add((obs, HIV.ofCountry, c))
    g.add((obs, HIV.inYear, y))
    g.add((obs, HIV["count"], Literal(float(row["Count_median"]), datatype=XSD.double)))
    if not pd.isna(row["Count_min"]):
        g.add((obs, HIV["countMin"], Literal(float(row["Count_min"]), datatype=XSD.double)))
    if not pd.isna(row["Count_max"]):
        g.add((obs, HIV["countMax"], Literal(float(row["Count_max"]), datatype=XSD.double)))
    g.add((c, HIV.hasDeathObservation, obs))
    n_death_obs += 1

# --- 2. People living with HIV (prevalence) ---
plhiv_path = os.path.join(BASE_DIR, "no_of_people_living_with_hiv_by_country_clean.csv")
plhiv = pd.read_csv(plhiv_path)
plhiv.columns = [c.strip() for c in plhiv.columns]
plhiv["Year"] = plhiv["Year"].astype(str).str.strip()
n_prev_obs = 0
for _, row in plhiv.iterrows():
    if pd.isna(row["Count_median"]):
        continue
    c = get_country(row["Country"], row["WHO Region"])
    y = get_year(row["Year"])
    obs = HIV[f"prevobs_{slug(row['Country'])}_{row['Year']}"]
    g.add((obs, RDF.type, HIV.PrevalenceObservation))
    g.add((obs, HIV.ofCountry, c))
    g.add((obs, HIV.inYear, y))
    g.add((obs, HIV["count"], Literal(float(row["Count_median"]), datatype=XSD.double)))
    g.add((c, HIV.hasPrevalenceObservation, obs))
    n_prev_obs += 1

# --- 3. ART coverage (snapshot, most recent - no Year column in source) ---
art_path = os.path.join(BASE_DIR, "art_coverage_by_country_clean.csv")
art = pd.read_csv(art_path)
art.columns = [c.strip() for c in art.columns]
n_art_obs = 0
for _, row in art.iterrows():
    cov = row["Estimated ART coverage among people living with HIV (%)_median"]
    if pd.isna(cov):
        continue
    c = get_country(row["Country"], row["WHO Region"])
    obs = HIV[f"artobs_{slug(row['Country'])}"]
    g.add((obs, RDF.type, HIV.ARTCoverageObservation))
    g.add((obs, HIV.ofCountry, c))
    g.add((obs, HIV["count"], Literal(float(cov), datatype=XSD.double)))
    g.add((c, HIV.hasARTCoverageObservation, obs))
    n_art_obs += 1

print(f"Countries: {len(country_uri)}, Regions: {len(region_uri)}")
print(f"Death observations: {n_death_obs}")
print(f"Prevalence observations: {n_prev_obs}")
print(f"ART coverage observations: {n_art_obs}")
print(f"Total triples: {len(g)}")

out_ttl = os.path.join(BASE_DIR, "hiv_kg.ttl")
g.serialize(destination=out_ttl, format="turtle")
print(f"Saved {out_ttl}")

