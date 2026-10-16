# Goldwind (002202.SZ): a RMB 1bn perpetual that barely moves the credit profile, with documentation weakest on use of proceeds

**Case bond:** 26金风科技MTN002 (102683199), RMB 1bn 3+N perpetual medium-term note, 2.00% coupon, issued 19 Aug 2026 · **Date:** 16 Oct 2026 · **Author:** Alvin Yonathan

*Student research project. No rating, price view or investment advice: this note assesses credit profile and disclosure, not value.*

## Key points (核心观点)

1. **Leverage is flat at about 4x.** Debt/EBITDA is 4.00x for the twelve months to 30 Jun 2026 (3.95x in FY2025), against 5.4-5.9x in 2022-2024.
2. **The 2025 improvement was earnings, not paydown.** Of the 1.90x fall in debt/EBITDA, 1.57x came from EBITDA (+37%). Part of the debt decline was a swap into perpetuals: debt plus perpetuals fell only about 1%.
3. **MTN002 changes little.** Across equity and debt treatment, debt/EBITDA stays within 3.90-4.11x. The prospectus's claimed 1.02-point fall in liabilities/assets could not be reproduced (we get 0.43-0.60 points).
4. **Green documentation scores 18/28 (64%).** Use of Proceeds is weakest at 5/10. Handling of unallocated proceeds (M3) and refinancing (U5) both score 0.

## 1. Credit profile

RMB 亿元 basis. LTM = twelve months to 30 Jun 2026 (H1 2026 unaudited).

| | FY2022 | FY2023 | FY2024 | FY2025 | LTM |
|---|---|---|---|---|---|
| Debt/EBITDA (x) | 5.44 | 5.61 | 5.85 | 3.95 | 4.00 |
| EBIT / interest (x) | 3.08 | 2.83 | 2.73 | 4.77 | 5.40 |
| Liabilities/assets (资产负债率, zī chǎn fù zhài lǜ) | 70.51% | 71.96% | 73.96% | 71.66% | 71.81% |
| Stress view: (debt + perpetuals) / EBITDA excl. investment and fair-value gains (x) | 8.72 | 9.62 | 8.95 | 5.53 | 5.37 |

![Credit ratios, FY2017-FY2025 and LTM](../outputs/charts/credit_trends.png)

Investment income and fair-value gains were 25-39% of EBITDA in 2021-2024 (peak 38.5% in 2023) and 15.8% in the LTM window. The stress view removes them and counts perpetuals (其他权益工具, qí tā quán yì gōng jù) as debt. It is a conservative bound, because part of 投资收益 (tóu zī shōu yì) may be recurring. EBITDA excluding those gains rose 60% in 2025 (46.4 to 74.3), so the recovery is not a gains effect. In the LTM window debt rose 7.4% against EBITDA +5.8%, which is why leverage has stopped improving.

## 2. Does MTN002 change it?

Pro-forma on the 30 Jun 2026 balance sheet, RMB 1bn issue.

| | No MTN002 | Equity, held as cash | Equity, repays debt | Reclassified as debt |
|---|---|---|---|---|
| Debt/EBITDA (x) | 4.00 | 4.00 | 3.90 | 4.11 |
| Liabilities/assets | 71.81% | 71.39% | 71.22% | 71.97% |
| EBIT / interest (x) | 5.40 | 5.40 | 5.40 | 5.29 |

The prospectus says the issuer intends to book the note as equity (pp. 6, 24) and lists reclassification as a financial liability among the risks (p. 19). The spread between treatments (0.21x) is small next to the 1.9x move between 2024 and 2025.

Prospectus p. 19 claims liabilities/assets falls by about 1.02 points versus FY2025. On the FY2025 balance sheet (p. 109) the result is -0.43 points if proceeds are held as cash and -0.60 points if they repay debt, and p. 143 itself says the effect is limited (影响不大). The gap is unexplained. Interest saved by repaying debt is not modelled.

## 3. Green bond documentation

14 criteria in four pillars of the Green Bond Principles, each scored 0/1/2 from the prospectus and the second-party opinion, with page-level evidence.

| Pillar | Score |
|---|---|
| Use of Proceeds | 5/10 |
| Process for project evaluation and selection | 4/6 |
| Management of Proceeds | 4/6 |
| Reporting (incl. external review) | 5/6 |
| **Total** | **18/28 (64%)** |

Both zero scores concern funds. Refinancing is allowed with no cap (U5, prospectus p. 35). There is no rule on temporary placement of unallocated proceeds (M3): the documents give only a supervised account (p. 34), a ban on financial and long-term investment of proceeds (p. 35) and semi-annual disclosure of unused proceeds (p. 174). Scores measure the quality of disclosure, not environmental impact. One bond was scored, so 64% has no benchmark.

## 4. Risks and limits (风险提示, fēng xiǎn tí shì)

- H1 2026 figures are unaudited. MTN002 is in no balance sheet used here, and equity treatment is an intention, not a confirmed accounting outcome.
- The composition of investment income, and of the RMB 1.08bn fair-value gain in FY2025, was not checked in the annual report notes.
- GBP scores are the author's judgements with evidence; two (P2, R3) are medium confidence.
- An LLM classifier of use of proceeds matched the author's labels exactly on 4 of 10 bonds and partly on 7 of 10. With one annotator and n = 10 this is descriptive only.

**Sources:** MTN002 prospectus and second-party opinion; Goldwind annual reports FY2022-FY2025; H1 2026 report (cninfo). Code, data and notebook: this repository.