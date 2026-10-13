"""Write outputs/error_view.txt: for every bond whose LLM L2 set is not identical to the hand label,
show the source text, the hand label, the model's answer (project / l2 / alt / evidence) and an
empty verdict line to fill in by hand.

Run src/llm_classifier.py and src/evaluate_classifier.py first.
Verdict codes to use:  MODEL_ERROR | LABEL_TOO_NARROW | AMBIGUOUS | PROTOCOL (one-L2-per-project rule)
Do not edit gold_labels.csv because of what you read here (or flag it: "revised after seeing LLM").
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "outputs" / "eval_per_bond.csv"
PRED = ROOT / "outputs" / "llm_predictions.csv"
GOLD = ROOT / "data" / "labels" / "gold_labels.csv"
CORPUS = ROOT / "data" / "labels" / "corpus_extracted.csv"
OUT = ROOT / "outputs" / "error_view.txt"


def read(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, dtype=str, encoding="utf-8-sig").fillna("")


def main() -> None:
    ev, pred, gold, corpus = read(EVAL), read(PRED), read(GOLD), read(CORPUS)
    pred, gold, corpus = (d.set_index("bond_id") for d in (pred, gold, corpus))
    wrong = ev[ev["error_type"] != "exact"]
    with OUT.open("w", encoding="utf-8") as f:
        f.write(f"{len(wrong)} of {len(ev)} bonds with a non-identical L2 set\n\n")
        for _, r in wrong.iterrows():
            b = r["bond_id"]
            f.write("=" * 78 + f"\n{b}   [{r['error_type']}]\n" + "=" * 78 + "\n")
            f.write(f"HAND LABEL : L1 {gold.loc[b, 'label_l1']}  L2 {gold.loc[b, 'label_l2']}\n")
            f.write(f"HAND NOTE  : {gold.loc[b, 'label_note']}\n")
            if r["declared_l2"]:
                f.write(f"DECLARED   : {r['declared_l2']}  (reference only)\n")
            f.write(f"LLM RESULT : L2 {r['pred_l2'] or '-'}   alt {r['pred_alt_l2'] or '-'}\n")
            try:
                obj = json.loads(pred.loc[b, "raw_json"])
            except Exception:  # noqa: BLE001
                obj = {}
            for i, p in enumerate(obj.get("projects", []), 1):
                f.write(f"  project {i}: {p.get('project', '')}\n"
                        f"     l2={p.get('l2')}  alt_l2={p.get('alt_l2')}  confidence={p.get('confidence')}\n"
                        f"     evidence: {p.get('evidence', '')}\n")
            f.write(f"  non_green_share_pct={obj.get('non_green_share_pct')}   notes: {obj.get('notes', '')}\n\n")
            f.write("SOURCE TEXT:\n" + corpus.loc[b, "input_text"] + "\n\n")
            f.write("VERDICT (MODEL_ERROR | LABEL_TOO_NARROW | AMBIGUOUS | PROTOCOL): ________\n")
            f.write("WHY (one or two sentences, cite the catalogue entry): ________\n\n\n")
    print("written", OUT, "-", len(wrong), "bonds")


if __name__ == "__main__":
    main()
