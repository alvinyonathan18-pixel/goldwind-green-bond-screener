"""Module 4 - Issuer financial health: credit ratios for Goldwind (金风科技, 002202.SZ).

Reads the annual input table built by data_collection.py (unit: 亿元) and computes the
ratios that matter for a bond issuer, as opposed to the equity-valuation view of a DCF.

Ratios
    Interest coverage          EBIT / interest expense        利息保障倍数
    EBITDA interest coverage   EBITDA / interest expense      EBITDA利息保障倍数
    Total debt / EBITDA        base and broad definitions     总债务/EBITDA
    Net debt / EBITDA          (total debt - cash) / EBITDA   净债务/EBITDA
    Liabilities / assets (%)   total liabilities / assets     资产负债率

Base total debt excludes long-term payables (长期应付款); the broad version includes them.
Report both until the annual report notes show whether 长期应付款 is interest-bearing.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
INPUT_CSV = PROCESSED / "goldwind_credit_inputs_annual.csv"
OUTPUT_CSV = PROCESSED / "goldwind_credit_ratios_annual.csv"

DISPLAY_LABELS = {
    "interest_coverage": "Interest coverage, EBIT/interest (利息保障倍数, x)",
    "ebitda_interest_coverage": "EBITDA/interest (EBITDA利息保障倍数, x)",
    "debt_to_ebitda": "Total debt/EBITDA (总债务/EBITDA, x)",
    "debt_to_ebitda_broad": "Total debt incl. LT payables/EBITDA (含长期应付款, x)",
    "debt_to_ebitda_change": "Change in debt/EBITDA vs prior year (同比变化, x)",
    "net_debt_to_ebitda": "Net debt/EBITDA (净债务/EBITDA, x)",
    "liabilities_to_assets_pct": "Liabilities/assets (资产负债率, %)",
}


def load_inputs(path: Path | None = None) -> pd.DataFrame:
    path = INPUT_CSV if path is None else path
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run src/data_collection.py first")
    return pd.read_csv(path, index_col="year")


def positive(s: pd.Series) -> pd.Series:
    """A ratio on a zero or negative denominator is meaningless, so return NaN there."""
    return s.where(s > 0)


def compute_ratios(x: pd.DataFrame) -> pd.DataFrame:
    """x: annual inputs in 亿元, indexed by year. Returns ratios, newest year first."""
    ebitda = positive(x["ebitda"])
    interest = positive(x["interest_expense"])
    r = pd.DataFrame(index=x.index)
    r["interest_coverage"] = x["ebit"] / interest
    r["ebitda_interest_coverage"] = x["ebitda"] / interest
    r["debt_to_ebitda"] = x["total_debt"] / ebitda
    r["debt_to_ebitda_broad"] = x["total_debt_broad"] / ebitda
    r["net_debt_to_ebitda"] = (x["total_debt"] - x["cash"]) / ebitda
    r["liabilities_to_assets_pct"] = x["total_liabilities"] / x["total_assets"] * 100
    # Year-over-year change needs ascending order; the assignment re-aligns on the year index.
    r["debt_to_ebitda_change"] = r.sort_index()["debt_to_ebitda"].diff()
    return r[list(DISPLAY_LABELS)].sort_index(ascending=False)


def to_display(ratios: pd.DataFrame, n_years: int = 10) -> pd.DataFrame:
    return ratios.head(n_years).T.rename(index=DISPLAY_LABELS)


def main() -> None:
    ratios = compute_ratios(load_inputs())
    ratios.to_csv(OUTPUT_CSV, encoding="utf-8-sig")
    print(to_display(ratios).to_string(float_format="{:,.2f}".format))


if __name__ == "__main__":
    main()