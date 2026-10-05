# Green Bond Compliance & Issuer Financial Health Screener
### Case: Goldwind 金风科技 (002202.SZ / 02208.HK)

Screens a Chinese green bond on two questions:
1. **Is the bond actually green?** Scored against the ICMA Green Bond Principles (GBP) and the PBoC 《绿色债券支持项目目录》.
2. **Can the issuer service the debt?** Interest coverage and leverage computed from audited financial statements.

Bond under review: **2026年度第一期绿色科技创新债券** (Goldwind, 2026 Series 1 Green Technology Innovation Bond).

> Student research project. Not investment advice. Not affiliated with Goldwind.

---

## Status

| Module | Description | Status |
|---|---|---|
| 1. Data collection | Annual financials from public sources, validated across providers | Done |
| 2. GBP compliance scorer | 0-2 checklist across the four GBP pillars | In progress (needs prospectus) |
| 3. LLM project classifier | Maps use-of-proceeds text to the 《绿色债券支持项目目录》 categories | Planned |
| 4. Issuer credit health | Interest coverage, Debt/EBITDA, leverage trend | Done (headline); adjusted view pending |

---

## Data and validation

| Source | Used for |
|---|---|
| Sina Finance via `akshare` | Primary: income statement and balance sheet (CAS, A-share) |
| Eastmoney via `akshare` | Depreciation and amortisation (cash-flow statement) |
| `yfinance` (2208.HK) and Eastmoney HK | Cross-check only (IFRS, 2022-2025) |

- Key lines (revenue, pre-tax profit, interest expense, borrowings, D&A) were reconciled across providers for 2022-2025. See `notebooks/01_data_check.ipynb`.
- A-share (CAS) and H-share (IFRS) figures differ slightly (FY2025 revenue: 730.23 vs 727.82 亿元). CAS is used because the bond prospectus follows CAS.
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

## Preliminary observations (PENDING: not yet reproducible from committed code)

> Move this block into the main findings only after the adjusted-ratio columns are committed.

- Headline EBIT includes 投资收益 and 公允价值变动收益, which are not operating earnings. Excluding both, FY2023-2024 interest coverage is roughly 0.94-0.99x and Debt/EBITDA roughly 8-9x.
- The FY2025 improvement in headline coverage is partly driven by 公允价值变动收益 rising from 1.55 to 10.82 亿元.
- Treating 投资收益 as non-core is a conservative assumption. The breakdown in the annual-report notes (年报附注) has not been checked yet.

---

## Known limitations

- Annual ratios only. No LTM figure yet, so the 2026 bond is not reflected: the 2026-06-30 balance sheet still shows 应付债券 at 0.
- Whether 长期应付款 bears interest is unverified, so both base and broad Debt/EBITDA are reported.
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

- [ ] Adjusted EBIT/EBITDA (excluding 投资收益 and 公允价值变动收益)
- [ ] LTM ratios (FY2025 + H1 2026 − H1 2025)
- [ ] Extract use of proceeds from the 募集说明书
- [ ] GBP scorer (rubric 0-2 per pillar)
- [ ] LLM classifier with gold labels, `temperature=0`, cached responses, logged model and prompt version
- [ ] One-page research note