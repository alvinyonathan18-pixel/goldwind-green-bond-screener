"""Module 2 - Green Bond Principles (GBP) compliance scorer.

Scores a green bond against the four GBP core components, using a 0-2 checklist rubric:
    UoP  Use of Proceeds                                  募集资金用途
    PES  Process for Project Evaluation and Selection     项目评估与遴选流程
    MoP  Management of Proceeds                           募集资金管理
    REP  Reporting                                        信息披露与报告

How it works
    - The rubric (what earns 0, 1 or 2 on each criterion) lives in this file.
    - The evidence and the score for each criterion live in
      data/prospectus/gbp_evidence.csv, one row per (bond, criterion), with the quoted
      Chinese source text and the page number. The scores are manual judgments.
    - This script does not judge. It checks that the evidence file is complete and
      well-formed, then aggregates scores per pillar. Equal weights, 2 points per criterion.

Outputs (committed): data/processed/gbp_scores_detail.csv, gbp_scores_summary.csv
No network access is needed.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_CSV = ROOT / "data" / "prospectus" / "gbp_evidence.csv"
PROCESSED = ROOT / "data" / "processed"

PILLARS = {
    "UoP": "Use of Proceeds (募集资金用途)",
    "PES": "Project Evaluation & Selection (项目评估与遴选)",
    "MoP": "Management of Proceeds (募集资金管理)",
    "REP": "Reporting (信息披露与报告)",
}

# 0 / 1 / 2 definitions. A score of 1 is the middle case; the wording says exactly what it means.
RUBRIC = [
    # --- Use of Proceeds -------------------------------------------------------------
    ("U1", "UoP", "Taxonomy category",
     "No category from a recognised green taxonomy",
     "Category named, but ambiguous or inconsistent across documents",
     "Category named and consistent across documents"),
    ("U2", "UoP", "Project specificity",
     "General or unspecified use",
     "One defined activity with a quantified scale, but no project list or amounts per project",
     "Project list with amounts per project"),
    ("U3", "UoP", "Environmental benefit quantified",
     "No environmental benefit stated",
     "Qualitative description only",
     "Quantified, with the method and emission factors disclosed"),
    ("U4", "UoP", "Directness of link to green asset",
     "General corporate purposes",
     "Indirect: e.g. equipment or supply-chain purchases for assets owned by third parties",
     "Proceeds finance the green asset itself"),
    ("U5", "UoP", "Refinancing and look-back",
     "Not disclosed, or refinancing allowed without limit",
     "Either the refinancing share or the look-back period is stated",
     "Both are stated"),
    # --- Process for Project Evaluation and Selection --------------------------------
    ("P1", "PES", "Process and responsible body",
     "No process described",
     "Process described at policy level; decision-maker or criteria not disclosed",
     "Process, decision-maker and criteria disclosed"),
    ("P2", "PES", "Environmental and social risk",
     "No risk discussion",
     "Generic risk discussion or issuer-level mitigation",
     "Project-specific risk identification with mitigation"),
    ("P3", "PES", "Screening checked externally",
     "No screening against stated criteria",
     "Screening stated but not externally reviewed",
     "Screening against stated criteria reviewed by an external reviewer"),
    # --- Management of Proceeds ------------------------------------------------------
    ("M1", "MoP", "Segregated account",
     "None",
     "Internal sub-account or ledger only",
     "Dedicated account with a third-party (bank) supervision agreement"),
    ("M2", "MoP", "Tracking and verification",
     "None",
     "Named tracking owner only",
     "Named owner plus a stated verification procedure"),
    ("M3", "MoP", "Unallocated proceeds",
     "Treatment not disclosed",
     "Temporary placement rule stated",
     "Rule stated and limited to cash or eligible instruments"),
    # --- Reporting -------------------------------------------------------------------
    ("R1", "REP", "Allocation reporting",
     "None",
     "Commitment without frequency or content",
     "Commitment with frequency and content (amount used, unused, project progress)"),
    ("R2", "REP", "Impact reporting",
     "None",
     "Qualitative commitment",
     "Quantitative indicators under a reference framework"),
    ("R3", "REP", "External review",
     "None",
     "Pre-issuance review only",
     "Pre-issuance and post-issuance verification"),
]
RUBRIC_DF = pd.DataFrame(RUBRIC, columns=["criterion_id", "pillar", "criterion", "score_0", "score_1", "score_2"])

EVIDENCE_COLS = ["bond", "criterion_id", "score", "confidence", "source_pages", "evidence_zh", "rationale"]


def load_evidence(path: Path | None = None) -> pd.DataFrame:
    """Read the evidence file and fail loudly if it is incomplete or malformed."""
    path = EVIDENCE_CSV if path is None else path
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    ev = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)

    missing_cols = [c for c in EVIDENCE_COLS if c not in ev.columns]
    if missing_cols:
        raise KeyError(f"Missing columns in {path.name}: {missing_cols}")

    ev["score"] = pd.to_numeric(ev["score"], errors="raise")
    bad_score = ev[~ev["score"].isin([0, 1, 2])]
    if not bad_score.empty:
        raise ValueError(f"Scores must be 0, 1 or 2:\n{bad_score[['bond', 'criterion_id', 'score']]}")

    bad_conf = ev[~ev["confidence"].isin(["high", "medium", "low"])]
    if not bad_conf.empty:
        raise ValueError(f"confidence must be high, medium or low:\n{bad_conf[['bond', 'criterion_id']]}")

    # Every row needs a source and a rationale. Quoted Chinese text is required whenever score > 0
    # (a score of 0 can mean "nothing found", so there may be nothing to quote).
    no_source = ev[(ev["source_pages"].str.strip() == "") | (ev["rationale"].str.strip() == "")]
    if not no_source.empty:
        raise ValueError(f"source_pages and rationale are required:\n{no_source[['bond', 'criterion_id']]}")
    no_quote = ev[(ev["score"] > 0) & (ev["evidence_zh"].str.strip() == "")]
    if not no_quote.empty:
        raise ValueError(f"evidence_zh is required when score > 0:\n{no_quote[['bond', 'criterion_id']]}")

    expected = set(RUBRIC_DF["criterion_id"])
    for bond, g in ev.groupby("bond"):
        ids = g["criterion_id"]
        dup = sorted(ids[ids.duplicated()])
        missing = sorted(expected - set(ids))
        extra = sorted(set(ids) - expected)
        if dup or missing or extra:
            raise ValueError(f"{bond}: duplicate={dup} missing={missing} unknown={extra}")
    return ev


def score_detail(ev: pd.DataFrame) -> pd.DataFrame:
    """One row per (bond, criterion), with pillar and criterion name attached."""
    d = ev.merge(RUBRIC_DF[["criterion_id", "pillar", "criterion"]], on="criterion_id", how="left")
    d["pillar"] = pd.Categorical(d["pillar"], categories=list(PILLARS), ordered=True)
    d = d.sort_values(["bond", "pillar", "criterion_id"]).reset_index(drop=True)
    return d[["bond", "pillar", "criterion_id", "criterion", "score", "confidence",
              "source_pages", "evidence_zh", "rationale"]]


def pillar_summary(detail: pd.DataFrame) -> pd.DataFrame:
    """Score, maximum and percentage per bond and pillar, plus a TOTAL row per bond."""
    s = (detail.groupby(["bond", "pillar"], observed=True)["score"]
         .agg(score="sum", n="count").reset_index())
    s["max"] = s["n"] * 2
    s["pillar"] = s["pillar"].astype(str)
    total = s.groupby("bond", as_index=False)[["score", "n", "max"]].sum()
    total["pillar"] = "TOTAL"
    s = pd.concat([s, total], ignore_index=True)
    s["pct"] = s["score"] / s["max"] * 100
    order = {p: i for i, p in enumerate([*PILLARS, "TOTAL"])}
    s = s.sort_values(["bond", "pillar"], key=lambda col: col.map(order) if col.name == "pillar" else col)
    return s[["bond", "pillar", "score", "max", "pct"]].reset_index(drop=True)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    detail = score_detail(load_evidence())
    summary = pillar_summary(detail)
    detail.to_csv(PROCESSED / "gbp_scores_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(PROCESSED / "gbp_scores_summary.csv", index=False, encoding="utf-8-sig")

    print("Score per criterion (0-2)")
    print(detail[["bond", "criterion_id", "criterion", "score", "confidence"]].to_string(index=False))
    print("\nScore per pillar")
    print(summary.to_string(index=False, float_format="{:,.0f}".format))
    low = detail[detail["confidence"] != "high"]
    if not low.empty:
        print("\nNot high-confidence (re-check against the source documents):",
              ", ".join(f"{b}/{c}" for b, c in zip(low["bond"], low["criterion_id"])))


if __name__ == "__main__":
    main()
