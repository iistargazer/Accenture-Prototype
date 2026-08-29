"""
Semantic layer: the ONLY place that knows how raw tables map to canonical
KPI values. Everything downstream (detection, driver analysis) consumes
`compute_kpi_series()` output and never touches raw tables directly.
This is deliberate - it's what "governed KPI semantics" means in practice
for a prototype: one function per KPI, contract-driven, grain-reconciled.
"""
import pandas as pd
import yaml
from pathlib import Path
from dataclasses import dataclass, field

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
CONTRACTS_PATH = ROOT / "contracts" / "kpi_contracts.yaml"


def load_contracts() -> dict:
    with open(CONTRACTS_PATH) as f:
        return yaml.safe_load(f)["kpis"]


def load_sales() -> pd.DataFrame:
    df = pd.read_csv(DATA / "sales_daily.csv", parse_dates=["date"])
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.dayofweek, unit="D")
    return df


def load_marketing() -> pd.DataFrame:
    return pd.read_csv(DATA / "marketing_spend_weekly.csv", parse_dates=["week_start"])


def load_ops() -> pd.DataFrame:
    return pd.read_csv(DATA / "ops_monthly.csv")


@dataclass
class KpiSeries:
    kpi: str
    contract: dict
    weekly: pd.DataFrame          # columns: week_start, value  (and region if sliced)
    freshness: dict = field(default_factory=dict)   # source -> as-of date
    n_periods: int = 0


def compute_kpi_series(kpi_name: str, region: str | None = None, category: str | None = None) -> KpiSeries:
    """Reconciles source grain -> weekly analysis grain per the contract.
    `category` lets the KPI slice match the grain that driver_analysis
    operates on (e.g. isolate existing_A in East) - without it, movements
    can be diluted by categories the driver analysis isn't looking at."""
    contracts = load_contracts()
    if kpi_name not in contracts:
        raise ValueError(f"Unknown KPI '{kpi_name}' - not in kpi_contracts.yaml")
    contract = contracts[kpi_name]

    sales = load_sales()
    if region:
        sales = sales[sales["region"] == region]
    if category:
        sales = sales[sales["category"] == category]

    freshness = {"sales_daily": str(sales["date"].max().date())}

    if kpi_name == "revenue":
        weekly = sales.assign(revenue=sales.units * sales.price).groupby("week_start")["revenue"].sum().reset_index(name="value")

    elif kpi_name == "units_sold":
        weekly = sales.groupby("week_start")["units"].sum().reset_index(name="value")

    elif kpi_name == "avg_selling_price":
        g = sales.groupby("week_start").apply(
            lambda d: (d.units * d.price).sum() / d.units.sum(), include_groups=False
        )
        weekly = g.reset_index(name="value")

    elif kpi_name == "marketing_efficiency":
        rev = sales.assign(revenue=sales.units * sales.price).groupby("week_start")["revenue"].sum()
        mkt = load_marketing().groupby("week_start")["spend"].sum()
        freshness["marketing_spend_weekly"] = str(load_marketing()["week_start"].max().date())
        merged = pd.concat([rev, mkt], axis=1).dropna()
        merged["value"] = merged["revenue"] / merged["spend"]
        weekly = merged.reset_index()[["week_start", "value"]]

    elif kpi_name == "new_launch_revenue":
        nl = sales[sales["category"] == "new_launch"]
        weekly = nl.assign(revenue=nl.units * nl.price).groupby("week_start")["revenue"].sum().reset_index(name="value")

    else:
        raise NotImplementedError(f"No compute rule wired for '{kpi_name}'")

    weekly = weekly.sort_values("week_start").reset_index(drop=True)
    return KpiSeries(kpi=kpi_name, contract=contract, weekly=weekly,
                      freshness=freshness, n_periods=len(weekly))
