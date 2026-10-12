"""Module 3, step 1 - extract the use-of-proceeds text from prospectus PDFs (募集说明书).

For every PDF in data/prospectus/ this script produces one row with
    input_text    what the LLM will see: the opening statement of 募集资金用途 plus the project overview
    declared_*    the catalogue category that the prospectus itself states (issuer or reviewer wording).
                  This is a second, independent label. It is compared with your hand label and is NOT
                  shown to the LLM.

Outputs
    data/labels/corpus_extracted.csv   regenerated on every run (machine-made, do not edit)
    data/labels/gold_labels.csv        YOUR labels, key = bond_id. The script only appends rows for
                                       new bond_id values and never touches labels already entered.

Leakage control: prospectuses often print the catalogue category right next to the project
description. Every sentence containing 目录 is removed from input_text and the count is logged.

Needs: pip install pymupdf pandas. No network access.
File naming: use a short unique stem per bond, e.g. data/prospectus/102683199_goldwind.pdf
"""
import re
from pathlib import Path

import pandas as pd
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "prospectus"
LABELS = ROOT / "data" / "labels"
CATALOGUE_CSV = LABELS / "catalogue_categories.csv"
EXTRACTED_CSV = LABELS / "corpus_extracted.csv"
GOLD_CSV = LABELS / "gold_labels.csv"

MAX_PROJECT_CHARS = 800      # project overview is cut here (at a sentence end if possible)
MAX_LEAD_CHARS = 1500
MAX_TABLE_CHARS = 1200       # text of the first table (project names are often only there)

CHAPTER = re.compile(r"^第[一二三四五六七八九十]+[章节条]\s*募集资金(用途|运用)\s*$")
SECTION_ONE = re.compile(r"^一、\s*[^。]{0,12}募集资金(用途|运用)[^。]{0,12}$")
SECTION_ONE_TEXT = re.compile(r"^[^。]{0,12}募集资金(用途|运用)[^。]{0,12}$")   # when "一、" sits alone on the previous line
SUBHEADING = re.compile(r"^（[一二三四五六七八九十]+）")
TOP_HEADING = re.compile(r"^[二三四五六七八九十]、")
PROJECT_HEADING = re.compile(r"^((（[一二三四五六七八九十]+）\s*募投项目(的)?(基本情况|概况))|([二三]、\s*募集资金投资项目概况))\s*$")
TABLE_MARKER = re.compile(r"^(图表|表)\s*\d+\s*[-－–]\s*\d+")
PAGE_NOISE = re.compile(r"^(\d{1,3}|.{0,60}募集说明书)$")      # page numbers and running headers
REFINANCING = re.compile(r"偿还|归还|置换|借款|有息债务|有息负债")
EDITION_2025 = "绿色金融支持项目目录（2025年版）"
EDITIONS = {                 # catalogue names that a prospectus may cite
    "2025": EDITION_2025,
    "2021": "绿色债券支持项目目录（2021年版）",
    "2019": "绿色产业指导目录（2019年版）",
    "2015": "绿色债券支持项目目录（2015年版）",
}


def read_lines(pdf: Path) -> tuple[list[str], str]:
    """(body lines without page numbers and running headers, raw text of the cover page)."""
    lines = []
    with pymupdf.open(pdf) as doc:
        cover = re.sub(r"\s+", "", doc[0].get_text("text"))
        for page in doc:
            for ln in page.get_text("text").splitlines():
                ln = ln.strip()
                if ln and not PAGE_NOISE.match(ln):
                    lines.append(ln)
    return lines, cover


def flatten(lines: list[str]) -> str:
    """One string without any whitespace and with full-width brackets (for pattern search)."""
    flat = re.sub(r"\s+", "", "".join(lines))
    return flat.replace("(", "（").replace(")", "）")


def collect(lines: list[str], start: int, stop_patterns: list, cap: int) -> str:
    """Join lines from `start` until a stop pattern or `cap` characters. Sub-headings are skipped."""
    out = []
    for ln in lines[start:]:
        if any(p.match(ln) for p in stop_patterns):
            break
        if SUBHEADING.match(ln) and not PROJECT_HEADING.match(ln):
            continue
        out.append(ln)
        if sum(map(len, out)) >= cap:
            break
    text = "".join(out)
    if len(text) > cap:
        cut = text.rfind("。", 0, cap)
        text = text[: cut + 1] if cut > cap // 2 else text[:cap]
    return text


TABLE_STUB = re.compile(r"[，、]?[^，。：“”]{0,12}?(?:如下表所示|详见下表|见下表|如下)：")


def is_section_one(lines: list[str], i: int) -> bool:
    """Heading '一、...募集资金用途...', also when the numbering '一、' is its own line in the PDF."""
    if SECTION_ONE.match(lines[i]):
        return True
    return i > 0 and lines[i - 1] == "一、" and bool(SECTION_ONE_TEXT.match(lines[i]))


def table_text(lines: list[str], start: int) -> str:
    """Text of the first table after `start`: from its caption line to the next heading or note."""
    first = next((i for i in range(start, min(start + 60, len(lines))) if TABLE_MARKER.match(lines[i])), None)
    if first is None:
        return ""
    out = []
    for ln in lines[first + 1:]:
        if TOP_HEADING.match(ln) or SUBHEADING.match(ln) or ln.startswith(("注：", "注:")):
            break
        out.append(ln)
        if sum(map(len, out)) >= MAX_TABLE_CHARS:
            break
    return " ".join(out)[:MAX_TABLE_CHARS]


def mask_catalogue_sentences(text: str) -> tuple[str, int]:
    """Drop every sentence that mentions 目录 so that the answer is not in the input."""
    sentences = re.split(r"(?<=。)", text)
    kept = [s for s in sentences if "目录" not in s]
    return "".join(kept), len(sentences) - len(kept)


def declared_paths(flat: str) -> list[str]:
    """Catalogue numbers (e.g. 6.2.6) quoted in 'the project belongs to “...”' sentences."""
    for m in re.finditer(re.escape(EDITION_2025) + "》", flat):
        segment = flat[m.end(): m.end() + 400].split("。")[0]
        quotes = re.findall(r"“([^”]{3,200})”", segment)
        paths = [p for q in quotes for p in re.findall(r"(?<![\d.])(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)(?=[^\d.])", q)]
        if paths:
            deepest = [p for p in paths if p.count(".") == 2] or paths
            return list(dict.fromkeys(deepest))
    return []


def extract_one(pdf: Path, valid_l2: set[str]) -> dict:
    lines, cover = read_lines(pdf)
    flat = flatten(lines)
    row = {"bond_id": pdf.stem, "source_file": pdf.name, "status": "ok"}

    cover = cover.replace("(", "（").replace(")", "）")
    title = (re.search(r".*(20\d\d年度第.{1,3}期[^募]{2,40}?募集说明书)", cover)       # greedy prefix: last occurrence
             or re.search(r"(20\d\d年.{4,60}?募集说明书)", cover))
    if not title:                                   # some covers are images: look in the first body text
        title = re.search(r"(20\d\d年.{4,60}?募集说明书)", flat[:4000])
    row["title"] = title.group(1) if title else ""
    issuer = (re.search(r"发行人[：:]?([^\s：:]{4,40}?(?:股份有限公司|有限责任公司|有限公司))", cover)
              or re.search(r"20\d\d年(?:度第.{1,3}期)?(.{4,30}?(?:有限公司|集团))", row["title"]))
    row["issuer"] = issuer.group(1) if issuer else ""
    found = [year for year, name in EDITIONS.items() if name in flat]
    row["edition_cited"] = "+".join(sorted(found)) if found else "none"

    chapters = [i for i, ln in enumerate(lines) if CHAPTER.match(ln)]
    ch = chapters[-1] if chapters else 0        # the last match is the body; earlier ones are the contents page
    lead = tbl = project = ""
    sections = [i for i in range(ch, len(lines)) if is_section_one(lines, i)]
    sec = None if not sections else (sections[0] if chapters else sections[-1])
    if sec is None:
        row["status"] = "no_section_one"
    else:
        lead = collect(lines, sec + 1, [TABLE_MARKER, TOP_HEADING], MAX_LEAD_CHARS)
        tbl = table_text(lines, sec + 1)
        prj = next((i for i in range(sec + 1, len(lines)) if PROJECT_HEADING.match(lines[i])), None)
        if prj is not None and prj - sec < 400:
            project = collect(lines, prj + 1, [TABLE_MARKER, TOP_HEADING, PROJECT_HEADING], MAX_PROJECT_CHARS)

    stubbed = TABLE_STUB.sub("。", lead).replace("。。", "。")
    input_text, n_masked = mask_catalogue_sentences("".join([stubbed, ("【表】" + tbl + "。") if tbl else "", project]))
    paths = declared_paths(flat)
    l2 = sorted({".".join(p.split(".")[:2]) for p in paths})
    row.update({
        "refinancing": int(bool(REFINANCING.search(lead))),
        "lead_chars": len(lead),
        "table_chars": len(tbl),
        "project_chars": len(project),
        "input_chars": len(input_text),
        "sentences_masked": n_masked,
        "input_text": input_text,
        "declared_paths": ";".join(paths),
        "declared_l1": ";".join(sorted({p.split(".")[0] for p in paths})),
        "declared_l2": ";".join(l2),
        "declared_valid": int(bool(l2) and all(c in valid_l2 for c in l2)),
    })
    if row["status"] == "ok" and not input_text:
        row["status"] = "empty_text"
    return row


def update_gold_template(bond_ids: list[str]) -> int:
    """Append an empty label row for each new bond_id. Existing rows are never modified."""
    cols = ["bond_id", "label_l1", "label_l2", "label_note"]
    gold = (pd.read_csv(GOLD_CSV, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            if GOLD_CSV.exists() else pd.DataFrame(columns=cols))
    new = [b for b in bond_ids if b not in set(gold["bond_id"])]
    if new or not GOLD_CSV.exists():
        add = pd.DataFrame({"bond_id": new, "label_l1": "", "label_l2": "", "label_note": ""})
        pd.concat([gold, add], ignore_index=True).to_csv(GOLD_CSV, index=False, encoding="utf-8-sig")
    return len(new)


def main() -> None:
    LABELS.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF found in {PDF_DIR}")
    valid_l2 = set()
    if CATALOGUE_CSV.exists():
        cat = pd.read_csv(CATALOGUE_CSV, dtype=str, encoding="utf-8-sig")
        valid_l2 = set(cat.loc[cat["level"] == "2", "category_id"])
    rows = [extract_one(p, valid_l2) for p in pdfs]
    df = pd.DataFrame(rows)
    df.to_csv(EXTRACTED_CSV, index=False, encoding="utf-8-sig")
    added = update_gold_template(list(df["bond_id"]))

    show = ["bond_id", "edition_cited", "refinancing", "input_chars", "table_chars", "sentences_masked", "declared_paths", "status"]
    print(df[show].to_string(index=False))
    print(f"\n{len(df)} bonds written to {EXTRACTED_CSV.name}; {added} new rows added to {GOLD_CSV.name}")
    no_declared = df["edition_cited"].str.contains("2025") & (df["declared_paths"] == "")
    bad = df[(df["status"] != "ok") | (df["input_chars"] < 150) | no_declared]
    if not bad.empty:
        print("Check by hand:", ", ".join(bad["bond_id"]))


if __name__ == "__main__":
    main()
