# Student/Staff Onboarding System

A Streamlit application for onboarding students and staff with data validation and column mapping capabilities.

## Features

✅ **Column Mapping**: Map columns from client Excel/CSV file to your format template
✅ **Name Validation**: Converts names to uppercase, removes dots and special characters
✅ **Email Validation**: Ensures emails are in correct format with valid domains (@gmail.com, @yahoo.com, etc.)
✅ **Mobile Validation**: Validates mobile numbers are exactly 10 digits
✅ **Error Reporting**: Generates separate file with all validation errors
✅ **Download Options**: Export valid and error records as CSV or Excel

## Installation

1. Install Python 3.8 or higher
2. Install required packages:

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
streamlit run student_onboarding_app.py
```

The application will open in your default web browser at `http://localhost:8501`

## How to Use

### Step 1: Upload Files
- Upload your **Client File** (Excel or CSV) - the file received from the client
- Upload **Our Format Template** (Excel or CSV) - your organization's format

### Step 2: Map Columns
- The system will auto-suggest column mappings based on similar names
- Manually adjust mappings as needed
- Map client columns to your format columns using dropdowns

### Step 3: Process & Validate
- Click "Process Data" button
- View statistics: Total, Valid, and Error records
- Review valid records in the first tab
- Review error records with detailed error messages in the second tab
- Download both valid and error records as CSV or Excel

## Validation Rules

### Names
- Converted to UPPERCASE
- Dots (.) removed
- Special characters not allowed
- Only letters and spaces permitted

### Email
- Must follow standard email format: `user@domain.com`
- Must end with recognized domains:
  - @gmail.com
  - @yahoo.com
  - @outlook.com
  - @hotmail.com
  - @edu, @ac.in, @edu.in
- Invalid formats are reported in error file

### Mobile Numbers
- Must be exactly 10 digits
- Country codes (like +91) are automatically removed
- Non-numeric characters are not allowed
- Spaces and hyphens are removed automatically

## File Outputs

The system generates two types of files:

1. **Valid Records**: Contains all records that passed validation
2. **Error Records**: Contains records with validation errors and detailed error descriptions

Both files can be downloaded in CSV or Excel format.

## Troubleshooting

- If column mapping doesn't auto-suggest correctly, manually select the appropriate columns
- Check error file for specific validation issues
- Ensure client file has all required columns before processing

## Support

For issues or questions, please contact your system administrator.
