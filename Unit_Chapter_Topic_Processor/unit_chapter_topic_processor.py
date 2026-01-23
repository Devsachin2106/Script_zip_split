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
    filename = re.sub(r'_+', '_', filename)
    filename = filename.strip('_')
    if len(filename) > 100:
        filename = filename[:100]
    return filename

def create_unit_chapter_mapping(df):
    """
    Create Unit-Chapter mapping
    Output: Unit | Chapters (comma-separated)
    """
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

def segregate_by_chapter(df):
    """
    Segregate topics by chapter
    Create separate CSV for each chapter with its topics
    """
    segregated = {}
    
    chapters = df['Chapter'].unique()
    chapters = [ch for ch in chapters if pd.notna(ch)]
    
    for chapter in sorted(chapters):
        chapter_df = df[df['Chapter'] == chapter].copy()
        clean_chapter_name = clean_filename(str(chapter))
        
        segregated[clean_chapter_name] = {
            'data': chapter_df,
            'original_name': str(chapter),
            'count': len(chapter_df),
            'topics': chapter_df['Topic'].tolist()
        }
    
    return segregated

def create_chapter_zip(segregated_data, include_summary=True):
    """Create ZIP file with chapter-wise topic CSVs"""
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add each chapter CSV
        for chapter_name, chapter_info in segregated_data.items():
            csv_data = chapter_info['data'].to_csv(index=False)
            filename = f"{chapter_name}.csv"
            zip_file.writestr(filename, csv_data)
        
        # Add summary file
        if include_summary:
            summary_lines = []
            summary_lines.append("=" * 70)
            summary_lines.append("TOPIC SEGREGATION BY CHAPTER - SUMMARY")
            summary_lines.append("=" * 70)
            summary_lines.append("")
            summary_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            summary_lines.append(f"Total Chapters: {len(segregated_data)}")
            summary_lines.append(f"Total Topics: {sum(info['count'] for info in segregated_data.values())}")
            summary_lines.append("")
            summary_lines.append("=" * 70)
            summary_lines.append("CHAPTER-WISE BREAKDOWN")
            summary_lines.append("=" * 70)
            summary_lines.append("")
            
            for idx, (chapter_name, chapter_info) in enumerate(segregated_data.items(), 1):
                summary_lines.append(f"{idx}. CHAPTER: {chapter_info['original_name']}")
                summary_lines.append(f"   File: {chapter_name}.csv")
                summary_lines.append(f"   Topics Count: {chapter_info['count']}")
                summary_lines.append(f"   Topics:")
                for topic in chapter_info['topics']:
                    summary_lines.append(f"      - {topic}")
                summary_lines.append("")
                summary_lines.append("-" * 70)
                summary_lines.append("")
            
            summary_lines.append("=" * 70)
            summary_lines.append("END OF SUMMARY")
            summary_lines.append("=" * 70)
            
            summary_text = "\n".join(summary_lines)
            zip_file.writestr("SUMMARY.txt", summary_text)
    
    zip_buffer.seek(0)
    return zip_buffer

def main():
    # Header
    st.title("📚 Unit-Chapter-Topic Processor")
    st.markdown("### Process your Unit-Chapter-Topic data in two ways")
    st.markdown("---")
    
    # Instructions
    with st.expander("📖 How to Use", expanded=True):
        st.markdown("""
        This tool provides **TWO processing options**:
        
        **Option 1: Unit-Chapter Mapping** 📊
        - Combines all chapters under each unit
        - Output: Unit | Chapters (comma-separated)
        - Example: "Indian Polity (UNIT 4)" | "Evolution of Indian Constitution, Making of Indian Constitution, Preamble"
        
        **Option 2: Topic Segregation by Chapter** 📁
        - Creates separate CSV file for each chapter
        - Each CSV contains all topics for that chapter
        - Downloads as ZIP file
        
        **Your CSV must have 3 columns:**
        - Unit (e.g., "Indian Polity (UNIT 4)")
        - Chapter (e.g., "Evolution of Indian Constitution")
        - Topic (e.g., "Regulating act of 1773")
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
            df = pd.read_csv(uploaded_file)
            
            # Validate columns
            required_columns = ['Unit', 'Chapter', 'Topic']
            if not all(col in df.columns for col in required_columns):
                st.error(f"❌ CSV must have these columns: {', '.join(required_columns)}")
                st.info(f"Your columns: {', '.join(df.columns)}")
                return
            
            st.session_state.uploaded_df = df
            
            st.success(f"✅ File uploaded successfully!")
            
            # Stats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", len(df))
            with col2:
                st.metric("Units", df['Unit'].nunique())
            with col3:
                st.metric("Chapters", df['Chapter'].nunique())
            with col4:
                st.metric("Topics", df['Topic'].nunique())
            
            # Preview
            with st.expander("📋 Preview Data", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)
            
            # Show structure
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
    
    # Processing Options
    if st.session_state.uploaded_df is not None:
        df = st.session_state.uploaded_df
        
        st.markdown("---")
        st.header("Step 2: Choose Processing Option 🎯")
        
        tab1, tab2 = st.tabs(["📊 Option 1: Unit-Chapter Mapping", "📁 Option 2: Topic Segregation by Chapter"])
        
        # ========== OPTION 1: Unit-Chapter Mapping ==========
        with tab1:
            st.markdown("### Unit-Chapter Mapping")
            st.info("This will create a table with Unit and all its Chapters (comma-separated)")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Output format:**")
                st.code("""
Unit                          | Chapters
------------------------------|----------------------------------
Indian Polity (UNIT 4)        | Evolution of Indian Constitution, 
                              | Making of Indian Constitution, 
                              | Preamble
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
                        
                        # Display result
                        st.markdown("### 📋 Result:")
                        st.dataframe(unit_chapter_df, use_container_width=True)
                        
                        # Download options
                        st.markdown("### 📥 Download Options:")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # CSV download
                            csv_data = unit_chapter_df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download as CSV",
                                data=csv_data,
                                file_name=f"Unit_Chapter_Mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        with col2:
                            # Excel download
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
        
        # ========== OPTION 2: Topic Segregation ==========
        with tab2:
            st.markdown("### Topic Segregation by Chapter")
            st.info("This will create separate CSV files for each chapter with all its topics, packaged in a ZIP file")
            
            # Show what will be generated
            chapters = df['Chapter'].unique()
            chapters = [ch for ch in chapters if pd.notna(ch)]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Files that will be generated:**")
                with st.expander("View all chapter files", expanded=True):
                    for chapter in sorted(chapters):
                        chapter_df = df[df['Chapter'] == chapter]
                        clean_name = clean_filename(chapter)
                        st.markdown(f"- `{clean_name}.csv` ({len(chapter_df)} topics)")
            
            with col2:
                st.markdown("**Stats:**")
                st.metric("CSV Files", len(chapters))
                st.metric("Total Topics", len(df))
                
                include_summary = st.checkbox(
                    "Include summary file",
                    value=True,
                    help="Add SUMMARY.txt with details",
                    key="summary_check"
                )
            
            # Preview distribution
            with st.expander("📊 Topics per Chapter", expanded=True):
                chapter_counts = df['Chapter'].value_counts().sort_index()
                st.bar_chart(chapter_counts)
            
            if st.button("🚀 Generate ZIP File", type="primary", use_container_width=True, key="btn_zip"):
                with st.spinner("🔄 Creating chapter-wise CSV files and ZIP..."):
                    try:
                        segregated_data = segregate_by_chapter(df)
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
                        
                        # Show contents
                        st.markdown("---")
                        st.markdown("### 📂 ZIP Contents:")
                        
                        files_list = []
                        for chapter_name, chapter_info in segregated_data.items():
                            files_list.append({
                                'Filename': f"{chapter_name}.csv",
                                'Chapter': chapter_info['original_name'],
                                'Topics': chapter_info['count']
                            })
                        
                        if include_summary:
                            files_list.append({
                                'Filename': 'SUMMARY.txt',
                                'Chapter': 'Summary Report',
                                'Topics': '-'
                            })
                        
                        files_df = pd.DataFrame(files_list)
                        st.dataframe(files_df, use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"❌ Error creating ZIP: {e}")
                        st.exception(e)
    
    else:
        st.info("👆 Please upload a CSV file to get started")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>💡 <b>Quick Guide:</b></p>
        <p><b>Option 1:</b> Get Unit → Chapters mapping in one CSV</p>
        <p><b>Option 2:</b> Get separate CSV for each chapter with its topics</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
