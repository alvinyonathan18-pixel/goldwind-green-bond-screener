"""Module 3, step 2: classify use-of-proceeds text to the 2025 green catalogue (L1/L2) with an LLM.

Design rules (see README, module 3):
  * The model sees ONLY the extracted use-of-proceeds text (no bond_id, no declared_* columns,
    no gold labels). Catalogue references were already masked by extract_use_of_proceeds.py.
  * temperature=0 and thinking DISABLED. DeepSeek ignores temperature in thinking mode, so
    leaving thinking on would make temperature=0 meaningless.
  * Every response is cached in outputs/llm_cache/ (key = model + prompt version + prompt text),
    together with model, prompt version, parameters, token usage and a UTC timestamp.
  * Only L1/L2 IDs that exist in data/labels/catalogue_categories.csv are accepted.
    Anything else is kept in `invalid_ids` and excluded from the prediction.

Usage (from the repo root, venv active):
  python src/llm_classifier.py --ping        # one tiny call to test key / network / model name
  python src/llm_classifier.py --dry-run     # write the prompts to outputs/llm_prompt_preview.txt, no API call
  python src/llm_classifier.py               # classify all bonds, write outputs/llm_predictions.csv
  python src/llm_classifier.py --only fsh_water_2026
  python src/llm_classifier.py --refresh     # ignore the cache and call the API again
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "data" / "labels" / "corpus_extracted.csv"
CATALOGUE_PATH = ROOT / "data" / "labels" / "catalogue_categories.csv"
CACHE_DIR = ROOT / "outputs" / "llm_cache"
OUT_PATH = ROOT / "outputs" / "llm_predictions.csv"
PREVIEW_PATH = ROOT / "outputs" / "llm_prompt_preview.txt"

PROMPT_VERSION = "v1"
TEMPERATURE = 0
MAX_TOKENS = 2000
MAX_RETRIES = 3

SYSTEM_TEMPLATE = """You classify the use of proceeds of a Chinese bond into the 2025 edition of the \
Green Finance Support Project Catalogue (《绿色金融支持项目目录（2025年版）》).

You are given the 募集资金用途 (use of proceeds) text of one bond prospectus. Follow these rules:

1. Identify each distinct green project or use named in the text and assign ONE level-2 (L2) category ID \
from the list below. Use only IDs from this list. Never output level-3 codes such as 6.4.7.
2. Look-through (穿透, chuantou): if the proceeds repay loans or refinance, classify the project that \
the loan financed, provided the text names it or describes it. If the text only says "repay interest-bearing \
debt" with no project information, return no project for that part and say so in "notes".
3. Working capital (补充营运资金) and other non-project uses get NO category. Report their share of total \
proceeds in "non_green_share_pct" (a number from 0 to 100, from amounts stated in the text; null if the text \
gives no amounts).
4. Classify from the text only. Do not guess catalogue entries that the text does not support. References to \
catalogue entries have been removed from the text on purpose.
5. If two L2 categories both fit one project, give the better one in "l2" and the other in "alt_l2".

Catalogue (2025 edition). Format: ID name

{catalogue}

Reply with a single json object and nothing else, in exactly this shape:
{{"projects": [{{"project": "short description in Chinese taken from the text", "l2": "4.2", \
"confidence": "high", "alt_l2": null, "evidence": "verbatim quote from the text, at most 60 characters"}}], \
"non_green_share_pct": 0, "notes": "short remark or empty string"}}

"confidence" is one of "high", "med", "low". If no green project can be identified, return "projects": []."""

USER_TEMPLATE = "募集资金用途文本如下，请按要求输出json：\n\n{text}"


# ----------------------------------------------------------------------------- catalogue
def load_catalogue() -> pd.DataFrame:
    cat = pd.read_csv(CATALOGUE_PATH, dtype=str, encoding="utf-8-sig").fillna("")
    cat["level"] = cat["level"].astype(int)
    return cat


def build_system_prompt(cat: pd.DataFrame) -> str:
    lines = []
    for _, r in cat.sort_values("category_id", key=lambda s: s.map(_id_key)).iterrows():
        indent = "" if r["level"] == 1 else "  "
        tag = "L1" if r["level"] == 1 else "L2"
        lines.append(f"{indent}{r['category_id']} {r['name_zh']} ({tag})")
    return SYSTEM_TEMPLATE.format(catalogue="\n".join(lines))


def _id_key(cid: str):
    return tuple(int(p) for p in cid.split("."))


# ----------------------------------------------------------------------------- client
def get_client():
    from openai import OpenAI

    load_dotenv(ROOT / ".env")
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip()
    model = os.getenv("DEEPSEEK_MODEL", "").strip()
    missing = [n for n, v in [("DEEPSEEK_API_KEY", key), ("DEEPSEEK_BASE_URL", base_url),
                              ("DEEPSEEK_MODEL", model)] if not v]
    if missing:
        sys.exit("Missing in .env: " + ", ".join(missing))
    return OpenAI(api_key=key, base_url=base_url), model, base_url


def call_model(client, model: str, system: str, user: str, json_mode: bool = True):
    """One chat call. thinking is disabled so that temperature=0 is actually applied."""
    kwargs = dict(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        extra_body={"thinking": {"type": "disabled"}},
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(**kwargs)
            text = (resp.choices[0].message.content or "").strip()
            if not text:  # the API can occasionally return empty content
                raise ValueError("empty content")
            usage = getattr(resp, "usage", None)
            usage_d = {"prompt_tokens": getattr(usage, "prompt_tokens", None),
                       "completion_tokens": getattr(usage, "completion_tokens", None)}
            return text, usage_d
        except Exception as e:  # noqa: BLE001 - retry on any API/network error
            last_err = e
            print(f"  attempt {attempt}/{MAX_RETRIES} failed: {type(e).__name__}")
            time.sleep(2 * attempt)
    raise RuntimeError(f"API call failed after {MAX_RETRIES} attempts: {type(last_err).__name__}")


# ----------------------------------------------------------------------------- cache
def cache_key(model: str, system: str, user: str) -> str:
    payload = json.dumps(
        {"model": model, "prompt_version": PROMPT_VERSION, "system": system, "user": user,
         "temperature": TEMPERATURE, "thinking": "disabled"}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cached_call(client, model, system, user, bond_id, refresh=False):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = cache_key(model, system, user)
    path = CACHE_DIR / f"{key[:16]}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8")), True
    text, usage = call_model(client, model, system, user)
    record = {
        "cache_key": key, "bond_id": bond_id, "model": model, "prompt_version": PROMPT_VERSION,
        "temperature": TEMPERATURE, "thinking": "disabled", "usage": usage,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "response_text": text,
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record, False


# ----------------------------------------------------------------------------- parsing
def parse_response(text: str, cat: pd.DataFrame) -> dict:
    """Validate the model output against the catalogue. Never trust IDs the model made up."""
    l2_ids = set(cat.loc[cat["level"] == 2, "category_id"])
    parent = dict(zip(cat["category_id"], cat["parent_id"]))
    out = {"parse_ok": False, "pred_l1": "", "pred_l2": "", "pred_alt_l2": "", "n_projects": 0,
           "min_confidence": "", "non_green_share_pct": None, "invalid_ids": "", "notes": ""}
    try:
        obj = json.loads(text)
        projects = obj.get("projects", [])
        assert isinstance(projects, list)
    except Exception:  # noqa: BLE001
        return out
    valid, alts, invalid, confs = [], [], [], []
    for p in projects:
        l2 = str(p.get("l2", "")).strip()
        if l2:
            (valid if l2 in l2_ids else invalid).append(l2)
        alt = p.get("alt_l2")
        if alt:
            alt = str(alt).strip()
            (alts if alt in l2_ids else invalid).append(alt)
        if p.get("confidence"):
            confs.append(str(p["confidence"]))
    valid = sorted(set(valid), key=_id_key)
    alts = sorted(set(alts) - set(valid), key=_id_key)
    order = {"low": 0, "med": 1, "high": 2}
    out.update(
        parse_ok=True,
        pred_l2=";".join(valid),
        pred_l1=";".join(sorted({parent[i] for i in valid}, key=int)),
        pred_alt_l2=";".join(alts),
        n_projects=len(projects),
        min_confidence=min(confs, key=lambda c: order.get(c, 1)) if confs else "",
        non_green_share_pct=obj.get("non_green_share_pct"),
        invalid_ids=";".join(sorted(set(invalid))),
        notes=str(obj.get("notes", "")).replace("\n", " "),
    )
    return out


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ping", action="store_true", help="test key, network and model name with one tiny call")
    ap.add_argument("--dry-run", action="store_true", help="write prompts to a file, no API call")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache")
    ap.add_argument("--only", help="classify only this bond_id")
    args = ap.parse_args()

    cat = load_catalogue()
    system = build_system_prompt(cat)

    if args.ping:
        client, model, base_url = get_client()
        t0 = time.time()
        text, usage = call_model(client, model, 'Reply with the json object {"ok": true}.', "ping")
        print(f"OK  base_url={base_url}  model={model}  seconds={time.time() - t0:.1f}  usage={usage}")
        print("reply:", text[:80].encode("ascii", "replace").decode())
        return

    df = pd.read_csv(CORPUS_PATH, dtype=str, encoding="utf-8-sig").fillna("")
    df = df[(df["status"] == "ok") & (df["input_text"].str.strip() != "")]
    if args.only:
        df = df[df["bond_id"] == args.only]
    if df.empty:
        sys.exit("No rows to classify.")

    if args.dry_run:
        PREVIEW_PATH.parent.mkdir(exist_ok=True)
        with PREVIEW_PATH.open("w", encoding="utf-8") as f:
            f.write(f"PROMPT_VERSION={PROMPT_VERSION}\n\n=== SYSTEM ===\n{system}\n\n")
            for _, r in df.iterrows():
                f.write(f"{'=' * 70}\nUSER ({r['bond_id']})\n{'=' * 70}\n")
                f.write(USER_TEMPLATE.format(text=r["input_text"]) + "\n\n")
        print("written", PREVIEW_PATH, "-", len(df), "bonds, no API call made")
        return

    client, model, _ = get_client()
    rows = []
    for _, r in df.iterrows():
        user = USER_TEMPLATE.format(text=r["input_text"])
        record, hit = cached_call(client, model, system, user, r["bond_id"], refresh=args.refresh)
        parsed = parse_response(record["response_text"], cat)
        rows.append({"bond_id": r["bond_id"], **parsed, "model": record["model"],
                     "prompt_version": record["prompt_version"], "from_cache": hit,
                     "raw_json": record["response_text"].replace("\n", " ")})
        print(f"{r['bond_id']:<28} l2={parsed['pred_l2'] or '-':<12} cache={hit}  parse_ok={parsed['parse_ok']}")
    # --only must never overwrite the full 10-bond result file
    out_path = OUT_PATH.with_name("llm_predictions_single.csv") if args.only else OUT_PATH
    out_path.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8-sig")
    print("written", out_path, len(rows), "bonds")


if __name__ == "__main__":
    main()
