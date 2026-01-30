import tempfile
from datetime import datetime
from io import BytesIO
import re
import zipfile

import gradio as gr
import pandas as pd


def clean_filename(filename: str) -> str:
    """Clean filename to remove invalid characters."""
    filename = re.sub(r'[<>:"/\\|?*]', '_', str(filename))
    filename = filename.replace(' ', '_')
    filename = filename.replace('(', '').replace(')', '')
    filename = filename.replace('[', '').replace(']', '')
    filename = re.sub(r'_+', '_', filename)
    filename = filename.strip('_')
    if len(filename) > 50:
        filename = filename[:50]
    filename = filename.rstrip('_')
    return filename


def get_unit_prefix(unit_name: str) -> str:
    """Extract unit number for filename prefix."""
    match = re.search(r'UNIT\s*(\d+)', str(unit_name), re.IGNORECASE)
    if match:
        return f"UNIT{match.group(1)}"
    return "UNIT"


def clean_topic_name(topic):
    """Clean topic name by replacing commas with hyphens."""
    if pd.isna(topic):
        return topic
    topic_str = str(topic).replace(',', ' -')
    topic_str = re.sub(r'\s+', ' ', topic_str)
    return topic_str.strip()


def has_tamil_characters(text) -> bool:
    """Check if text contains Tamil characters."""
    if pd.isna(text):
        return False
    return bool(re.search(r'[\u0B80-\u0BFF]', str(text)))


def wrap_tamil_in_html(topic):
    """Wrap Tamil content in HTML tags with $editorvalue in correct format."""
    if pd.isna(topic):
        return topic

    topic_str = str(topic)
    if has_tamil_characters(topic_str):
        return f'$editorvalue <p class="MsoNormal" style=""><span style="">{topic_str}</span></p>'

    return topic_str


def create_unit_chapter_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Create Unit-Chapter mapping."""
    unit_chapter_map = []

    for unit in df['Unit'].unique():
        if pd.notna(unit):
            unit_df = df[df['Unit'] == unit]
            chapters = unit_df['Chapter'].unique()
            chapters = [ch for ch in chapters if pd.notna(ch)]

            unit_chapter_map.append({
                'Unit': unit,
                'Chapters': ', '.join(chapters)
            })

    return pd.DataFrame(unit_chapter_map)


def segregate_by_chapter(df: pd.DataFrame, remove_duplicates: bool = False):
    """Segregate topics by chapter with unit prefix in filename (no folders)."""
    segregated = {}

    for unit in df['Unit'].unique():
        if pd.notna(unit):
            unit_df = df[df['Unit'] == unit]
            unit_prefix = get_unit_prefix(str(unit))

            for chapter in unit_df['Chapter'].unique():
                if pd.notna(chapter):
                    chapter_df = unit_df[unit_df['Chapter'] == chapter].copy()
                    clean_chapter_name = clean_filename(str(chapter))

                    topics_list = []
                    for topic in chapter_df['Topic'].tolist():
                        cleaned = clean_topic_name(topic)
                        wrapped = wrap_tamil_in_html(cleaned)
                        topics_list.append(wrapped)

                    if remove_duplicates:
                        seen = set()
                        topics_list = [t for t in topics_list if not (t in seen or seen.add(t))]

                    topic_only_df = pd.DataFrame({'Topic': topics_list})
                    filename = f"{unit_prefix}_{clean_chapter_name}"

                    segregated[filename] = {
                        'data': topic_only_df,
                        'unit': str(unit),
                        'chapter': str(chapter),
                        'count': len(topic_only_df),
                        'topics': topic_only_df['Topic'].tolist()
                    }

    return segregated


def create_chapter_zip(segregated_data, include_summary: bool = True) -> BytesIO:
    """Create ZIP file with flat structure - all files at root level."""
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, chapter_info in segregated_data.items():
            csv_data = chapter_info['data'].to_csv(index=False, encoding='utf-8-sig')
            zip_file.writestr(f"{filename}.csv", csv_data.encode('utf-8-sig'))

        if include_summary:
            summary_lines = [
                "=" * 70,
                "TOPIC SEGREGATION BY CHAPTER - SUMMARY",
                "=" * 70,
                "",
                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Total Files: {len(segregated_data)}",
                f"Total Topics: {sum(info['count'] for info in segregated_data.values())}",
                "",
                "=" * 70,
                "FILE LIST",
                "=" * 70,
                "",
            ]

            current_unit = None
            for filename, chapter_info in sorted(segregated_data.items()):
                unit = chapter_info['unit']
                chapter = chapter_info['chapter']

                if unit != current_unit:
                    summary_lines.append(f"\n📚 {unit}")
                    current_unit = unit

                summary_lines.append(f"   📄 {filename}.csv ({chapter_info['count']} topics)")
                summary_lines.append(f"      Chapter: {chapter}")
                summary_lines.append("      Topics:")
                for topic in chapter_info['topics']:
                    summary_lines.append(f"         • {topic}")
                summary_lines.append("")

            summary_lines.extend([
                "=" * 70,
                "END OF SUMMARY",
                "=" * 70,
            ])

            summary_text = "\n".join(summary_lines)
            zip_file.writestr("SUMMARY.txt", summary_text.encode('utf-8-sig'))

    zip_buffer.seek(0)
    return zip_buffer


def read_csv_with_fallback(file_path: str):
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252']
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            return df, encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None, None


def summarize_structure(df: pd.DataFrame) -> str:
    lines = []
    for unit in df['Unit'].dropna().unique():
        unit_df = df[df['Unit'] == unit]
        chapters = unit_df['Chapter'].dropna().unique()
        lines.append(f"**{unit}** — Chapters: {len(chapters)}, Topics: {len(unit_df)}")
        for chapter in chapters:
            chapter_count = len(unit_df[unit_df['Chapter'] == chapter])
            lines.append(f"- {chapter} ({chapter_count} topics)")
        lines.append("")
    return "\n".join(lines) or "No structure available."


def preview_files(df: pd.DataFrame) -> str:
    lines = []
    units = sorted([u for u in df['Unit'].unique() if pd.notna(u)])
    for unit in units:
        unit_df = df[df['Unit'] == unit]
        chapters = sorted([c for c in unit_df['Chapter'].unique() if pd.notna(c)])
        unit_prefix = get_unit_prefix(str(unit))
        lines.append(f"**{unit}:**")
        for chapter in chapters:
            chapter_df = unit_df[unit_df['Chapter'] == chapter]
            clean_chapter = clean_filename(str(chapter))
            lines.append(f"- `{unit_prefix}_{clean_chapter}.csv` ({len(chapter_df)} topics)")
        lines.append("")
    return "\n".join(lines) or "No files to preview."


def load_csv(file_path: str):
    if not file_path:
        return None, "", "", pd.DataFrame(), "", ""

    df, used_encoding = read_csv_with_fallback(file_path)
    if df is None:
        return None, "❌ Could not read file. Please save your CSV with UTF-8 encoding.", "", pd.DataFrame(), "", ""

    required_columns = ['Unit', 'Chapter', 'Topic']
    if not all(col in df.columns for col in required_columns):
        return None, (
            f"❌ CSV must have these columns: {', '.join(required_columns)}\n\n"
            f"Your columns: {', '.join(df.columns)}"
        ), "", pd.DataFrame(), "", ""

    encoding_note = ""
    if used_encoding not in ['utf-8', 'utf-8-sig']:
        encoding_note = (
            f"⚠️ File read with '{used_encoding}' encoding. For Tamil characters, please use UTF-8."
        )

    stats_md = (
        f"**Total Records:** {len(df)}  |  "
        f"**Units:** {df['Unit'].nunique()}  |  "
        f"**Chapters:** {df['Chapter'].nunique()}  |  "
        f"**Topics:** {df['Topic'].nunique()}"
    )

    preview_df = df.head(10)
    structure_md = summarize_structure(df)
    files_md = preview_files(df)

    return df, encoding_note, stats_md, preview_df, structure_md, files_md


def generate_mapping(df: pd.DataFrame):
    if df is None:
        return pd.DataFrame(), None, None, "❗ Please upload a valid CSV first."

    unit_chapter_df = create_unit_chapter_mapping(df)

    csv_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    unit_chapter_df.to_csv(csv_file.name, index=False, encoding='utf-8-sig')

    excel_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    with pd.ExcelWriter(excel_file.name, engine='openpyxl') as writer:
        unit_chapter_df.to_excel(writer, index=False, sheet_name='Unit-Chapter Mapping')

    return unit_chapter_df, csv_file.name, excel_file.name, "✅ Mapping created successfully."


def generate_zip(df: pd.DataFrame, include_summary: bool, remove_duplicates: bool):
    if df is None:
        return None, pd.DataFrame(), "", "❗ Please upload a valid CSV first."

    segregated_data = segregate_by_chapter(df, remove_duplicates)
    zip_buffer = create_chapter_zip(segregated_data, include_summary)

    zip_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    zip_file.write(zip_buffer.getvalue())
    zip_file.close()

    files_rows = []
    for filename, chapter_info in segregated_data.items():
        files_rows.append({
            'Filename': f"{filename}.csv",
            'Unit': chapter_info['unit'],
            'Chapter': chapter_info['chapter'],
            'Topics': chapter_info['count'],
        })

    files_df = pd.DataFrame(files_rows).sort_values(['Unit', 'Chapter']) if files_rows else pd.DataFrame()

    summary_note = "📄 SUMMARY.txt included" if include_summary else ""

    return zip_file.name, files_df, summary_note, "✅ ZIP file created successfully."


CUSTOM_CSS = """
#app-title {
  font-size: 2.2rem;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.section-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 16px 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}
"""


def build_app():
    theme = gr.themes.Soft(primary_hue="blue", secondary_hue="cyan")

    with gr.Blocks(theme=theme, css=CUSTOM_CSS) as demo:
        gr.Markdown("# 📚 Unit-Chapter-Topic Processor", elem_id="app-title")
        gr.Markdown(
            "Upload your CSV and generate unit-chapter mapping or chapter-wise topic files. "
            "Supports Tamil content with special HTML wrapping."
        )

        with gr.Row():
            with gr.Column(scale=2):
                file_input = gr.File(label="Upload CSV", file_types=[".csv"], type="filepath")
                encoding_warning = gr.Markdown()
            with gr.Column(scale=3):
                stats_md = gr.Markdown()

        preview_df = gr.Dataframe(label="Preview (first 10 rows)", interactive=False)
        structure_md = gr.Markdown(label="Data structure overview")

        df_state = gr.State()

        with gr.Tabs():
            with gr.TabItem("📊 Unit-Chapter Mapping"):
                mapping_btn = gr.Button("Generate Unit-Chapter Mapping", variant="primary")
                mapping_status = gr.Markdown()
                mapping_df = gr.Dataframe(label="Mapping Result", interactive=False)
                with gr.Row():
                    mapping_csv = gr.File(label="Download CSV")
                    mapping_excel = gr.File(label="Download Excel")

            with gr.TabItem("📁 Topic Segregation"):
                files_md = gr.Markdown(label="Files that will be generated")
                with gr.Row():
                    include_summary = gr.Checkbox(value=True, label="Include summary file")
                    remove_duplicates = gr.Checkbox(value=True, label="Remove duplicate topics")
                zip_btn = gr.Button("Generate ZIP File", variant="primary")
                zip_status = gr.Markdown()
                zip_file = gr.File(label="Download ZIP")
                zip_contents = gr.Dataframe(label="ZIP Contents", interactive=False)
                summary_note = gr.Markdown()

        file_input.change(
            fn=load_csv,
            inputs=file_input,
            outputs=[df_state, encoding_warning, stats_md, preview_df, structure_md, files_md],
        )

        mapping_btn.click(
            fn=generate_mapping,
            inputs=df_state,
            outputs=[mapping_df, mapping_csv, mapping_excel, mapping_status],
        )

        zip_btn.click(
            fn=generate_zip,
            inputs=[df_state, include_summary, remove_duplicates],
            outputs=[zip_file, zip_contents, summary_note, zip_status],
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch()
