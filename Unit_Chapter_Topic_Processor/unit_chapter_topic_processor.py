import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
from datetime import datetime
import re

st.set_page_config(page_title="Unit-Chapter-Topic Processor", layout="wide", page_icon="📚")

# Initialize session state
if 'uploaded_df' not in st.session_state:
    st.session_state.uploaded_df = None
if 'unit_chapter_df' not in st.session_state:
    st.session_state.unit_chapter_df = None
if 'segregated_data' not in st.session_state:
    st.session_state.segregated_data = {}

def clean_filename(filename):
    """Clean filename to remove invalid characters"""
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

def get_unit_prefix(unit_name):
    """Extract unit number for filename prefix"""
    match = re.search(r'UNIT\s*(\d+)', str(unit_name), re.IGNORECASE)
    if match:
        return f"UNIT{match.group(1)}"
    return "UNIT"

def clean_topic_name(topic):
    """Clean topic name by replacing commas with hyphens"""
    if pd.isna(topic):
        return topic
    # Replace comma with space-hyphen-space
    topic_str = str(topic).replace(',', ' -')
    # Clean up multiple spaces
    topic_str = re.sub(r'\s+', ' ', topic_str)
    return topic_str.strip()

def has_tamil_characters(text):
    """Check if text contains Tamil characters"""
    if pd.isna(text):
        return False
    # Tamil Unicode range: \u0B80-\u0BFF
    return bool(re.search(r'[\u0B80-\u0BFF]', str(text)))

def wrap_tamil_in_html(topic):
    """Wrap Tamil content in HTML tags with $editorvalue in correct format"""
    if pd.isna(topic):
        return topic
    
    topic_str = str(topic)
    
    # If contains Tamil characters, wrap in HTML with proper format
    if has_tamil_characters(topic_str):
        return f'$editorvalue <p class="MsoNormal" style=""><span style="">{topic_str}</span></p>'
    
    return topic_str

def create_unit_chapter_mapping(df):
    """Create Unit-Chapter mapping"""
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

def segregate_by_chapter(df, remove_duplicates=False):
    """Segregate topics by chapter with unit prefix in filename (no folders)"""
    segregated = {}
    
    for unit in df['Unit'].unique():
        if pd.notna(unit):
            unit_df = df[df['Unit'] == unit]
            unit_prefix = get_unit_prefix(str(unit))
            
            for chapter in unit_df['Chapter'].unique():
                if pd.notna(chapter):
                    chapter_df = unit_df[unit_df['Chapter'] == chapter].copy()
                    clean_chapter_name = clean_filename(str(chapter))
                    
                    # Get topics list, clean them, and wrap Tamil in HTML
                    topics_list = []
                    for t in chapter_df['Topic'].tolist():
                        cleaned = clean_topic_name(t)
                        wrapped = wrap_tamil_in_html(cleaned)
                        topics_list.append(wrapped)
                    
                    # Remove duplicates while preserving order if requested
                    if remove_duplicates:
                        seen = set()
                        topics_list = [t for t in topics_list if not (t in seen or seen.add(t))]
                    
                    # Create only Topic column dataframe
                    topic_only_df = pd.DataFrame({
                        'Topic': topics_list
                    })
                    
                    # Filename: UNIT4_ChapterName.csv (no folders)
                    filename = f"{unit_prefix}_{clean_chapter_name}"
                    
                    segregated[filename] = {
                        'data': topic_only_df,
                        'unit': str(unit),
                        'chapter': str(chapter),
                        'count': len(topic_only_df),
                        'topics': topic_only_df['Topic'].tolist()
                    }
    
    return segregated

def create_chapter_zip(segregated_data, include_summary=True):
    """Create ZIP file with flat structure - all files at root level"""
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add each chapter CSV at root level (no folders)
        for filename, chapter_info in segregated_data.items():
            # Convert to CSV with UTF-8 encoding for Tamil characters
            csv_data = chapter_info['data'].to_csv(index=False, encoding='utf-8-sig')
            zip_file.writestr(f"{filename}.csv", csv_data.encode('utf-8-sig'))
        
        if include_summary:
            summary_lines = []
            summary_lines.append("=" * 70)
            summary_lines.append("TOPIC SEGREGATION BY CHAPTER - SUMMARY")
            summary_lines.append("=" * 70)
            summary_lines.append("")
            summary_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            summary_lines.append(f"Total Files: {len(segregated_data)}")
            summary_lines.append(f"Total Topics: {sum(info['count'] for info in segregated_data.values())}")
            summary_lines.append("")
            summary_lines.append("=" * 70)
            summary_lines.append("FILE LIST")
            summary_lines.append("=" * 70)
            summary_lines.append("")
            
            current_unit = None
            for filename, chapter_info in sorted(segregated_data.items()):
                unit = chapter_info['unit']
                chapter = chapter_info['chapter']
                
                if unit != current_unit:
                    summary_lines.append(f"\n📚 {unit}")
                    current_unit = unit
                
                summary_lines.append(f"   📄 {filename}.csv ({chapter_info['count']} topics)")
                summary_lines.append(f"      Chapter: {chapter}")
                summary_lines.append(f"      Topics:")
                for topic in chapter_info['topics']:
                    summary_lines.append(f"         • {topic}")
                summary_lines.append("")
            
            summary_lines.append("=" * 70)
            summary_lines.append("END OF SUMMARY")
            summary_lines.append("=" * 70)
            
            summary_text = "\n".join(summary_lines)
            # Encode summary with UTF-8 for Tamil characters
            zip_file.writestr("SUMMARY.txt", summary_text.encode('utf-8-sig'))
    
    zip_buffer.seek(0)
    return zip_buffer

def main():
    st.title("📚 Unit-Chapter-Topic Processor")
    st.markdown("### Process your Unit-Chapter-Topic data in two ways")
    st.markdown("---")
    
    with st.expander("📖 How to Use", expanded=True):
        st.markdown("""
        **Option 1: Unit-Chapter Mapping** 📊
        - Combines all chapters under each unit
        - Output: Unit | Chapters (comma-separated)
        
        **Option 2: Topic Segregation by Chapter** 📁
        - Creates separate CSV file for each chapter
        - Each CSV contains only Topic column
        - Downloads as ZIP file
        - Files named as: UNIT4_ChapterName.csv
        
        **Your CSV must have 3 columns:**
        - Unit, Chapter, Topic
        """)
    
    st.markdown("---")
    
    # Step 1: File Upload
    st.header("Step 1: Upload CSV File 📁")
    
    uploaded_file = st.file_uploader(
        "Upload your CSV file with Unit, Chapter, and Topic columns",
        type=['csv'],
        help="CSV must have three columns: Unit, Chapter, Topic"
    )
    
    if uploaded_file:
        try:
            # Try reading with UTF-8 first, then fallback to other encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252']
            df = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding=encoding)
                    used_encoding = encoding
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if df is None:
                st.error("❌ Could not read file. Please save your CSV with UTF-8 encoding.")
                st.info("💡 In Excel: File → Save As → CSV UTF-8 (Comma delimited)")
                return
            
            if used_encoding != 'utf-8':
                st.warning(f"⚠️ File read with '{used_encoding}' encoding. For Tamil characters, please use UTF-8.")
            
            required_columns = ['Unit', 'Chapter', 'Topic']
            if not all(col in df.columns for col in required_columns):
                st.error(f"❌ CSV must have these columns: {', '.join(required_columns)}")
                st.info(f"Your columns: {', '.join(df.columns)}")
                return
            
            st.session_state.uploaded_df = df
            
            st.success(f"✅ File uploaded successfully!")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", len(df))
            with col2:
                st.metric("Units", df['Unit'].nunique())
            with col3:
                st.metric("Chapters", df['Chapter'].nunique())
            with col4:
                st.metric("Topics", df['Topic'].nunique())
            
            with st.expander("📋 Preview Data", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)
            
            with st.expander("📊 Data Structure Overview"):
                for unit in df['Unit'].unique():
                    if pd.notna(unit):
                        unit_df = df[df['Unit'] == unit]
                        chapters = unit_df['Chapter'].unique()
                        st.markdown(f"**{unit}**")
                        st.markdown(f"- Chapters: {len(chapters)}")
                        st.markdown(f"- Topics: {len(unit_df)}")
                        with st.expander(f"View chapters in {unit}"):
                            for ch in chapters:
                                if pd.notna(ch):
                                    ch_count = len(unit_df[unit_df['Chapter'] == ch])
                                    st.markdown(f"  - {ch} ({ch_count} topics)")
                        st.markdown("")
            
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
            return
    
    if st.session_state.uploaded_df is not None:
        df = st.session_state.uploaded_df
        
        st.markdown("---")
        st.header("Step 2: Choose Processing Option 🎯")
        
        tab1, tab2 = st.tabs(["📊 Option 1: Unit-Chapter Mapping", "📁 Option 2: Topic Segregation by Chapter"])
        
        # OPTION 1
        with tab1:
            st.markdown("### Unit-Chapter Mapping")
            st.info("Creates a table with Unit and all its Chapters (comma-separated)")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Output format:**")
                st.code("""
Unit                     | Chapters
-------------------------|-------------------------
Indian Polity (UNIT 4)   | Evolution, Making, Preamble
                """)
            
            with col2:
                st.markdown("**Stats:**")
                st.metric("Total Units", df['Unit'].nunique())
                st.metric("Total Chapters", df['Chapter'].nunique())
            
            if st.button("🚀 Generate Unit-Chapter Mapping", type="primary", use_container_width=True, key="btn_mapping"):
                with st.spinner("Creating Unit-Chapter mapping..."):
                    try:
                        unit_chapter_df = create_unit_chapter_mapping(df)
                        st.session_state.unit_chapter_df = unit_chapter_df
                        
                        st.success("✅ Mapping created successfully!")
                        
                        st.markdown("### 📋 Result:")
                        st.dataframe(unit_chapter_df, use_container_width=True)
                        
                        st.markdown("### 📥 Download Options:")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            csv_data = unit_chapter_df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="📥 Download as CSV",
                                data=csv_data.encode('utf-8-sig'),
                                file_name=f"Unit_Chapter_Mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        with col2:
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                unit_chapter_df.to_excel(writer, index=False, sheet_name='Unit-Chapter Mapping')
                            excel_data = output.getvalue()
                            
                            st.download_button(
                                label="📥 Download as Excel",
                                data=excel_data,
                                file_name=f"Unit_Chapter_Mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                    
                    except Exception as e:
                        st.error(f"❌ Error creating mapping: {e}")
                        st.exception(e)
        
        # OPTION 2
        with tab2:
            st.markdown("### Topic Segregation by Chapter")
            st.info("Creates separate CSV files for each chapter with only Topic column. Tamil content automatically wrapped in HTML tags with $editorvalue. Files named as: UNIT4_ChapterName.csv")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Files that will be generated:**")
                with st.expander("View all files", expanded=True):
                    units = df['Unit'].unique()
                    for unit in sorted(units):
                        if pd.notna(unit):
                            unit_df = df[df['Unit'] == unit]
                            chapters = unit_df['Chapter'].unique()
                            unit_prefix = get_unit_prefix(str(unit))
                            st.markdown(f"**{unit}:**")
                            for chapter in sorted(chapters):
                                if pd.notna(chapter):
                                    chapter_df = unit_df[unit_df['Chapter'] == chapter]
                                    clean_chapter = clean_filename(str(chapter))
                                    st.markdown(f"   └─ `{unit_prefix}_{clean_chapter}.csv` ({len(chapter_df)} topics)")
                            st.markdown("")
            
            with col2:
                st.markdown("**Stats:**")
                st.metric("CSV Files", df['Chapter'].nunique())
                st.metric("Total Topics", len(df))
                
                include_summary = st.checkbox(
                    "Include summary file",
                    value=True,
                    help="Add SUMMARY.txt",
                    key="summary_check"
                )
                
                remove_duplicates = st.checkbox(
                    "Remove duplicate topics",
                    value=True,
                    help="Remove duplicate topic names within same chapter",
                    key="remove_dup_check"
                )
            
            with st.expander("📊 Topics per Chapter", expanded=True):
                chapter_counts = df['Chapter'].value_counts().sort_index()
                st.bar_chart(chapter_counts)
            
            if st.button("🚀 Generate ZIP File", type="primary", use_container_width=True, key="btn_zip"):
                with st.spinner("🔄 Creating CSV files and ZIP..."):
                    try:
                        segregated_data = segregate_by_chapter(df, remove_duplicates)
                        st.session_state.segregated_data = segregated_data
                        
                        zip_buffer = create_chapter_zip(segregated_data, include_summary)
                        
                        st.success("✅ ZIP file created successfully!")
                        
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        zip_filename = f"Topics_by_Chapter_{timestamp}.zip"
                        
                        st.download_button(
                            label="📥 Download ZIP File",
                            data=zip_buffer,
                            file_name=zip_filename,
                            mime="application/zip",
                            type="primary",
                            use_container_width=True
                        )
                        
                        st.markdown("---")
                        st.markdown("### 📂 ZIP Contents:")
                        
                        files_by_unit = {}
                        for filename, chapter_info in segregated_data.items():
                            unit = chapter_info['unit']
                            if unit not in files_by_unit:
                                files_by_unit[unit] = []
                            files_by_unit[unit].append({
                                'Filename': filename + '.csv',
                                'Chapter': chapter_info['chapter'],
                                'Topics': chapter_info['count']
                            })
                        
                        for unit, files in sorted(files_by_unit.items()):
                            with st.expander(f"📚 {unit}", expanded=True):
                                files_df = pd.DataFrame(files)
                                st.dataframe(files_df, use_container_width=True)
                        
                        if include_summary:
                            st.info("📄 SUMMARY.txt included")
                        
                    except Exception as e:
                        st.error(f"❌ Error creating ZIP: {e}")
                        st.exception(e)
    
    else:
        st.info("👆 Please upload a CSV file to get started")
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>💡 <b>Quick Guide:</b></p>
        <p><b>Option 1:</b> Unit → Chapters mapping</p>
        <p><b>Option 2:</b> Separate CSV per chapter (Topic column only)</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()