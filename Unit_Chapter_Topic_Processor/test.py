# gradio_app.py
# Run: python gradio_app.py
#
# What it does (per your instructions):
# 1) Reads your CSV (expects columns: Unit, chapter, topic)
# 2) Creates a "Unit -> Chapters" CSV where each Unit appears once and all its unique Chapters
#    are appended into ONE column separated by commas.
# 3) Creates a ZIP containing chapter-wise CSVs (one CSV per Chapter) listing Topics under that chapter.

import os
import re
import csv
import tempfile
import zipfile
from collections import OrderedDict

import pandas as pd
import gradio as gr


def _normalize_colname(c: str) -> str:
    return re.sub(r"\s+", " ", str(c).strip().lower())


def _ordered_unique(items):
    seen = OrderedDict()
    for x in items:
        if pd.isna(x):
            continue
        s = str(x).strip()
        if s and s not in seen:
            seen[s] = True
    return list(seen.keys())


def process_csv(file_obj):
    # file_obj is a temp file path from Gradio
    in_path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
    df = pd.read_csv(in_path)

    # Handle column name variations (case/space)
    col_map = {_normalize_colname(c): c for c in df.columns}
    required = ["unit", "chapter", "topic"]

    missing = [c for c in required if c not in col_map]
    if missing:
        raise gr.Error(
            f"Missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}. "
            f"Your CSV must include Unit, chapter, topic."
        )

    unit_col = col_map["unit"]
    chapter_col = col_map["chapter"]
    topic_col = col_map["topic"]

    # Clean basic whitespace
    df[unit_col] = df[unit_col].astype(str).str.strip()
    df[chapter_col] = df[chapter_col].astype(str).str.strip()
    df[topic_col] = df[topic_col].astype(str).str.strip()

    # Drop empty rows
    df = df[(df[unit_col] != "") & (df[chapter_col] != "") & (df[topic_col] != "")]

    with tempfile.TemporaryDirectory() as tmpdir:
        # =========================
        # (1) Unit -> Chapters CSV
        # =========================
        unit_rows = []
        # preserve unit order as it appears
        unit_order = _ordered_unique(df[unit_col].tolist())

        for unit in unit_order:
            sub = df[df[unit_col] == unit]
            chapters = _ordered_unique(sub[chapter_col].tolist())
            unit_rows.append(
                {
                    "Unit": unit,
                    "Chapters (comma separated)": ", ".join(chapters),
                }
            )

        summary_df = pd.DataFrame(unit_rows)
        summary_path = os.path.join(tmpdir, "unit_chapters_summary.csv")
        summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

        # =====================================
        # (2) Chapter-wise Topic CSVs -> ZIP
        # =====================================
        zip_path = os.path.join(tmpdir, "chapter_wise_topics.zip")

        # preserve chapter order as it appears
        chapter_order = _ordered_unique(df[chapter_col].tolist())

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for chapter in chapter_order:
                sub = df[df[chapter_col] == chapter]

                # keep Unit info too (helps if a chapter name repeats across units)
                # If a chapter appears under multiple units, we keep all pairs.
                # Output columns: Unit, Chapter, Topic
                rows = []
                # preserve topic order as it appears for that chapter
                for unit in _ordered_unique(sub[unit_col].tolist()):
                    sub2 = sub[sub[unit_col] == unit]
                    topics = _ordered_unique(sub2[topic_col].tolist())
                    for t in topics:
                        rows.append({"Unit": unit, "Chapter": chapter, "Topic": t})

                chapter_df = pd.DataFrame(rows)

                # Safe filename for chapter
                safe_name = re.sub(r"[^\w\-\.\(\) ]+", "", chapter).strip()
                safe_name = re.sub(r"\s+", "_", safe_name)[:120] or "chapter"
                chapter_csv_name = f"{safe_name}.csv"

                chapter_csv_path = os.path.join(tmpdir, chapter_csv_name)
                chapter_df.to_csv(chapter_csv_path, index=False, encoding="utf-8-sig")

                zf.write(chapter_csv_path, arcname=chapter_csv_name)

        # Gradio needs paths that persist after function returns,
        # so copy them to a new temp dir that won't be deleted immediately.
        outdir = tempfile.mkdtemp(prefix="gradio_outputs_")
        final_summary = os.path.join(outdir, "unit_chapters_summary.csv")
        final_zip = os.path.join(outdir, "chapter_wise_topics.zip")
        pd.read_csv(summary_path).to_csv(final_summary, index=False, encoding="utf-8-sig")
        with open(zip_path, "rb") as f_in, open(final_zip, "wb") as f_out:
            f_out.write(f_in.read())

    return final_summary, final_zip


with gr.Blocks(title="CSV Unit/Chapter Summary + Chapter-wise Topic ZIP") as demo:
    gr.Markdown(
        """
### Upload CSV (must have columns: **Unit**, **chapter**, **topic**)

**Outputs**
1) **unit_chapters_summary.csv**: one row per Unit, with all unique Chapters joined by commas  
2) **chapter_wise_topics.zip**: one CSV per Chapter listing Topics under that chapter
"""
    )

    inp = gr.File(label="Upload your CSV", file_types=[".csv"])
    btn = gr.Button("Process")

    out_summary = gr.File(label="Download Unit → Chapters Summary CSV")
    out_zip = gr.File(label="Download Chapter-wise Topics ZIP")

    btn.click(fn=process_csv, inputs=[inp], outputs=[out_summary, out_zip])

if __name__ == "__main__":
    demo.launch()