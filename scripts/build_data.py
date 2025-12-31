#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gera datasets JSON em /data/json a partir dos arquivos .xlsx em /data/raw.

Objetivo: rodar no GitHub Actions (sem depender do seu notebook).
Observação: isso é para estudo/auditoria estatística; não “prevê” resultados de loteria.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple


RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/json")


# -----------------------------
# Utils
# -----------------------------
def utc_now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "dataset"


def to_int(v) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if re.fullmatch(r"\d+", s):
            return int(s)
    return None


def clean_headers(headers: List[Optional[str]]) -> List[Optional[str]]:
    seen: Dict[str, int] = {}
    out: List[Optional[str]] = []
    for h in headers:
        if h is None:
            out.append(None)
            continue
        s = str(h).strip()
        if not s:
            out.append(None)
            continue
        if s in seen:
            seen[s] += 1
            out.append(f"{s}_{seen[s]}")
        else:
            seen[s] = 1
            out.append(s)
    return out


def extract_number_columns(headers: List[Optional[str]]) -> List[str]:
    patterns = [
        re.compile(r"^Bola\s*\d+$", re.I),
        re.compile(r"^Bola\d+$", re.I),
        re.compile(r"^Trevo\s*\d+$", re.I),
        re.compile(r"^Trevo\d+$", re.I),
        re.compile(r"^Coluna\s*\d+$", re.I),
        re.compile(r"^Coluna\d+$", re.I),
    ]
    cols: List[str] = []
    for h in headers:
        if not h:
            continue
        hs = str(h).strip()
        if any(p.match(hs) for p in patterns):
            cols.append(hs)
    return cols


# -----------------------------
# XLSX (parser tolerante via XML)
# -----------------------------
def _col_to_index(col_letters: str) -> int:
    col_letters = col_letters.upper()
    idx = 0
    for ch in col_letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1  # zero-based


def _parse_shared_strings(zf: zipfile.ZipFile) -> List[str]:
    try:
        xml_data = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml_data)
    strings: List[str] = []
    for si in root.findall(".//{*}si"):
        parts: List[str] = []
        for tnode in si.findall(".//{*}t"):
            if tnode.text:
                parts.append(tnode.text)
        strings.append("".join(parts))
    return strings


def _first_sheet_path(zf: zipfile.ZipFile) -> str:
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

    rid_to_target: Dict[str, str] = {}
    for rel in rels.findall(".//{*}Relationship"):
        rid_to_target[rel.attrib.get("Id")] = rel.attrib.get("Target", "")

    sheet = wb.find(".//{*}sheets/{*}sheet")
    if sheet is None:
        raise RuntimeError("Não achei nenhuma sheet no workbook.xml")

    rid = (
        sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        or sheet.attrib.get("r:id")
    )
    target = rid_to_target.get(rid, "")
    if not target:
        raise RuntimeError("Não consegui resolver o caminho da primeira sheet (rels).")

    if not target.startswith("xl/"):
        target = "xl/" + target.lstrip("/")
    return target


def read_first_sheet_rows(xlsx_path: Path) -> List[List[Optional[str]]]:
    """
    Lê a primeira aba do XLSX como matriz de strings (tolerante a arquivos “estranhos”).
    """
    with zipfile.ZipFile(xlsx_path) as zf:
        shared = _parse_shared_strings(zf)
        sheet_path = _first_sheet_path(zf)
        root = ET.fromstring(zf.read(sheet_path))

        rows: List[List[Optional[str]]] = []
        global_max_col = 0

        for row_el in root.findall(".//{*}sheetData/{*}row"):
            cells: Dict[int, Optional[str]] = {}
            cur_col = 0

            for c in row_el.findall("{*}c"):
                ref = c.attrib.get("r")
                if ref:
                    m = re.match(r"([A-Z]+)(\d+)", ref)
                    if m:
                        cur_col = _col_to_index(m.group(1))

                col_idx = cur_col
                cur_col += 1

                t = c.attrib.get("t")
                v_el = c.find("{*}v")
                value: Optional[str] = None

                if t == "s":
                    if v_el is not None and v_el.text is not None:
                        si = int(v_el.text)
                        value = shared[si] if 0 <= si < len(shared) else v_el.text
                elif t == "inlineStr":
                    t_el = c.find(".//{*}t")
                    value = t_el.text if t_el is not None else None
                else:
                    value = v_el.text if v_el is not None else None

                cells[col_idx] = value
                global_max_col = max(global_max_col, col_idx)

            if not cells and not rows:
                # ignora “linhas” vazias antes do header
                continue

            row = [None] * (global_max_col + 1)
            for idx, val in cells.items():
                row[idx] = val
            rows.append(row)

        return rows


# -----------------------------
# Build JSON
# -----------------------------
def parse_xlsx_dataset(xlsx_path: Path) -> Dict:
    matrix = read_first_sheet_rows(xlsx_path)
    if not matrix:
        raise RuntimeError(f"Sem dados em {xlsx_path.name}")

    header_raw = matrix[0]
    # corta colunas finais vazias
    last = 0
    for i, v in enumerate(header_raw):
        if v is not None and str(v).strip() != "":
            last = i
    header_raw = header_raw[: last + 1]

    headers = clean_headers([v if v is None else str(v) for v in header_raw])
    num_cols = extract_number_columns(headers)

    draws: List[Dict] = []

    for row in matrix[1:]:
        row = row[: len(headers)]
        if not row or all(v is None or str(v).strip() == "" for v in row):
            continue

        # se a primeira coluna (geralmente "Concurso") estiver vazia, ignora
        if row[0] is None or str(row[0]).strip() == "":
            continue

        rec: Dict[str, object] = {}

        for h, v in zip(headers, row):
            if not h:
                continue
            if v is None:
                continue
            s = str(v).strip()
            if s == "":
                continue
            rec[h] = s

        # derived numbers
        nums: List[int] = []
        for col in num_cols:
            n = to_int(rec.get(col))
            if n is not None:
                nums.append(n)
        if nums:
            rec["__numbers"] = nums

        draws.append(rec)

    counts: Dict[str, int] = {}
    total_nums = 0
    for d in draws:
        for n in d.get("__numbers", []):
            counts[str(n)] = counts.get(str(n), 0) + 1
            total_nums += 1

    last_draw = draws[-1] if draws else {}

    dataset = {
        "meta": {
            "game_name": xlsx_path.stem,
            "source_file": xlsx_path.name,
            "generated_at_utc": utc_now_iso(),
            "rows": len(draws),
            "number_columns": num_cols,
        },
        "stats": {
            "total_numbers": total_nums,
            "number_counts": counts,
        },
        "last": {
            "Concurso": last_draw.get("Concurso"),
            "Data do Sorteio": last_draw.get("Data do Sorteio")
            or last_draw.get("Data de Sorteio")
            or last_draw.get("Data de apuração"),
        },
        "draws": draws,
    }
    return dataset


def build_all(raw_dir: Path = RAW_DIR, out_dir: Path = OUT_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    datasets_manifest: List[Dict] = []
    xlsx_files = sorted(p for p in raw_dir.glob("*.xlsx") if p.is_file())

    if not xlsx_files:
        raise RuntimeError("Nenhum .xlsx encontrado em data/raw")

    for xlsx in xlsx_files:
        ds = parse_xlsx_dataset(xlsx)
        ds_id = slugify(xlsx.stem)
        out_path = out_dir / f"{ds_id}.json"
        out_path.write_text(json.dumps(ds, ensure_ascii=False, indent=2), encoding="utf-8")

        datasets_manifest.append(
            {
                "id": ds_id,
                "name": xlsx.stem,
                "path": f"data/json/{ds_id}.json",
                "rows": ds["meta"]["rows"],
                "number_columns": ds["meta"]["number_columns"],
                "generated_at_utc": ds["meta"]["generated_at_utc"],
            }
        )

        print(f"[OK] {xlsx.name} -> {out_path.as_posix()} ({ds['meta']['rows']} linhas)")

    manifest = {
        "generated_at_utc": utc_now_iso(),
        "datasets": datasets_manifest,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] manifest.json gerado com {len(datasets_manifest)} datasets.")


if __name__ == "__main__":
    build_all()
