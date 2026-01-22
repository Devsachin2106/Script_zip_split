# answer_script.py
import streamlit as st
import zipfile
import os
import tempfile
from pathlib import Path
from datetime import datetime
import csv

st.set_page_config(page_title="Split ZIP into 500MB parts", layout="wide")

st.title("📦 Split Answer Scripts ZIP into 500MB ZIP Parts (No file split)")
st.caption("Creates multiple ZIP files up to max size. If current ZIP >= threshold (e.g., 480MB), next file goes to next ZIP.")

# -----------------------------
# Settings
# -----------------------------
MAX_ZIP_MB = st.number_input("Max ZIP size (MB)", min_value=50, max_value=5000, value=500, step=50)
THRESHOLD_MB = st.number_input(
    "Threshold to stop adding more files (MB)",
    min_value=0,
    max_value=int(MAX_ZIP_MB),
    value=min(480, int(MAX_ZIP_MB)),
    step=10,
    help="If current ZIP size >= this value, the next file will go to the next ZIP even if space remains."
)

SORT_MODE = st.selectbox(
    "File ordering",
    ["Keep ZIP order (as stored)", "Sort by filename (A→Z)", "Sort by size (small→large)"],
    index=1
)

INCLUDE_EXTENSIONS = st.text_input(
    "Optional: include only these extensions (comma-separated, leave empty for all)",
    value="",
    help="Example: pdf,jpg,png"
).strip()

# -----------------------------
# Input mode
# -----------------------------
st.subheader("1) Choose Input Method")
input_mode = st.radio("Input type", ["Use server file path (recommended for 5–10GB)", "Upload ZIP (small only)"])

uploaded_zip = None
server_zip_path = None

if input_mode == "Upload ZIP (small only)":
    uploaded_zip = st.file_uploader("Upload ZIP file", type=["zip"])
else:
    server_zip_path = st.text_input("Enter ZIP file path", value="D:\\C\\Code\\Script\\input.zip")

# -----------------------------
# Helpers
# -----------------------------
def bytes_to_mb(b: int) -> float:
    return b / (1024 * 1024)

def normalize_exts(ext_str: str):
    if not ext_str:
        return None
    exts = [e.strip().lower().lstrip(".") for e in ext_str.split(",") if e.strip()]
    return set(exts) if exts else None

def should_include(filename: str, allowed_exts):
    if not allowed_exts:
        return True
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    return ext in allowed_exts

def safe_name(s: str) -> str:
    return s.replace("\\", "_").replace("/", "_").replace(":", "_")

def apply_sort(infos):
    if SORT_MODE == "Keep ZIP order (as stored)":
        return infos
    if SORT_MODE == "Sort by filename (A→Z)":
        return sorted(infos, key=lambda x: x.filename.lower())
    if SORT_MODE == "Sort by size (small→large)":
        return sorted(infos, key=lambda x: x.file_size)
    return infos

# -----------------------------
# Main
# -----------------------------
st.subheader("2) Split & Create ZIP Parts")

if st.button("🚀 Process ZIP", type="primary"):
    allowed_exts = normalize_exts(INCLUDE_EXTENSIONS)

    # Prepare temp working dir
    work_dir = Path(tempfile.mkdtemp(prefix="zip_split_"))
    out_dir = work_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve input ZIP path
    if uploaded_zip is not None:
        zip_path = work_dir / "input.zip"
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.getbuffer())
    else:
        if not server_zip_path:
            st.error("Please provide a ZIP path.")
            st.stop()
        zip_path = Path(server_zip_path).expanduser()
        if not zip_path.exists():
            st.error(f"ZIP not found: {zip_path}")
            st.stop()

    max_bytes = int(MAX_ZIP_MB * 1024 * 1024)
    threshold_bytes = int(THRESHOLD_MB * 1024 * 1024)

    # Read ZIP file list
    try:
        with zipfile.ZipFile(zip_path, "r") as zin:
            infos = [i for i in zin.infolist() if not i.is_dir()]
    except zipfile.BadZipFile:
        st.error("Invalid ZIP file.")
        st.stop()

    # Filter by extension
    infos = [i for i in infos if should_include(i.filename, allowed_exts)]
    infos = apply_sort(infos)

    if not infos:
        st.warning("No files found (after filtering).")
        st.stop()

    # Validate: no single file > max
    too_big = [i for i in infos if i.file_size > max_bytes]
    if too_big:
        st.error(
            "Some files are larger than the max ZIP size. Cannot pack without splitting (splitting disabled).\n\n"
            + "\n".join([f"- {i.filename} ({bytes_to_mb(i.file_size):.2f} MB)" for i in too_big[:30]])
        )
        st.stop()

    # Init
    base_name = safe_name(zip_path.stem)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    part_index = 1
    part_bytes = 0
    part_file_count = 0

    current_zip_name = f"{base_name}_part_{part_index:03d}_{timestamp}.zip"
    current_zip_path = out_dir / current_zip_name

    manifest_rows = []
    total_files = len(infos)

    progress = st.progress(0)
    status = st.empty()

    zin = zipfile.ZipFile(zip_path, "r")
    zout = zipfile.ZipFile(current_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6)

    def close_and_open_new_zip():
        nonlocal_needed = False  # just to show we are NOT using nonlocal 😄
        # close current
        zout.close()

    # We will manage "new zip" without nested function changing variables
    for idx, info in enumerate(infos, start=1):
        file_size = info.file_size

        # RULE A: If current part already crossed threshold, start next zip (only if current has something)
        if part_file_count > 0 and part_bytes >= threshold_bytes:
            zout.close()
            part_index += 1
            part_bytes = 0
            part_file_count = 0
            current_zip_name = f"{base_name}_part_{part_index:03d}_{timestamp}.zip"
            current_zip_path = out_dir / current_zip_name
            zout = zipfile.ZipFile(current_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6)

        # RULE B: If adding this file exceeds max, start next zip (only if current has something)
        if part_file_count > 0 and (part_bytes + file_size > max_bytes):
            zout.close()
            part_index += 1
            part_bytes = 0
            part_file_count = 0
            current_zip_name = f"{base_name}_part_{part_index:03d}_{timestamp}.zip"
            current_zip_path = out_dir / current_zip_name
            zout = zipfile.ZipFile(current_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6)

        # Copy file bytes to output zip (NO split)
        with zin.open(info, "r") as src:
            data = src.read()
            zout.writestr(info.filename, data)

        part_bytes += file_size
        part_file_count += 1

        manifest_rows.append({
            "original_file": info.filename,
            "original_size_mb": round(bytes_to_mb(file_size), 2),
            "output_zip": current_zip_name,
            "output_zip_total_mb_after_add": round(bytes_to_mb(part_bytes), 2),
            "part_index": part_index
        })

        progress.progress(idx / total_files)
        status.write(
            f"✅ Packed {idx}/{total_files} | Current: {current_zip_name} "
            f"({bytes_to_mb(part_bytes):.2f} MB, {part_file_count} files)"
        )

    zout.close()
    zin.close()

    # Manifest CSV
    manifest_path = out_dir / f"{base_name}_manifest_{timestamp}.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["original_file", "original_size_mb", "output_zip", "output_zip_total_mb_after_add", "part_index"]
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    # Show output list
    output_files = sorted(out_dir.glob("*.zip"))
    st.success(f"Done ✅ Created {len(output_files)} ZIP parts + manifest CSV.")
    st.info(f"Output folder: {out_dir}")

    st.subheader("3) Download Manifest (Recommended)")
    with open(manifest_path, "rb") as f:
        st.download_button(
            label=f"⬇️ Download Manifest CSV ({manifest_path.name})",
            data=f.read(),
            file_name=manifest_path.name,
            mime="text/csv"
        )

    st.warning(
        "⚠️ For 500MB ZIP parts, Streamlit download buttons may be slow or memory-heavy.\n"
        "Better: Open the output folder path shown above and take ZIPs directly from there."
    )

    st.write("Created ZIP parts:")
    for p in output_files:
        st.write(f"- {p.name} ({bytes_to_mb(p.stat().st_size):.2f} MB)")
    st.write("Process completed. You can now access the output ZIP files and manifest CSV in the specified output folder.")