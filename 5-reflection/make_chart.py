import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_csv_path(filename):
    p1 = os.path.join(BASE_DIR, filename)
    if os.path.exists(p1):
        return p1
    return os.path.join(BASE_DIR, "..", "4-logic", filename)

df = pd.read_csv(get_csv_path("region_year_totals.csv"))
regions = df["Region"].unique()
years = [2000, 2010, 2018]

fig, ax = plt.subplots(figsize=(7.5, 4.5))
colors = plt.cm.tab10.colors
for i, r in enumerate(regions):
    sub = df[df["Region"] == r].sort_values("Year")
    ax.plot(sub["Year"], sub["TotalDeaths"], marker="o", label=r, color=colors[i % 10], linewidth=2)

ax.set_xticks(years)
ax.set_xlabel("Year")
ax.set_ylabel("Total reported HIV/AIDS deaths (median estimate)")
ax.set_title("HIV/AIDS deaths by WHO Region, 2000–2018\n(derived from SPARQL aggregation query Q2 over the Knowledge Graph)")
ax.legend(loc="upper right", fontsize=8)
ax.grid(alpha=0.3)
plt.tight_layout()
chart1_path = os.path.join(BASE_DIR, "chart_region_trends.png")
plt.savefig(chart1_path, dpi=150)
print(f"Saved {chart1_path}")

# Second chart: trend classification counts
trends = pd.read_csv(get_csv_path("country_trends.csv"))
counts = trends["Trend"].value_counts().reindex(["StronglyImproved","Improved","Stable","Worsened"]).fillna(0)
fig2, ax2 = plt.subplots(figsize=(6,4))
bar_colors = ["#2E7D32","#66BB6A","#FFC107","#E53935"]
ax2.bar(counts.index, counts.values, color=bar_colors)
ax2.set_ylabel("Number of countries")
ax2.set_title("Country classification by HIV death-rate trend (2000→2018)\n(materialized via SPARQL rule Q4)")
for i,v in enumerate(counts.values):
    ax2.text(i, v+1, str(int(v)), ha="center")
plt.tight_layout()
chart2_path = os.path.join(BASE_DIR, "chart_trend_classification.png")
plt.savefig(chart2_path, dpi=150)
print(f"Saved {chart2_path}")

