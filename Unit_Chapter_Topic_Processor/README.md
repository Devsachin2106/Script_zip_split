# 📚 Unit-Chapter-Topic Processor

A Streamlit application that processes Unit-Chapter-Topic data in two powerful ways.

## 🎯 What It Does

This tool provides **TWO processing options** for your Unit-Chapter-Topic CSV data:

### **Option 1: Unit-Chapter Mapping** 📊
Aggregates all chapters under each unit into a single row.

**Input:**
```
Unit                    | Chapter                           | Topic
------------------------|-----------------------------------|------------------
Indian Polity (UNIT 4)  | Evolution of Indian Constitution  | Regulating act of 1773
Indian Polity (UNIT 4)  | Evolution of Indian Constitution  | Charter Act of 1793
Indian Polity (UNIT 4)  | Making of Indian Constitution     | Background
Indian Polity (UNIT 4)  | Preamble                          | Nature of State
```

**Output:**
```
Unit                    | Chapters
------------------------|-------------------------------------------------------------
Indian Polity (UNIT 4)  | Evolution of Indian Constitution, Making of Indian Constitution, Preamble
```

### **Option 2: Topic Segregation by Chapter** 📁
Creates separate CSV files for each chapter containing all its topics.

**Input:** Same as above

**Output ZIP contains:**
```
📦 Topics_by_Chapter_20260123.zip
  ├── Evolution_of_Indian_Constitution.csv (11 topics)
  ├── Making_of_Indian_Constitution.csv (6 topics)
  ├── Preamble.csv (4 topics)
  └── SUMMARY.txt
```

## 📋 Requirements

Your CSV file must have exactly **3 columns**:
1. **Unit** - The unit name (e.g., "Indian Polity (UNIT 4)")
2. **Chapter** - Chapter name within the unit
3. **Topic** - Individual topics under each chapter

## 🚀 Installation

1. Install Python 3.8 or higher
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## 💻 Running the Application

```bash
streamlit run unit_chapter_topic_processor.py
```

Browser opens automatically at `http://localhost:8501`

## 📖 How to Use

### Step 1: Upload File
- Click "Upload your CSV file"
- Select your CSV with Unit, Chapter, Topic columns
- See preview and statistics

### Step 2: Choose Option

#### **For Option 1 (Unit-Chapter Mapping):**
1. Go to "Option 1" tab
2. Click "Generate Unit-Chapter Mapping"
3. View the result table
4. Download as CSV or Excel

#### **For Option 2 (Topic Segregation):**
1. Go to "Option 2" tab
2. Review which files will be created
3. Check/uncheck "Include summary file"
4. Click "Generate ZIP File"
5. Download the ZIP
6. Extract to see individual chapter CSV files

## 📊 Features

### Option 1 Features:
✅ **Aggregates chapters per unit** - All chapters in one cell
✅ **Comma-separated format** - Easy to read
✅ **Duplicate removal** - Each chapter appears only once
✅ **Download as CSV/Excel** - Your choice of format

### Option 2 Features:
✅ **Separate file per chapter** - Organized and clean
✅ **ZIP packaging** - Easy to download and share
✅ **Optional summary** - Detailed breakdown of all chapters
✅ **Stats and preview** - See before you download
✅ **Clean filenames** - Handles special characters

## 📁 File Examples

### Option 1 Output (CSV/Excel):
```csv
Unit,Chapters
Indian Polity (UNIT 4),"Evolution of Indian Constitution, Making of Indian Constitution, Preamble"
Indian Economy (UNIT 5),"Basics of Economy, Nature of Indian Economy, Five-year plan"
```

### Option 2 Output (ZIP):
Each chapter gets its own CSV with all columns from original:
```csv
Unit,Chapter,Topic
Indian Polity (UNIT 4),Evolution of Indian Constitution,Regulating act of 1773
Indian Polity (UNIT 4),Evolution of Indian Constitution,Charter Act of 1793
...
```

## 🎨 User Interface

- **Clean Design** - Easy to navigate
- **Two Tabs** - Separate options clearly
- **Live Preview** - See data structure
- **Statistics** - Units, chapters, topics count
- **Progress Indicators** - Know what's happening
- **Error Handling** - Clear error messages

## ⚠️ Important Notes

1. **Column Names Matter**: Must be exactly "Unit", "Chapter", "Topic"
2. **CSV Format**: File must be in CSV format
3. **Headers Required**: First row must be column names
4. **No Empty Values**: Rows with empty Unit/Chapter will be skipped

## 🔧 Technical Details

### File Naming (Option 2):
Chapter names are cleaned for valid filenames:
- Special characters → `_`
- Spaces → `_`
- Multiple underscores → single `_`
- Length limit → 100 characters

**Examples:**
- `"Evolution of Indian Constitution"` → `Evolution_of_Indian_Constitution.csv`
- `"Charter Act of 1833"` → `Charter_Act_of_1833.csv`

### Summary File (Option 2):
Contains:
- Generation timestamp
- Total chapters and topics
- Complete breakdown of each chapter
- List of all topics per chapter
- File names generated

## 💡 Use Cases

### Option 1 is perfect for:
- Creating curriculum overview
- Quick reference sheets
- Unit-level documentation
- Course outlines
- Study guides

### Option 2 is perfect for:
- Distributing chapter-wise content
- Creating separate study materials
- Organizing topics by chapter
- Sharing specific chapters
- Structured learning paths

## 🆘 Troubleshooting

### Upload Issues:
**Problem**: File upload fails
- **Solution**: Ensure file is CSV format
- **Solution**: Check column names are exact
- **Solution**: Remove special characters from data

### Missing Columns:
**Problem**: "CSV must have these columns" error
- **Solution**: Rename columns to: Unit, Chapter, Topic
- **Solution**: Check for extra spaces in column names

### Empty Results:
**Problem**: No output generated
- **Solution**: Check for empty Unit/Chapter values
- **Solution**: Ensure data is properly formatted

## 📞 Support

For help:
- Check the "How to Use" section in the app
- Review this README
- Contact system administrator

## 🔄 Version History

### Version 1.0
- Initial release
- Unit-Chapter mapping functionality
- Topic segregation by chapter
- ZIP file generation
- Summary file option
- Dual download formats (CSV/Excel)

---

**Last Updated**: January 2026
**Version**: 1.0
