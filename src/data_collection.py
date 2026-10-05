"""Module 1 - Data collection for Goldwind (金风科技, 002202.SZ).

Pulls annual financial statements prepared under Chinese Accounting Standards
(CAS, 中国会计准则), the same basis as the bond prospectus (募集说明书), and builds
the input table for the credit ratios in module 4.

Sources (all via akshare):
    Sina       - income statement (利润表) and balance sheet (资产负债表)
    Eastmoney  - cash flow statement (现金流量表), only for depreciation & amortization

Network note: turn the VPN OFF when running (Sina rejects connections through a VPN).
Unit of all output figures: 亿元 (100 million RMB).

Glossary (English <-> 中文)
    Revenue                  营业总收入
    Pretax profit            利润总额
    Interest expense         利息费用
    EBIT                     息税前利润
    D&A                      折旧摊销 (depreciation & amortization)
    EBITDA                   息税折旧摊销前利润
    Cash                     货币资金
    Total debt               总债务
    Total liabilities        负债合计
    Total assets             资产总计
"""
from pathlib import Path

import akshare as ak
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]   # repo root, independent of the working directory
RAW = ROOT / "data" / "raw"                  # git-ignored
PROCESSED = ROOT / "data" / "processed"      # committed to Git
YI = 1e8                                     # 1 亿 = 100 million

# Column names are kept exactly as the providers return them (Chinese on purpose),
# and mapped to English names used everywhere else in the project.
SINA_DATE_COL = "报告日"                      # report date
SINA_INCOME_COLS = {                         # income statement (利润表)
    "营业总收入": "revenue",                   # total operating revenue
    "利润总额": "pretax_profit",               # total profit = profit before tax
    "利息费用": "interest_expense",            # interest expense
    "投资收益": "investment_income",           # investment income (excluded in adjusted view)
    "公允价值变动收益": "fair_value_gain",      # fair-value gains (excluded in adjusted view)
}
SINA_BALANCE_COLS = {                        # balance sheet (资产负债表)
    "货币资金": "cash",                                      # cash and cash equivalents
    "短期借款": "short_term_borrowings",                     # short-term borrowings
    "一年内到期的非流动负债": "current_portion_noncurrent",  # non-current liabilities due within 1 year
    "长期借款": "long_term_borrowings",                      # long-term borrowings
    "应付债券": "bonds_payable",                             # bonds payable
    "租赁负债": "lease_liabilities",                         # lease liabilities (non-current)
    "长期应付款": "long_term_payables",                      # long-term payables (not in base total debt)
    "负债合计": "total_liabilities",                         # total liabilities
    "资产总计": "total_assets",                              # total assets
    "其他权益工具": "other_equity_instruments",              # perpetual notes + renewable trust loans booked as equity
}
EASTMONEY_DATE_COL = "REPORT_DATE"
EASTMONEY_CASHFLOW_COLS = {                  # cash flow statement (现金流量表), supplementary items
    "FA_IR_DEPR": "dep_fixed_assets",                # 固定资产折旧 (fixed asset depreciation)
    "IA_AMORTIZE": "amort_intangibles",              # 无形资产摊销 (intangible asset amortization)
    "LPE_AMORTIZE": "amort_lt_prepaid",              # 长期待摊费用摊销 (long-term prepaid expense amortization)
    "USERIGHT_ASSET_AMORTIZE": "dep_rou_assets",     # 使用权资产折旧 (right-of-use asset depreciation)
}

# Labels for the console printout only (CSV keeps the English snake_case names).
DISPLAY_LABELS = {
    "revenue": "Revenue (营业总收入)",
    "pretax_profit": "Pretax profit (利润总额)",
    "interest_expense": "Interest expense (利息费用)",
    "investment_income": "Investment income (投资收益)",
    "fair_value_gain": "Fair-value gains (公允价值变动收益)",
    "ebit": "EBIT (息税前利润)",
    "da": "D&A (折旧摊销)",
    "ebitda": "EBITDA (息税折旧摊销前利润)",
    "cash": "Cash (货币资金)",
    "total_debt": "Total debt (总债务)",
    "long_term_payables": "Long-term payables (长期应付款)",
    "total_debt_broad": "Total debt incl. LT payables (含长期应付款总债务)",
    "total_liabilities": "Total liabilities (负债合计)",
    "total_assets": "Total assets (资产总计)",
    "other_equity_instruments": "Other equity instruments (其他权益工具, perpetuals)",
}


def fetch_sina(statement: str) -> pd.DataFrame:
    """statement: '利润表' (income statement) or '资产负债表' (balance sheet)."""
    return ak.stock_financial_report_sina(stock="sz002202", symbol=statement)


def fetch_cashflow_em() -> pd.DataFrame:
    """Cash flow statement (现金流量表) from Eastmoney."""
    return ak.stock_cash_flow_sheet_by_report_em(symbol="SZ002202")


def annual_rows(df: pd.DataFrame, date_col: str, col_map: dict) -> pd.DataFrame:
    """Keep only 31 December rows (annual reports, 年报), index = year, values in 亿元.

    Sina and Eastmoney report cumulative figures (Q1, 半年报, 三季报, 年报), so the
    December row is the full-year number. `col_map` maps provider column -> English name.
    """
    missing = [c for c in [date_col, *col_map] if c not in df.columns]
    if missing:
        raise KeyError(f"Columns not found in provider data: {missing}")
    ymd = df[date_col].astype(str).str.replace("-", "", regex=False).str[:8]  # YYYYMMDD
    d = df.copy()
    d["year"] = ymd.str[:4].astype(int)
    d = d[ymd.str[4:] == "1231"]
    out = d.set_index("year")[list(col_map)].apply(pd.to_numeric, errors="coerce") / YI
    out = out.rename(columns=col_map)
    return out[~out.index.duplicated(keep="first")].sort_index()


def build_credit_inputs(is_df, bs_df, cf_df) -> pd.DataFrame:
    """Annual inputs for the credit ratios (unit: 亿元), newest year first."""
    income = annual_rows(is_df, SINA_DATE_COL, SINA_INCOME_COLS)
    balance = annual_rows(bs_df, SINA_DATE_COL, SINA_BALANCE_COLS)
    cashflow = annual_rows(cf_df, EASTMONEY_DATE_COL, EASTMONEY_CASHFLOW_COLS)
    t = income.join(balance, how="outer").join(cashflow, how="outer")

    # EBIT (息税前利润) = pretax profit (利润总额) + interest expense (利息费用).
    # Same definition as yfinance's EBIT (matched for 2022-2025).
    t["ebit"] = t["pretax_profit"] + t["interest_expense"]

    # D&A (折旧摊销): the two core components must exist; the other two are treated as 0
    # when missing. ASSUMPTION: right-of-use assets (使用权资产) did not exist before the new
    # lease standard. Note: yfinance omits 长期待摊费用摊销 (amort_lt_prepaid); it is <1% of EBITDA.
    core_da = t[["dep_fixed_assets", "amort_intangibles"]].sum(axis=1, skipna=False)
    other_da = t[["amort_lt_prepaid", "dep_rou_assets"]].sum(axis=1)
    t["da"] = core_da + other_da
    t["ebitda"] = t["ebit"] + t["da"]

    # Total debt (总债务) = short-term borrowings (短期借款) + non-current liabilities due within
    # 1 year (一年内到期的非流动负债) + long-term borrowings (长期借款) + bonds payable (应付债券)
    # + lease liabilities (租赁负债). Lease liabilities are included because EBITDA adds back
    # right-of-use depreciation. ASSUMPTION: missing bonds payable / lease liabilities = 0.
    core_debt = t[["short_term_borrowings", "current_portion_noncurrent",
                   "long_term_borrowings"]].sum(axis=1, skipna=False)
    other_debt = t[["bonds_payable", "lease_liabilities"]].sum(axis=1)
    t["total_debt"] = core_debt + other_debt
    
    # Broad definition: also include long-term payables (长期应付款), whose interest-bearing
    # share is unknown (check the annual report notes). Missing = 0.
    t["total_debt_broad"] = t["total_debt"] + t["long_term_payables"].fillna(0)

    return t[list(DISPLAY_LABELS)].sort_index(ascending=False)


def to_display(table: pd.DataFrame, n_years: int = 10) -> pd.DataFrame:
    """Latest `n_years` as columns, bilingual row labels (readable in the terminal)."""
    return table.head(n_years).T.rename(index=DISPLAY_LABELS)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    is_df = fetch_sina("利润表")
    bs_df = fetch_sina("资产负债表")
    cf_df = fetch_cashflow_em()
    for name, df in [("IS_sina", is_df), ("BS_sina", bs_df), ("CF_em", cf_df)]:
        df.to_csv(RAW / f"goldwind_{name}.csv", index=False, encoding="utf-8-sig")

    table = build_credit_inputs(is_df, bs_df, cf_df)
    table.to_csv(PROCESSED / "goldwind_credit_inputs_annual.csv", encoding="utf-8-sig")
    print("Unit: 亿元 (100 million RMB)")
    print(to_display(table).to_string(float_format="{:,.2f}".format))


if __name__ == "__main__":
    main()