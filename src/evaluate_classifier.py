"""Module 3, step 3: evaluate the LLM classifier against the hand labels (n=10 case study).

Inputs
  data/labels/gold_labels.csv        hand labels (label_l1, label_l2, label_note)
  outputs/llm_predictions.csv        output of src/llm_classifier.py
  data/labels/corpus_extracted.csv   declared_l1 / declared_l2 / declared_valid (only 4 of 10 bonds)

Outputs
  outputs/eval_per_bond.csv          one row per bond, with an automatic error type
  outputs/eval_summary.txt           the metric table (also printed, ASCII only)

Read the numbers as a description of this sample, not as an accuracy claim: n=10, one labeler,
labels were discussed with a second person, and multi-label gold sets penalise recall.
Do not edit gold_labels.csv after reading these results unless the note says
"revised after seeing LLM".
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data" / "labels" / "gold_labels.csv"
PRED_PATH = ROOT / "outputs" / "llm_predictions.csv"
CORPUS_PATH = ROOT / "data" / "labels" / "corpus_extracted.csv"
OUT_BOND = ROOT / "outputs" / "eval_per_bond.csv"
OUT_SUMMARY = ROOT / "outputs" / "eval_summary.txt"


# ----------------------------------------------------------------------------- helpers
def id_key(cid: str):
    return tuple(int(p) for p in cid.split("."))


def to_set(s) -> set[str]:
    s = str(s or "").strip()
    if not s or s.upper() == "NONE":
        return set()
    return {x.strip() for x in s.split(";") if x.strip()}


def fmt(ids: set[str]) -> str:
    return ";".join(sorted(ids, key=id_key))


def parse_note(note: str) -> dict:
    """Read 'high/med/low / alt <ids|none> / non-green <x>% / assisted' from label_note."""
    note = str(note or "")
    m_alt = re.search(r"alt\s+([0-9][0-9.;]*|none)", note, re.I)
    m_ng = re.search(r"non-green\s+(\d+(?:\.\d+)?)\s*%", note, re.I)
    m_conf = re.match(r"\s*(high|med|low)\b", note, re.I)
    return {
        "gold_alt": to_set(m_alt.group(1)) if m_alt and m_alt.group(1).lower() != "none" else set(),
        "gold_nongreen": float(m_ng.group(1)) if m_ng else None,
        "gold_conf": m_conf.group(1).lower() if m_conf else "",
        "assisted": bool(re.search(r"\bassisted\b", note, re.I)),
        "revised": bool(re.search(r"revised after seeing", note, re.I)),
    }


def error_type(g: set, p: set, g_alt: set) -> str:
    if not p:
        return "no_prediction"
    if g == p:
        return "exact"
    if p < g:
        return "subset_missing_gold"
    if p > g:
        return "superset_extra"
    if p & g:
        return "overlap_mixed"
    return "disjoint_hits_gold_alt" if p & g_alt else "disjoint"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    d = 1 + z * z / n
    c = ph + z * z / (2 * n)
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def micro_prf(rows: list[tuple[set, set]]) -> tuple[float, float, float, int, int, int]:
    tp = sum(len(g & p) for g, p in rows)
    n_p = sum(len(p) for _, p in rows)
    n_g = sum(len(g) for g, _ in rows)
    prec = tp / n_p if n_p else float("nan")
    rec = tp / n_g if n_g else float("nan")
    f1 = 2 * tp / (n_p + n_g) if (n_p + n_g) else float("nan")
    return prec, rec, f1, tp, n_p, n_g


def truthy(x) -> bool:
    return str(x).strip().lower() in {"1", "true", "yes", "y"}


# ----------------------------------------------------------------------------- core
def evaluate(gold: pd.DataFrame, pred: pd.DataFrame, corpus: pd.DataFrame):
    pred = pred.set_index("bond_id")
    decl = {}
    for _, r in corpus.iterrows():
        if truthy(r.get("declared_valid", "")) and str(r.get("declared_l2", "")).strip():
            decl[r["bond_id"]] = (to_set(r.get("declared_l1", "")), to_set(r["declared_l2"]))

    rows = []
    for _, g in gold.iterrows():
        bid = g["bond_id"]
        note = parse_note(g["label_note"])
        g1, g2 = to_set(g["label_l1"]), to_set(g["label_l2"])
        if bid in pred.index:
            pr = pred.loc[bid]
            p1, p2 = to_set(pr["pred_l1"]), to_set(pr["pred_l2"])
            p_alt = to_set(pr.get("pred_alt_l2", ""))
            conf = str(pr.get("min_confidence", ""))
            ng_pred = pd.to_numeric(pr.get("non_green_share_pct", ""), errors="coerce")
            invalid = str(pr.get("invalid_ids", ""))
        else:
            p1 = p2 = p_alt = set()
            conf, ng_pred, invalid = "", float("nan"), ""
        d1, d2 = decl.get(bid, (set(), set()))
        has_decl = bool(d2)
        rows.append({
            "bond_id": bid,
            "gold_l1": fmt(g1), "pred_l1": fmt(p1),
            "gold_l2": fmt(g2), "pred_l2": fmt(p2),
            "gold_alt": fmt(note["gold_alt"]), "pred_alt_l2": fmt(p_alt),
            "l1_exact": g1 == p1, "l2_exact": g2 == p2, "l2_overlap": bool(g2 & p2),
            "l2_overlap_lenient": bool(p2 & (g2 | note["gold_alt"])),
            "gold_in_pred_alt": fmt((g2 - p2) & p_alt),
            "pred_in_gold_alt": fmt((p2 - g2) & note["gold_alt"]),
            "error_type": error_type(g2, p2, note["gold_alt"]),
            "declared_l2": fmt(d2),
            "llm_vs_declared": ("agree" if p2 == d2 else "differ") if has_decl else "n/a",
            "gold_vs_declared": ("agree" if g2 == d2 else "differ") if has_decl else "n/a",
            "gold_nongreen_pct": note["gold_nongreen"], "pred_nongreen_pct": ng_pred,
            "gold_conf": note["gold_conf"], "llm_min_conf": conf,
            "assisted": note["assisted"], "revised": note["revised"], "invalid_ids": invalid,
        })
    per = pd.DataFrame(rows)
    return per


def summarise(per: pd.DataFrame) -> str:
    n = len(per)
    g1 = [(to_set(r.gold_l1), to_set(r.pred_l1)) for r in per.itertuples()]
    g2 = [(to_set(r.gold_l2), to_set(r.pred_l2)) for r in per.itertuples()]
    lines = [f"EVALUATION  n={n} bonds  (descriptive only; see caveats in the script header)", ""]

    def prop(label: str, k: int):
        lo, hi = wilson(k, n)
        lines.append(f"  {label:<44}{k}/{n} = {k / n:5.0%}   95% Wilson CI [{lo:.0%}, {hi:.0%}]")

    lines.append("Exact / overlap match (per bond)")
    prop("L1 set exactly equal", int(per["l1_exact"].sum()))
    prop("L2 set exactly equal", int(per["l2_exact"].sum()))
    prop("L2 at least one ID in common", int(per["l2_overlap"].sum()))
    prop("L2 overlap, gold alt counted as acceptable", int(per["l2_overlap_lenient"].sum()))
    lines.append("")
    lines.append("Micro precision / recall / F1 over IDs")
    for name, rows in [("L1", g1), ("L2", g2)]:
        p, r, f, tp, n_p, n_g = micro_prf(rows)
        lines.append(f"  {name}: precision {p:.0%} ({tp}/{n_p})   recall {r:.0%} ({tp}/{n_g})   F1 {f:.2f}")
    lines.append("")
    d = per[per["llm_vs_declared"] != "n/a"]
    lines.append(f"Agreement with declared_* (only {len(d)} bonds have a valid declared category, L2 level)")
    lines.append(f"  LLM vs declared : {(d['llm_vs_declared'] == 'agree').sum()}/{len(d)}")
    lines.append(f"  Gold vs declared: {(d['gold_vs_declared'] == 'agree').sum()}/{len(d)}"
                 f"   (gold rows tagged assisted: {int(per['assisted'].sum())})")
    lines.append("")
    lines.append("Error types (L2)")
    for k, v in per["error_type"].value_counts().items():
        lines.append(f"  {k:<26}{v}")
    lines.append("")
    lines.append("Per bond")
    lines.append(f"  {'bond_id':<28}{'gold L2':<14}{'LLM L2':<12}{'type':<24}notes")
    for r in per.itertuples():
        extra = []
        if r.pred_in_gold_alt:
            extra.append(f"LLM chose your alt {r.pred_in_gold_alt}")
        if r.gold_in_pred_alt:
            extra.append(f"LLM listed gold {r.gold_in_pred_alt} only as alt")
        if r.llm_vs_declared == "differ":
            extra.append(f"differs from declared {r.declared_l2}")
        if r.invalid_ids:
            extra.append(f"invalid ids {r.invalid_ids}")
        lines.append(f"  {r.bond_id:<28}{(r.gold_l2 or '-'):<14}{(r.pred_l2 or '-'):<12}"
                     f"{r.error_type:<24}{'; '.join(extra)}")
    return "\n".join(lines)


def main() -> None:
    gold = pd.read_csv(GOLD_PATH, dtype=str, encoding="utf-8-sig").fillna("")
    pred = pd.read_csv(PRED_PATH, dtype=str, encoding="utf-8-sig").fillna("")
    corpus = pd.read_csv(CORPUS_PATH, dtype=str, encoding="utf-8-sig").fillna("")
    empty = gold[(gold["label_l2"].str.strip() == "")]["bond_id"].tolist()
    if empty:
        raise SystemExit("gold_labels.csv has empty label_l2 for: " + ", ".join(empty)
                         + "  (use NONE if no project can be identified)")
    per = evaluate(gold, pred, corpus)
    OUT_BOND.parent.mkdir(exist_ok=True)
    per.to_csv(OUT_BOND, index=False, encoding="utf-8-sig")
    text = summarise(per)
    OUT_SUMMARY.write_text(text + "\n", encoding="utf-8")
    print(text)
    print("\nwritten", OUT_BOND)
    print("written", OUT_SUMMARY)


if __name__ == "__main__":
    main()
