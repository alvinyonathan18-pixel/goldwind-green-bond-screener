"""Module 4 (extension) - LTM credit ratios for Goldwind (金风科技) as of 30 June 2026.

LTM (last twelve months, 滚动十二个月) for flow items = FY2025 + H1 2026 - H1 2025.
Balance-sheet items are taken at 30 June 2026. FY2025 comes from the annual inputs table
built by data_collection.py, so every definition (EBIT, D&A, total debt) is identical to
the annual ratios in credit_ratios.py.

Source of the H1 figures: Goldwind 2026 half-year report (2026年半年度报告), UNAUDITED,
https://static.cninfo.com.cn/finalpage/2026-08-26/1225504212.PDF
    income statement  pp. 58-59   (利润表: 利润总额, 利息费用, 投资收益, 公允价值变动收益)
    balance sheet     pp. 53-55   (资产负债表)
    D&A schedule      p. 170      (现金流量表补充资料)
All figures below are in yuan (元), exactly as printed in the report.

Run:  python src/credit_ratios_ltm.py   (needs data_collection.py and credit_ratios.py run first)
"""
import pandas as pd

from credit_ratios import INPUT_CSV, OUTPUT_CSV, PROCESSED, compute_ratios, to_display

YI = 1e8
FY = 2025
LTM_OUTPUT_CSV = PROCESSED / "goldwind_credit_ratios_ltm.csv"

# Flow items: (H1 2026, H1 2025) in yuan.
H1_FLOWS = {
    "pretax_profit": (2_475_991_658.19, 2_107_383_250.14),      # 利润总额
    "interest_expense": (463_970_992.34, 531_179_978.02),       # 财务费用: 其中 利息费用
    "investment_income": (323_067_008.67, 245_630_035.61),      # 投资收益
    "fair_value_gain": (-31_927_382.83, 313_234_732.84),        # 公允价值变动收益
    # D&A = fixed assets + investment property + right-of-use + intangibles + LT prepaid (p. 170),
    # the same five components as data_collection.py (FA_IR_DEPR already includes investment property).
    "da": (
        1_532_107_025.65 + 138_316.64 + 171_141_601.09 + 328_612_742.48 + 50_880_829.11,
        1_396_211_482.14 + 138_316.64 + 96_732_093.17 + 309_218_640.22 + 41_958_242.84,
    ),
}

# Balance sheet at 30 June 2026, yuan (pp. 53-55).
BALANCE_2026H1 = {
    "cash": 11_296_346_097.25,                    # 货币资金
    "short_term_borrowings": 1_380_174_098.84,    # 短期借款
    "current_portion_noncurrent": 4_612_173_158.57,  # 一年内到期的非流动负债
    "long_term_borrowings": 29_702_667_602.85,    # 长期借款
    "bonds_payable": 0.0,                         # 应付债券
    "lease_liabilities": 3_436_479_677.17,        # 租赁负债
    "long_term_payables": 3_956_889_954.62,       # 长期应付款
    "total_liabilities": 122_723_620_777.21,      # 负债合计
    "total_assets": 170_908_774_936.18,           # 资产总计
    "other_equity_instruments": 5_043_000_000.00,  # 其他权益工具 (perpetuals)
}


def check_fy_inputs(fy: pd.Series) -> None:
    """Fail loudly if the provider's FY2025 differs from the audited figures in the prospectus."""
    expected = {"pretax_profit": 39.8899, "interest_expense": 10.5683, "revenue": 730.2348}
    for k, v in expected.items():
        if abs(fy[k] - v) > 0.01:
            raise ValueError(f"FY{FY} {k} = {fy[k]:.4f} 亿元, prospectus says {v:.4f}")


def build_ltm_row() -> pd.DataFrame:
    fy = pd.read_csv(INPUT_CSV, index_col="year").loc[FY]
    check_fy_inputs(fy)
    row = {k: fy[k] + (h26 - h25) / YI for k, (h26, h25) in H1_FLOWS.items()}
    row["ebit"] = row["pretax_profit"] + row["interest_expense"]
    row["ebitda"] = row["ebit"] + row["da"]

    b = {k: v / YI for k, v in BALANCE_2026H1.items()}
    row["cash"] = b["cash"]
    row["total_debt"] = (b["short_term_borrowings"] + b["current_portion_noncurrent"]
                         + b["long_term_borrowings"] + b["bonds_payable"] + b["lease_liabilities"])
    row["total_debt_broad"] = row["total_debt"] + b["long_term_payables"]
    row["total_liabilities"] = b["total_liabilities"]
    row["total_assets"] = b["total_assets"]
    row["other_equity_instruments"] = b["other_equity_instruments"]
    return pd.DataFrame([row], index=pd.Index([FY + 1], name="year"))


def main() -> None:
    ltm = compute_ratios(build_ltm_row())
    fy = pd.read_csv(OUTPUT_CSV, index_col="year").loc[[FY]]
    ltm["debt_to_ebitda_change"] = ltm["debt_to_ebitda"].iloc[0] - fy["debt_to_ebitda"].iloc[0]
    ltm.to_csv(LTM_OUTPUT_CSV, encoding="utf-8-sig")

    both = pd.concat([ltm.rename(index={FY + 1: "LTM Jun-2026"}), fy.rename(index={FY: "FY2025"})])
    print("LTM = FY2025 + H1 2026 - H1 2025; H1 2026 is unaudited. Change row: LTM column is vs FY2025, FY2025 column is vs FY2024.")
    print(to_display(both).to_string(float_format="{:,.2f}".format))


if __name__ == "__main__":
    main()