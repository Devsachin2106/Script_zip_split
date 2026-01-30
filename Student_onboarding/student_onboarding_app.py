# Student/Staff Onboarding System

import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Student/Staff Onboarding System", layout="wide")

# Initialize session state
if 'client_df' not in st.session_state:
    st.session_state.client_df = None
if 'our_format_df' not in st.session_state:
    st.session_state.our_format_df = None
if 'column_mapping' not in st.session_state:
    st.session_state.column_mapping = {}
if 'column_prefixes' not in st.session_state:
    st.session_state.column_prefixes = {}  # Store prefixes for register number columns

def auto_map_columns(our_columns, client_columns):
    """Automatically map columns based on name similarity"""
    mapping = {}
    used_client_cols = set()
    
    def normalize_name(name):
        """Normalize column name for comparison"""
        return re.sub(r'[_\s\-]', '', str(name).lower())
    
    def calculate_similarity(our_col, client_col):
        """Calculate similarity score between two column names"""
        our_norm = normalize_name(our_col)
        client_norm = normalize_name(client_col)
        our_lower = str(our_col).lower()
        client_lower = str(client_col).lower()
        
        # Exact match (case-insensitive)
        if our_lower == client_lower:
            return 100
        
        # Normalized exact match
        if our_norm == client_norm:
            return 95
        
        # One contains the other
        if our_norm in client_norm or client_norm in our_norm:
            return 80
        
        # Word-based matching
        our_words = set(re.findall(r'\w+', our_lower))
        client_words = set(re.findall(r'\w+', client_lower))
        if our_words and client_words:
            common_words = our_words.intersection(client_words)
            if common_words:
                # Calculate word overlap percentage
                overlap = len(common_words) / max(len(our_words), len(client_words))
                return int(overlap * 70)
        
        # Check for common variations
        common_patterns = {
            'name': ['name', 'fullname', 'full_name', 'full name'],
            'firstname': ['firstname', 'first_name', 'first name', 'fname', 'f_name'],
            'lastname': ['lastname', 'last_name', 'last name', 'lname', 'l_name', 'surname'],
            'email': ['email', 'e-mail', 'emailid', 'email_id', 'mail'],
            'mobile': ['mobile', 'phone', 'phonenumber', 'phone_number', 'contact', 'contactnumber'],
            'phone': ['phone', 'phonenumber', 'phone_number', 'mobile', 'contact'],
        }
        
        for key, variations in common_patterns.items():
            if key in our_lower:
                if any(var in client_lower for var in variations):
                    return 75
        
        return 0
    
    # First pass: find best matches
    for our_col in our_columns:
        best_match = None
        best_score = 0
        
        for client_col in client_columns:
            if client_col in used_client_cols:
                continue
            
            score = calculate_similarity(our_col, client_col)
            if score > best_score:
                best_score = score
                best_match = client_col
        
        # Only map if similarity is above threshold
        if best_score >= 50 and best_match:
            mapping[our_col] = best_match
            used_client_cols.add(best_match)
    
    return mapping

def validate_name(name):
    """Validate and format name - convert to uppercase, remove special characters"""
    if pd.isna(name) or str(name).strip() == '':
        return None, "Empty name - kept as empty", []
    
    original_name = str(name)
    corrections = []
    
    # Convert to string and uppercase (minor change - don't log)
    name_str = str(name).strip().upper()
    
    # Remove dots and extra spaces
    name_cleaned = name_str.replace('.', ' ').replace('  ', ' ')
    if '.' in name_str:
        corrections.append(f"Removed dots: '{original_name}' → '{name_cleaned}'")
    name_str = name_cleaned
    
    # Remove special characters but keep letters and spaces (major change - log)
    name_cleaned = re.sub(r'[^A-Z\s]', '', name_str)
    if name_cleaned != name_str:
        corrections.append(f"Removed special characters: '{original_name}' → '{name_cleaned}'")
    name_str = name_cleaned.strip()
    
    # Clean up multiple spaces (minor change - don't log)
    name_str = re.sub(r'\s+', ' ', name_str)
    
    if not name_str:
        return None, "Name became empty after cleaning", corrections
    
    return name_str, None, corrections

def validate_email(email):
    """Validate and auto-correct email format"""
    if pd.isna(email) or str(email).strip() == '':
        return None, "Empty email - kept as empty", []
    
    original_email = str(email)
    corrections = []
    
    email_str = str(email).strip().lower()
    # Convert to lowercase is minor - don't log
    
    # Remove spaces
    if ' ' in email_str:
        email_cleaned = email_str.replace(' ', '')
        corrections.append(f"Removed spaces: '{original_email}' → '{email_cleaned}'")
        email_str = email_cleaned
    
    # Basic email validation pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email_str):
        # Try to fix common issues
        # Check if @ is missing
        if '@' not in email_str:
            # Try to add @ before common domain patterns
            domain_patterns = ['gmail', 'yahoo', 'outlook', 'hotmail', 'edu', 'ac.in', 'edu.in']
            for domain in domain_patterns:
                if domain in email_str.lower():
                    # Try to insert @ before domain
                    idx = email_str.lower().find(domain)
                    if idx > 0:
                        email_fixed = email_str[:idx] + '@' + email_str[idx:]
                        corrections.append(f"Added missing @: '{original_email}' → '{email_fixed}'")
                        email_str = email_fixed
                        break
            else:
                return None, f"Missing @ symbol - cannot auto-correct: {original_email}", corrections
        
        # Check for multiple @
        if email_str.count('@') > 1:
            # Keep only the first @
            parts = email_str.split('@')
            email_fixed = parts[0] + '@' + ''.join(parts[1:])
            corrections.append(f"Removed extra @ symbols: '{original_email}' → '{email_fixed}'")
            email_str = email_fixed
        
        # Fix common domain typos
        domain_fixes = {
            'gmai.com': 'gmail.com',
            'gmial.com': 'gmail.com',
            'gmal.com': 'gmail.com',
            'yahooo.com': 'yahoo.com',
            'yaho.com': 'yahoo.com',
            'outlok.com': 'outlook.com',
            'hotmial.com': 'hotmail.com',
            'hotmai.com': 'hotmail.com',
        }
        
        for typo, correct in domain_fixes.items():
            if typo in email_str:
                email_fixed = email_str.replace(typo, correct)
                corrections.append(f"Fixed domain typo: '{original_email}' → '{email_fixed}'")
                email_str = email_fixed
                break
        
        # Fix missing dot before domain extension
        if '@' in email_str and '.' not in email_str.split('@')[1]:
            # Try to add .com if missing
            local, domain = email_str.split('@')
            if domain and not '.' in domain:
                email_fixed = f"{local}@{domain}.com"
                corrections.append(f"Added missing domain extension: '{original_email}' → '{email_fixed}'")
                email_str = email_fixed
        
        # Validate again after fixes
        if not re.match(email_pattern, email_str):
            return None, f"Invalid email format - cannot auto-correct: {original_email}", corrections
    
    # Check if email ends with valid domain
    valid_domains = ['@gmail.com', '@yahoo.com', '@outlook.com', '@hotmail.com', 
                     '@edu', '@ac.in', '@edu.in', '.com', '.in', '.org', '.net', '.edu']
    
    has_valid_domain = any(email_str.endswith(domain) or domain in email_str 
                           for domain in valid_domains)
    
    if not has_valid_domain:
        # It's a valid email format but uncommon domain - accept but warn (minor - don't log)
        pass
    
    return email_str, None, corrections

def validate_country_code(value):
    """Validate and standardize country code - replace any value with +91"""
    if pd.isna(value) or str(value).strip() == '':
        return "+91", "Empty country code - set to +91", []
    
    original = str(value).strip()
    corrections = []
    
    # Always replace with +91 regardless of input
    if original != "+91":
        corrections.append(f"Replaced with +91: '{original}' → '+91'")
    
    return "+91", None, corrections

def validate_text_field(value, field_name):
    """Validate and format text fields like Nationality, Religion with case-sensitive rules"""
    if pd.isna(value) or str(value).strip() == '':
        return None, f"Empty {field_name} - kept as empty", []
    
    original = str(value).strip()
    corrections = []
    
    # Remove extra spaces and normalize spacing
    cleaned = re.sub(r'\s+', ' ', original)
    if cleaned != original:
        corrections.append(f"Normalized spacing: '{original}' → '{cleaned}'")
    
    # Apply case-sensitive formatting based on field type
    if field_name.lower() == 'nationality':
        # Nationality: Title Case (e.g., "Indian", "American")
        formatted = cleaned.title()
    elif field_name.lower() == 'religion':
        # Religion: Title Case (e.g., "Hindu", "Christian", "Muslim")
        formatted = cleaned.title()
    else:
        # Default: Title Case for other text fields
        formatted = cleaned.title()
    
    if formatted != cleaned:
        corrections.append(f"Formatted case: '{cleaned}' → '{formatted}'")
    
    # Remove any special characters except letters, spaces, and common punctuation
    final_cleaned = re.sub(r'[^A-Za-z\s\-\'\.]', '', formatted)
    if final_cleaned != formatted:
        corrections.append(f"Removed special characters: '{formatted}' → '{final_cleaned}'")
    
    if not final_cleaned.strip():
        return None, f"{field_name} became empty after cleaning: {original}", corrections
    
    return final_cleaned.strip(), None, corrections

def validate_blood_group(value):
    """Standardize blood group to dropdown formats"""
    if pd.isna(value) or str(value).strip() == '':
        return None, "Empty blood group - kept as empty", []
    
    original = str(value).strip()
    corrections = []
    val = original.lower()
    
    # Standard formats from dropdown
    VALID_BLOOD_GROUPS = {
        "O+", "A+", "B+", "AB+", "Rh+", "O-", "A-", "B-", "AB-",
        "A1+", "A1B+", "A2+", "A2B+", "B1+", "A1-", "A1B-", "A2-", "A2B-", "B1-"
    }
    
    # Mapping of common variations
    BLOOD_GROUP_MAP = {
        # Positive
        "o+": "O+", "o positive": "O+", "o pos": "O+", "o+ve": "O+", "o +": "O+",
        "a+": "A+", "a positive": "A+", "a pos": "A+", "a+ve": "A+", "a +": "A+",
        "b+": "B+", "b positive": "B+", "b pos": "B+", "b+ve": "B+", "b +": "B+",
        "ab+": "AB+", "ab positive": "AB+", "ab pos": "AB+", "ab+ve": "AB+", "ab +": "AB+",
        "rh+": "Rh+", "rh positive": "Rh+", "rh pos": "Rh+", "rh+ve": "Rh+", "rh +": "Rh+",
        "a1+": "A1+", "a1 positive": "A1+", "a1 pos": "A1+", "a1+ve": "A1+", "a1 +": "A1+",
        "a1b+": "A1B+", "a1b positive": "A1B+", "a1b pos": "A1B+", "a1b+ve": "A1B+", "a1b +": "A1B+",
        "a2+": "A2+", "a2 positive": "A2+", "a2 pos": "A2+", "a2+ve": "A2+", "a2 +": "A2+",
        "a2b+": "A2B+", "a2b positive": "A2B+", "a2b pos": "A2B+", "a2b+ve": "A2B+", "a2b +": "A2B+",
        "b1+": "B1+", "b1 positive": "B1+", "b1 pos": "B1+", "b1+ve": "B1+", "b1 +": "B1+",
        # Negative
        "o-": "O-", "o negative": "O-", "o neg": "O-", "o-ve": "O-", "o -": "O-",
        "a-": "A-", "a negative": "A-", "a neg": "A-", "a-ve": "A-", "a -": "A-",
        "b-": "B-", "b negative": "B-", "b neg": "B-", "b-ve": "B-", "b -": "B-",
        "ab-": "AB-", "ab negative": "AB-", "ab neg": "AB-", "ab-ve": "AB-", "ab -": "AB-",
        "a1-": "A1-", "a1 negative": "A1-", "a1 neg": "A1-", "a1-ve": "A1-", "a1 -": "A1-",
        "a1b-": "A1B-", "a1b negative": "A1B-", "a1b neg": "A1B-", "a1b-ve": "A1B-", "a1b -": "A1B-",
        "a2-": "A2-", "a2 negative": "A2-", "a2 neg": "A2-", "a2-ve": "A2-", "a2 -": "A2-",
        "a2b-": "A2B-", "a2b negative": "A2B-", "a2b neg": "A2B-", "a2b-ve": "A2B-", "a2b -": "A2B-",
        "b1-": "B1-", "b1 negative": "B1-", "b1 neg": "B1-", "b1-ve": "B1-", "b1 -": "B1-",
    }
    
    # Direct mapping
    if val in BLOOD_GROUP_MAP:
        standardized = BLOOD_GROUP_MAP[val]
        if standardized != original:
            corrections.append(f"Standardized: '{original}' → '{standardized}'")
        return standardized, None, corrections
    
    # Try pattern matching
    if any(word in val for word in ['positive', 'pos', '+ve', '+']):
        base = re.sub(r'(positive|pos|ve)', '+', val)
        base = re.sub(r'[^aboa-z0-9+-]', '', base).upper()
        if base in VALID_BLOOD_GROUPS:
            corrections.append(f"Standardized: '{original}' → '{base}'")
            return base, None, corrections
    
    if any(word in val for word in ['negative', 'neg', '-ve', '-']):
        base = re.sub(r'(negative|neg|ve)', '-', val)
        base = re.sub(r'[^aboa-z0-9+-]', '', base).upper()
        if base in VALID_BLOOD_GROUPS:
            corrections.append(f"Standardized: '{original}' → '{base}'")
            return base, None, corrections
    
    # Fallback: return original if not matched
    return original, f"Could not standardize blood group: {original}", corrections

def validate_income(value):
    """Clean income to integer by removing non-numeric characters and handling Indian notation"""
    if pd.isna(value) or str(value).strip() == '':
        return None, "Empty income - kept as empty", []
    
    original = str(value).strip()
    corrections = []
    
    # Handle Indian notation (lakhs, k)
    val_lower = original.lower()
    cleaned = original
    
    # Handle 'lakhs' or 'lakh'
    if 'lakh' in val_lower:
        # Extract number before 'lakh'
        match = re.search(r'([\d.]+)\s*lakh', val_lower)
        if match:
            num = float(match.group(1))
            cleaned = str(int(num * 100000))
            corrections.append(f"Converted lakhs: '{original}' → '{cleaned}'")
    
    # Handle 'k' for thousands
    elif 'k' in val_lower:
        # Extract number before 'k'
        match = re.search(r'([\d.]+)\s*k', val_lower)
        if match:
            num = float(match.group(1))
            cleaned = str(int(num * 1000))
            corrections.append(f"Converted k: '{original}' → '{cleaned}'")
    
    # If no special notation, just remove non-numeric characters
    if cleaned == original:
        cleaned = re.sub(r'[^0-9-]', '', original)
        if cleaned != original:
            corrections.append(f"Cleaned: '{original}' → '{cleaned}'")
    
    if cleaned == '' or cleaned == '-':
        return None, f"Income became empty after cleaning: {original}", corrections
    
    try:
        income_int = int(cleaned)
        return income_int, None, corrections
    except ValueError:
        return None, f"Cannot convert to integer: {original}", corrections

def validate_mobile(mobile):
    """Validate and auto-correct mobile number - must be exactly 10 digits, replace any country code with +91"""
    if pd.isna(mobile):
        return None, "Empty mobile number - kept as empty", []
    
    original_mobile = str(mobile)
    corrections = []
    
    # Convert to string and remove any spaces or special characters except +
    mobile_str = str(mobile).strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    if mobile_str != original_mobile.strip():
        corrections.append(f"Removed formatting: '{original_mobile}' → '{mobile_str}'")
    
    # Remove any existing country code and replace with +91
    if len(mobile_str) > 10:
        # Extract first 10 digits as the actual number
        if len(mobile_str) >= 10:
            actual_number = mobile_str[:10]
            if mobile_str != actual_number:
                corrections.append(f"Replaced country code with +91: '{mobile_str}' → '{actual_number}'")
            mobile_str = actual_number
    
    # Check if it contains only digits
    if not mobile_str.isdigit():
        return None, f"Contains non-numeric characters - cannot auto-correct: {original_mobile}", corrections
    
    # If more than 10 digits, take the first 10 digits
    if len(mobile_str) > 10:
        mobile_cleaned = mobile_str[:10]
        corrections.append(f"Took first 10 digits: '{mobile_str}' → '{mobile_cleaned}'")
        mobile_str = mobile_cleaned
    
    # If less than 10 digits, cannot auto-correct
    if len(mobile_str) < 10:
        return None, f"Not 10 digits (length: {len(mobile_str)}) - cannot auto-correct: {original_mobile}", corrections
    
    # Check if starts with valid digit (6-9 for Indian mobile numbers)
    if not mobile_str[0] in ['6', '7', '8', '9']:
        corrections.append(f"Warning: Mobile number '{mobile_str}' doesn't start with 6-9")
    
    return mobile_str, None, corrections

def process_data(client_df, column_mapping, template_columns, column_prefixes=None):
    """Process the client data according to mapping and validation rules"""
    if column_prefixes is None:
        column_prefixes = {}
    
    # Create a new dataframe for our format with all template columns in order
    processed_data = []
    correction_log = []
    
    # First pass: collect all emails and contacts for cross-referencing
    email_candidates = {}
    contact_candidates = {}
    
    for idx, row in client_df.iterrows():
        row_emails = {}
        row_contacts = {}
        
        for our_col, client_col in column_mapping.items():
            if client_col and client_col != 'None':
                value = row[client_col]
                
                # Collect emails
                if 'email' in our_col.lower():
                    if pd.isna(value) or str(value).strip() == '':
                        # Empty email - still consider for cross-referencing
                        row_emails[our_col] = None
                    else:
                        validated_value, error, corrections = validate_email(value)
                        if not error or "cannot auto-correct" not in error:
                            row_emails[our_col] = validated_value
                
                # Collect contacts
                if 'phone' in our_col.lower() or 'mobile' in our_col.lower() or ('emergency' in our_col.lower() and 'contact' in our_col.lower()):
                    if pd.isna(value) or str(value).strip() == '':
                        # Empty contact - still consider for cross-referencing
                        row_contacts[our_col] = None
                    else:
                        validated_value, error, corrections = validate_mobile(value)
                        if not error or "cannot auto-correct" not in error:
                            row_contacts[our_col] = validated_value
        
        if row_emails:
            email_candidates[idx] = row_emails
        if row_contacts:
            contact_candidates[idx] = row_contacts
    
    # Second pass: process with cross-referencing
    for idx, row in client_df.iterrows():
        row_corrections = []
        processed_row = {}
        
        # Initialize all template columns (maintain order)
        for col in template_columns:
            processed_row[col] = None
        
        # Process each mapped column
        for our_col, client_col in column_mapping.items():
            if client_col and client_col != 'None':
                value = row[client_col]
                
                # Check if this column has a prefix (for register number columns)
                prefix = column_prefixes.get(our_col, "")
                
                # Apply validation based on column type
                if 'name' in our_col.lower() or 'firstname' in our_col.lower() or 'lastname' in our_col.lower():
                    validated_value, error, corrections = validate_name(value)
                    processed_row[our_col] = validated_value
                    # Don't log name corrections - only mobile, email, blood group, and income
                
                elif 'email' in our_col.lower():
                    if pd.isna(value) or str(value).strip() == '':
                        # Empty email - try cross-referencing
                        validated_value = None
                        error = "Empty email - trying fallback"
                        corrections = []
                        
                        # Try to find a valid email from other parent emails
                        fallback_email = None
                        fallback_source = None
                        
                        for other_email_col, email_val in email_candidates.get(idx, {}).items():
                            if other_email_col != our_col and email_val is not None:
                                fallback_email = email_val
                                fallback_source = other_email_col
                                break
                        
                        # If no parent email found, try student email
                        if not fallback_email:
                            for other_email_col, email_val in email_candidates.get(idx, {}).items():
                                if email_val is not None and ('student' in other_email_col.lower() or ('father' not in other_email_col.lower() and 'mother' not in other_email_col.lower())):
                                    fallback_email = email_val
                                    fallback_source = other_email_col
                                    break
                        
                        if fallback_email:
                            validated_value = fallback_email
                            error = None
                            corrections.append(f"Used {fallback_source} as fallback for empty email")
                    else:
                        validated_value, error, corrections = validate_email(value)
                        
                        # Cross-referencing logic for emails
                        if error and "cannot auto-correct" in error:
                            # Try to find a valid email from other parent emails
                            fallback_email = None
                            fallback_source = None
                            
                            # Check other email columns in the same row
                            for other_email_col, email_val in email_candidates.get(idx, {}).items():
                                if other_email_col != our_col and email_val is not None:
                                    fallback_email = email_val
                                    fallback_source = other_email_col
                                    break
                            
                            # If no parent email found, try student email
                            if not fallback_email:
                                for other_email_col, email_val in email_candidates.get(idx, {}).items():
                                    if email_val is not None and ('student' in other_email_col.lower() or ('father' not in other_email_col.lower() and 'mother' not in other_email_col.lower())):
                                        fallback_email = email_val
                                        fallback_source = other_email_col
                                        break
                            
                            if fallback_email:
                                validated_value = fallback_email
                                error = None
                                corrections.append(f"Used {fallback_source} as fallback: '{value}' → '{validated_value}'")
                    
                    processed_row[our_col] = validated_value
                    # Only log major corrections (format fixes, not just lowercase conversion)
                    if corrections:
                        row_corrections.extend([f"{our_col}: {corr}" for corr in corrections])
                    if error and "cannot auto-correct" in error:
                        row_corrections.append(f"{our_col}: ERROR - {error}")
                
                elif 'phone' in our_col.lower() or 'mobile' in our_col.lower() or ('emergency' in our_col.lower() and 'contact' in our_col.lower()):
                    if pd.isna(value) or str(value).strip() == '':
                        # Empty contact - try cross-referencing for any mobile/phone column
                        validated_value = None
                        error = "Empty contact - trying fallback"
                        corrections = []
                        
                        # For any mobile/phone column, try to find a valid contact from other contacts
                        fallback_contact = None
                        fallback_source = None
                        
                        for other_contact_col, contact_val in contact_candidates.get(idx, {}).items():
                            if other_contact_col != our_col and contact_val is not None:
                                # Prefer other parent contacts for parent columns
                                if 'emergency' not in our_col.lower():
                                    if 'emergency' not in other_contact_col.lower():
                                        fallback_contact = contact_val
                                        fallback_source = other_contact_col
                                        break
                                else:
                                    # For emergency contact, prefer parent contacts
                                    if 'emergency' not in other_contact_col.lower():
                                        fallback_contact = contact_val
                                        fallback_source = other_contact_col
                                        break
                        
                        if fallback_contact:
                            validated_value = fallback_contact
                            error = None
                            corrections.append(f"Used {fallback_source} as fallback for empty {our_col}")
                    else:
                        validated_value, error, corrections = validate_mobile(value)
                        
                        # Cross-referencing logic for any mobile/phone column
                        if error and "cannot auto-correct" in error:
                            # Try to find a valid contact from other contacts
                            fallback_contact = None
                            fallback_source = None
                            
                            for other_contact_col, contact_val in contact_candidates.get(idx, {}).items():
                                if other_contact_col != our_col and contact_val is not None:
                                    # Prefer other parent contacts for parent columns
                                    if 'emergency' not in our_col.lower():
                                        if 'emergency' not in other_contact_col.lower():
                                            fallback_contact = contact_val
                                            fallback_source = other_contact_col
                                            break
                                    else:
                                        # For emergency contact, prefer parent contacts
                                        if 'emergency' not in other_contact_col.lower():
                                            fallback_contact = contact_val
                                            fallback_source = other_contact_col
                                            break
                            
                            if fallback_contact:
                                validated_value = fallback_contact
                                error = None
                                corrections.append(f"Used {fallback_source} as fallback: '{value}' → '{validated_value}'")
                    
                    processed_row[our_col] = validated_value
                    if corrections:
                        row_corrections.extend([f"{our_col}: {corr}" for corr in corrections])
                    if error and "cannot auto-correct" in error:
                        row_corrections.append(f"{our_col}: ERROR - {error}")
                
                elif 'country' in our_col.lower() and 'code' in our_col.lower():
                    validated_value, error, corrections = validate_country_code(value)
                    processed_row[our_col] = validated_value
                    if corrections:
                        row_corrections.extend([f"{our_col}: {corr}" for corr in corrections])
                    if error and "cannot auto-correct" in error:
                        row_corrections.append(f"{our_col}: ERROR - {error}")
                
                elif 'nationality' in our_col.lower():
                    validated_value, error, corrections = validate_text_field(value, 'Nationality')
                    processed_row[our_col] = validated_value
                    if corrections:
                        row_corrections.extend([f"{our_col}: {corr}" for corr in corrections])
                    if error and "cannot auto-correct" in error:
                        row_corrections.append(f"{our_col}: ERROR - {error}")
                
                elif 'religion' in our_col.lower():
                    validated_value, error, corrections = validate_text_field(value, 'Religion')
                    processed_row[our_col] = validated_value
                    if corrections:
                        row_corrections.extend([f"{our_col}: {corr}" for corr in corrections])
                    if error and "cannot auto-correct" in error:
                        row_corrections.append(f"{our_col}: ERROR - {error}")
                
                elif 'blood' in our_col.lower() or 'group' in our_col.lower():
                    validated_value, error, corrections = validate_blood_group(value)
                    processed_row[our_col] = validated_value
                    if corrections:
                        row_corrections.extend([f"{our_col}: {corr}" for corr in corrections])
                    if error and "cannot auto-correct" in error:
                        row_corrections.append(f"{our_col}: ERROR - {error}")
                
                elif 'income' in our_col.lower() or 'salary' in our_col.lower() or 'earnings' in our_col.lower():
                    validated_value, error, corrections = validate_income(value)
                    processed_row[our_col] = validated_value
                    if corrections:
                        row_corrections.extend([f"{our_col}: {corr}" for corr in corrections])
                    if error and "cannot auto-correct" in error:
                        row_corrections.append(f"{our_col}: ERROR - {error}")
                
                else:
                    # For other columns, just copy the value
                    # If there's a prefix and value is not empty, append prefix
                    if prefix and pd.notna(value) and str(value).strip():
                        processed_row[our_col] = prefix + str(value).strip()
                    else:
                        processed_row[our_col] = value
        
        # Add row to processed data
        processed_data.append(processed_row)
        
        # Log corrections if any
        if row_corrections:
            # Determine status: check if any corrections contain "ERROR" or "cannot auto-correct"
            has_error = any("ERROR" in corr or "cannot auto-correct" in corr for corr in row_corrections)
            status = "❌ Error" if has_error else "✅ Success"
            
            log_entry = {
                'Row_Number': idx + 2,  # +2 because Excel starts at 1 and has header
                'Status': status,
                'Corrections_Made': ' | '.join(row_corrections),
                'Original_Data': row.to_dict()
            }
            correction_log.append(log_entry)
    
    # Create DataFrame with columns in template order
    processed_df = pd.DataFrame(processed_data, columns=template_columns)
    correction_df = pd.DataFrame(correction_log)
    
    return processed_df, correction_df

def main():
    st.title("💥 Student/Staff Onboarding System")
    st.markdown("---")
    
    # Step 1: File Upload
    st.header("Step 1: Upload Files")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Client File")
        client_file = st.file_uploader("Upload Client Excel/CSV File", 
                                       type=['xlsx', 'xls', 'csv'],
                                       key="client")
        if client_file:
            try:
                if client_file.name.endswith('.csv'):
                    st.session_state.client_df = pd.read_csv(client_file)
                else:
                    st.session_state.client_df = pd.read_excel(client_file)
                st.success(f"✅ Loaded {len(st.session_state.client_df)} rows")
                st.dataframe(st.session_state.client_df.head(3), use_container_width=True)
                # Clear mapping and prefixes when new client file is uploaded
                if 'column_mapping' in st.session_state:
                    st.session_state.column_mapping = {}
                if 'column_prefixes' in st.session_state:
                    st.session_state.column_prefixes = {}
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    with col2:
        st.subheader("Our Format Template")
        our_file = st.file_uploader("Upload Our Format Template (CSV/Excel)", 
                                    type=['xlsx', 'xls', 'csv'],
                                    key="our_format")
        if our_file:
            try:
                if our_file.name.endswith('.csv'):
                    st.session_state.our_format_df = pd.read_csv(our_file)
                else:
                    st.session_state.our_format_df = pd.read_excel(our_file)
                st.success(f"✅ Template loaded with {len(st.session_state.our_format_df.columns)} columns")
                st.dataframe(st.session_state.our_format_df.head(1), use_container_width=True)
                # Clear mapping and prefixes when new template file is uploaded
                if 'column_mapping' in st.session_state:
                    st.session_state.column_mapping = {}
                if 'column_prefixes' in st.session_state:
                    st.session_state.column_prefixes = {}
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
    st.markdown("---")
    
    # Step 2: Column Mapping
    if st.session_state.client_df is not None and st.session_state.our_format_df is not None:
        st.header("Step 2: Map Columns")
        
        client_columns = ['None'] + list(st.session_state.client_df.columns)
        our_columns = list(st.session_state.our_format_df.columns)
        
        # Auto-map columns if mapping is empty
        if not st.session_state.column_mapping:
            auto_mapping = auto_map_columns(our_columns, list(st.session_state.client_df.columns))
            st.session_state.column_mapping = auto_mapping
            if auto_mapping:
                st.success(f"✅ Automatically mapped {len(auto_mapping)} out of {len(our_columns)} columns!")
            else:
                st.info("⚠️ No automatic mappings found. Please map columns manually.")
        
        # Button to re-run auto-mapping
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("🔄 Re-auto Map", help="Re-run automatic column mapping"):
                with st.spinner("Re-mapping columns..."):
                    auto_mapping = auto_map_columns(our_columns, list(st.session_state.client_df.columns))
                    st.session_state.column_mapping = auto_mapping
                    st.success(f"✅ Re-mapped {len(auto_mapping)} columns!")
                    st.rerun()
        
        st.info("💡 Columns are automatically mapped. You can manually adjust any mapping below.")
        
        # Create mapping interface
        # Check if there are any register number columns
        has_register_col = any(any(keyword in col.lower() for keyword in ['register', 'reg', 'regno', 'reg_no', 'registration']) 
                               for col in our_columns)
        
        # Always use consistent column structure for alignment
        if has_register_col:
            # Header with 4 columns when register columns exist
            header_col1, header_col2, header_col3, header_col4 = st.columns([2, 1, 2, 1.5])
            with header_col1:
                st.markdown("**Our Format Columns**")
            with header_col2:
                st.markdown("**→**")
            with header_col3:
                st.markdown("**Client File Columns**")
            with header_col4:
                st.markdown("**Prefix (Register No.)**")
        else:
            # Standard 3 column header
            col1, col2, col3 = st.columns([2, 1, 2])
            with col1:
                st.markdown("**Our Format Columns**")
            with col3:
                st.markdown("**Client File Columns**")
        
        for our_col in our_columns:
            # Check if this is a register number column
            is_register_col = any(keyword in our_col.lower() for keyword in ['register', 'reg', 'regno', 'reg_no', 'registration'])
            
            # Use consistent column structure - always 4 columns if register columns exist
            if has_register_col:
                col1, col2, col3, col4 = st.columns([2, 1, 2, 1.5])
            else:
                col1, col2, col3 = st.columns([2, 1, 2])
                col4 = None
            
            with col1:
                st.text(our_col)
            
            with col2:
                st.markdown("→")
            
            with col3:
                # Find current mapping or auto-suggest
                default_index = 0
                current_mapping = st.session_state.column_mapping.get(our_col, None)
                
                if current_mapping and current_mapping in client_columns:
                    default_index = client_columns.index(current_mapping)
                else:
                    # Fallback to auto-suggest if no mapping exists
                    for i, client_col in enumerate(client_columns[1:], 1):
                        if (our_col.lower().replace(' ', '') in client_col.lower().replace(' ', '') or
                            client_col.lower().replace(' ', '') in our_col.lower().replace(' ', '')):
                            default_index = i
                            break
                
                selected = st.selectbox(
                    f"Map {our_col}",
                    client_columns,
                    index=default_index,
                    key=f"map_{our_col}",
                    label_visibility="collapsed"
                )
                
                if selected != 'None':
                    st.session_state.column_mapping[our_col] = selected
                elif our_col in st.session_state.column_mapping:
                    del st.session_state.column_mapping[our_col]
            
            # Add prefix input for register number columns in the 4th column
            if is_register_col and col4:
                with col4:
                    current_prefix = st.session_state.column_prefixes.get(our_col, "")
                    prefix = st.text_input(
                        "Prefix",
                        value=current_prefix,
                        key=f"prefix_{our_col}",
                        help="Enter prefix to append to register numbers (e.g., REG-)",
                        placeholder="e.g., REG-"
                    )
                    if prefix:
                        st.session_state.column_prefixes[our_col] = prefix
                    elif our_col in st.session_state.column_prefixes:
                        del st.session_state.column_prefixes[our_col]
            elif has_register_col and col4:
                # Empty space for non-register columns to maintain alignment
                with col4:
                    st.empty()
        
        st.markdown("---")
        
        # Step 3: Process Data
        if st.session_state.column_mapping:
            st.header("Step 3: Process & Validate Data")
            
            if st.button("💥 Boom ", type="primary", use_container_width=True):
                with st.spinner("Processing data..."):
                    template_columns = list(st.session_state.our_format_df.columns)
                    processed_df, correction_df = process_data(
                        st.session_state.client_df,
                        st.session_state.column_mapping,
                        template_columns,
                        st.session_state.column_prefixes
                    )
                    
                    st.session_state.processed_df = processed_df
                    st.session_state.correction_df = correction_df
            
            # Display results
            if 'processed_df' in st.session_state:
                st.success(f"✅ Successfully processed ALL {len(st.session_state.processed_df)} records!")
                
                if len(st.session_state.correction_df) > 0:
                    st.info(f"ℹ️ Auto-corrected issues in {len(st.session_state.correction_df)} records - see correction log below")
                else:
                    st.success("🎉 No corrections needed - all data was perfect!")
                
                # Show statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Records", len(st.session_state.client_df))
                with col2:
                    st.metric("Valid Records", len(st.session_state.processed_df))
                with col3:
                    st.metric("Auto-Corrections", len(st.session_state.correction_df))
                
                # Tabs for viewing data
                tab1, tab2 = st.tabs(["✅ Valid Records (All Data)", "📝 Correction Log"])
                
                with tab1:
                    st.info("All records processed successfully! Column order matches your template.")
                    st.dataframe(st.session_state.processed_df, use_container_width=True)
                    
                    # Download button for valid records
                    csv_valid = st.session_state.processed_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Complete Valid File (CSV)",
                        data=csv_valid,
                        file_name=f"valid_records_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    # Excel download
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        st.session_state.processed_df.to_excel(writer, index=False, sheet_name='Valid Records')
                    excel_valid = output.getvalue()
                    
                    st.download_button(
                        label="📥 Download Complete Valid File (Excel)",
                        data=excel_valid,
                        file_name=f"valid_records_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
                with tab2:
                    if len(st.session_state.correction_df) > 0:
                        st.markdown("### What Was Corrected?")
                        st.markdown("""
                        The following records had issues that were automatically fixed:
                        - **Emails**: Format fixes, typo corrections, space removal
                          - If parent email cannot be auto-corrected, uses the other parent's email
                          - If both parents' emails fail, uses student email as fallback
                          - Empty email cells also trigger fallback logic
                        - **Mobile Numbers**: Removed country codes, replaced with +91, formatting characters removed, digit adjustments
                          - Any country code (91, +1, etc.) is replaced with +91
                          - If parent mobile cannot be auto-corrected, uses the other parent's mobile
                          - Empty mobile cells also trigger fallback logic
                        - **Emergency Contact**: Same mobile number formatting rules applied
                          - If emergency contact cannot be auto-corrected, uses father/mother number as fallback
                          - Empty emergency contact cells also trigger fallback logic
                        - **Country Code**: Any value is replaced with +91
                        - **Blood Groups**: Standardized to dropdown formats (O+, A+, B+, AB+, etc.)
                        - **Income**: Converted lakhs/k to exact numbers (e.g., 2 lakhs → 200000, 80k → 80000)
                        - **Nationality/Religion**: Case-sensitive formatting (Title Case), spacing normalization
                        
                        **Color Coding:**
                        - 🟢 **Green**: Successfully auto-corrected
                        - 🔴 **Red**: Cannot be auto-corrected (requires manual review)
                        """)
                        
                        # Style the dataframe with color coding
                        def style_corrections(row):
                            """Apply color styling based on status - color entire row"""
                            if 'Status' in st.session_state.correction_df.columns:
                                status_idx = list(st.session_state.correction_df.columns).index('Status')
                                status_value = row.iloc[status_idx]
                                
                                if status_value == "❌ Error":
                                    # Red background for errors
                                    return ['background-color: #ffcccc; color: #cc0000;'] * len(row)
                                elif status_value == "✅ Success":
                                    # Green background for success
                                    return ['background-color: #ccffcc; color: #006600;'] * len(row)
                            return [''] * len(row)
                        
                        # Reorder columns to show Status first
                        if 'Status' in st.session_state.correction_df.columns:
                            cols = ['Row_Number', 'Status', 'Corrections_Made', 'Original_Data']
                            # Only include columns that exist
                            cols = [c for c in cols if c in st.session_state.correction_df.columns]
                            display_df = st.session_state.correction_df[cols].copy()
                            styled_df = display_df.style.apply(style_corrections, axis=1)
                            st.dataframe(styled_df, use_container_width=True)
                        else:
                            st.dataframe(st.session_state.correction_df, use_container_width=True)
                        
                        # Download button for correction log
                        csv_corrections = st.session_state.correction_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Correction Log (CSV)",
                            data=csv_corrections,
                            file_name=f"correction_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        # Excel download
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            st.session_state.correction_df.to_excel(writer, index=False, sheet_name='Corrections')
                        excel_corrections = output.getvalue()
                        
                        st.download_button(
                            label="📥 Download Correction Log (Excel)",
                            data=excel_corrections,
                            file_name=f"correction_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        st.success("No corrections were needed! All data was perfect.")
        else:
            st.info("Please map at least one column to proceed")
    
    else:
        st.info("👆 Please upload both files to begin")

if __name__ == "__main__":
    main()