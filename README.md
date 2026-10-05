# Green Bond Compliance & Issuer Financial Health Screener
### Case: Goldwind 金风科技 (002202.SZ / 02208.HK)

Screens a Chinese green bond on two questions:
1. **Is the bond actually green?** Scored against the ICMA Green Bond Principles (GBP) and the PBoC 《绿色债券支持项目目录》.
2. **Can the issuer service the debt?** Interest coverage and leverage computed from audited financial statements.

Bond under review: **金风科技股份有限公司2026年度第二期绿色科技创新债券** (Goldwind 2026 Series 2 Green Technology Innovation Bond; short name 26金风科技MTN002(科创债), code 102683199). RMB 1 billion, 3+N perpetual medium-term note, issued 19 Aug 2026, coupon 2.00%, accounted for as equity. Pre-issuance green assessment by 联合赤道 (Lianhe Equator): grade G1.

> Student research project. Not investment advice. Not affiliated with Goldwind.

---

## Status

| Module | Description | Status |
|---|---|---|
| 1. Data collection | Annual financials from public sources, validated across providers | Done |
| 2. GBP compliance scorer | 0-2 checklist across the four GBP pillars | In progress (needs prospectus) |
| 3. LLM project classifier | Maps use-of-proceeds text to the 《绿色债券支持项目目录》 categories | Planned |
| 4. Issuer credit health | Interest coverage, Debt/EBITDA, leverage trend, adjusted view | Done (annual; LTM pending) |

---

## Data and validation

| Source | Used for |
|---|---|
| Sina Finance via `akshare` | Primary: income statement and balance sheet (CAS, A-share) |
| Eastmoney via `akshare` | Depreciation and amortisation (cash-flow statement) |
| `yfinance` (2208.HK) and Eastmoney HK | Cross-check only (IFRS, 2022-2025) |

- Key lines (revenue, pre-tax profit, interest expense, borrowings, D&A) were reconciled across providers for 2022-2025. See `notebooks/01_data_check.ipynb`.
- A-share (CAS) and H-share (IFRS) figures differ slightly (FY2025 revenue: 730.23 vs 727.82 亿元). CAS is used because the bond prospectus follows CAS.
- Total debt vs the prospectus's 有息债务 (RMB 326.90 / 347.93 / 324.32 亿 for 2025 / 2024 / 2023): bank borrowings match exactly. Our total is higher by 37.51 / 47.46 / 53.71 亿 because it also includes 租赁负债 (33.38 / 42.16 / 49.67 亿) and other non-current liabilities due within one year (4.13 / 5.29 / 4.04 亿). Bonds payable are zero in all three years.
- Units: 亿元 (100 million RMB). Annual rows are 31 December year-end, cumulative.
- 2016 has no 利息费用 in the source, so ratios cover **2017-2025**.

---

## Definitions

| Metric | Definition |
|---|---|
| EBIT | 利润总额 + 利息费用 |
| D&A | 固定资产折旧 + 无形资产摊销 + 长期待摊费用摊销 + 使用权资产折旧 |
| EBITDA | EBIT + D&A |
| Total debt (base) | 短期借款 + 一年内到期的非流动负债 + 长期借款 + 应付债券 + 租赁负债 |
| Total debt (broad) | Base + 长期应付款 |
| Interest coverage | EBIT / 利息费用 |
| Debt / EBITDA | Total debt / EBITDA (shown for base and broad) |
| Adjusted EBIT | EBIT − 投资收益 − 公允价值变动收益 |
| Adjusted EBITDA | Adjusted EBIT + D&A |
| Perpetuals | 其他权益工具 (renewable trust loans + perpetual MTNs, booked as equity) |

Chinese terms:

| 中文 | Pinyin | English |
|---|---|---|
| 利息费用 | lìxī fèiyòng | interest expense |
| 利润总额 | lìrùn zǒng'é | pre-tax profit |
| 投资收益 | tóuzī shōuyì | investment income |
| 公允价值变动收益 | gōngyǔn jiàzhí biàndòng shōuyì | fair-value gains |
| 应付债券 | yīngfù zhàiquàn | bonds payable |
| 租赁负债 | zūlìn fùzhài | lease liabilities |
| 长期应付款 | chángqī yīfùkuǎn | long-term payables |
| 募集说明书 | mùjí shuōmíngshū | offering prospectus |

---

## Preliminary observations (computed by `src/credit_ratios.py`)

| | 2023 | 2024 | 2025 |
|---|---|---|---|
| EBIT / interest, headline | 2.83x | 2.73x | 4.77x |
| Adj. EBIT / interest (ex-投资收益 and 公允价值变动收益) | 0.95x | 0.99x | 3.06x |
| Total debt / EBITDA, headline | 5.61x | 5.85x | 3.95x |
| Total debt / adj. EBITDA | 9.12x | 8.52x | 4.91x |
| (Total debt + perpetuals) / adj. EBITDA | 9.62x | 8.95x | 5.53x |
| Liabilities / assets, reported | 71.96% | 73.96% | 71.66% |
| Liabilities / assets incl. perpetuals | 73.39% | 75.24% | 74.45% |

- In 2023-2024, 投资收益 (RMB 2.25 bn and 1.96 bn) was about 58-59% of EBIT. Without it, interest coverage was about 1x versus a headline of 2.7-2.8x.
- FY2025 recovered on operating earnings: adjusted EBIT rose from about RMB 1.2 bn to 3.2 bn. Non-operating items did not drive it (投资收益 fell to RMB 0.73 bn while 公允价值变动收益 rose to RMB 1.08 bn).
- RMB 4.64 bn of perpetual instruments (其他权益工具) are booked as equity at FY2025 and are excluded from reported debt. Counting them lifts liabilities/assets from 71.66% to 74.45%.
- Caveats: treating all 投资收益 as non-core is conservative (it includes JV income and possibly wind-farm disposal gains; the breakdown in the annual-report notes was not checked), so the adjusted figures are a lower bound. Distributions on perpetuals are not added to interest, so coverage is still flattered.

---

## Known limitations

- Annual ratios only. No LTM figure yet.
- Goldwind's perpetual notes are booked in equity (其他权益工具: RMB 46.43 亿 at FY2025, incl. RMB 21.43 亿 renewable trust loans), so they are not in 应付债券 or in total debt. An adjusted-debt view that adds them is pending.
- 长期应付款 is mainly warranty retention (应付质量保证金) and finance-lease deposits, plus sale-leaseback payables (financing-like). It is excluded from base total debt; the broad version is shown as an upper bound.
- 租赁负债 only exists from the 2019 lease-standard change, which breaks comparability before 2019.
- Missing 应付债券, 租赁负债, 长期待摊费用摊销 and 使用权资产折旧 values are treated as 0.
- Cross-checks cover 2022-2025 only, because yfinance history is limited.

---

## Repository structure

```
data/
  raw/          provider downloads (gitignored, regenerate with the script)
  processed/    cleaned inputs and ratios (committed)
  prospectus/   bond prospectus extraction (planned)
  labels/       gold labels for the LLM classifier (planned)
notebooks/      01_data_check.ipynb: cross-provider validation
src/
  data_collection.py   module 1
  credit_ratios.py     module 4
docs/           research note (planned)
outputs/        charts, LLM response cache (planned)
```

## Reproduce

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

python src/data_collection.py   # writes data/raw and data/processed/goldwind_credit_inputs_annual.csv
python src/credit_ratios.py     # writes data/processed/goldwind_credit_ratios_annual.csv
```

Turn **VPN off** before running `data_collection.py`; Sina Finance requests fail with SSL errors otherwise.

## Roadmap

- [x] Adjusted EBIT/EBITDA and perpetuals-as-debt view
- [ ] LTM ratios (FY2025 + H1 2026 − H1 2025)
- [ ] Extract use of proceeds from the 募集说明书
- [ ] GBP scorer (rubric 0-2 per pillar)
- [ ] LLM classifier with gold labels, `temperature=0`, cached responses, logged model and prompt version
- [ ] One-page research note