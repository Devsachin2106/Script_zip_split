import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="CO Mapping Verifier", layout="wide", page_icon="✅")

st.title("🎓 CO Mapping Verifier")
st.markdown("Upload your CSV file to verify that each Unit's CO Mapping matches the correct CO number.")

# ─── Helper Functions ────────────────────────────────────────────────────────

def extract_unit_number(unit_str):
    """
    Dynamically extracts the sequence number from any unit/module label.
    Supports formats like:
      - Unit 1, Unit-1
      - Module-1, Module 1, Module-1 - Some Title
      - Chapter 3, Lecture 4
      - Any label where the FIRST number found is the unit number
    Returns int or None.
    """
    if not isinstance(unit_str, str) or unit_str.strip() == "":
        return None
    match = re.search(r'\b(\d+)\b', unit_str)
    return int(match.group(1)) if match else None

def extract_co_number(co_str):
    """
    Extracts the number from a CO label like CO1, CO2, co3, C.O.1, etc.
    Returns int or None.
    """
    if not isinstance(co_str, str) or co_str.strip() == "":
        return None
    match = re.search(r'\d+', co_str)
    return int(match.group()) if match else None

def load_and_parse(file):
    """
    Loads CSV and forward-fills the Course column (handles merged/blank cells).
    Returns a clean DataFrame.
    """
    df = pd.read_csv(file, dtype=str)
    df.columns = df.columns.str.strip()

    # Identify the course, unit, and CO columns flexibly
    col_map = {}
    for col in df.columns:
        lower = col.lower().strip()
        if "course" in lower:
            col_map["course"] = col
        elif "unit" in lower or "module" in lower:
            col_map["unit"] = col
        elif "co" in lower and ("map" in lower or "mapping" in lower or lower == "co"):
            col_map["co"] = col

    # Fallback: use positional columns if names not matched
    if len(col_map) < 3:
        cols = df.columns.tolist()
        if len(cols) >= 3:
            col_map = {"course": cols[0], "unit": cols[1], "co": cols[2]}
        else:
            return None, None, "CSV must have at least 3 columns: Course, Unit, CO Mapping."

    df_clean = df[[col_map["course"], col_map["unit"], col_map["co"]]].copy()
    df_clean.columns = ["Course", "Unit", "CO Mapping"]

    # Forward-fill course names (handles blank cells under a course)
    df_clean["Course"] = df_clean["Course"].replace("", pd.NA).ffill()

    # Drop fully empty rows
    df_clean = df_clean.dropna(subset=["Unit", "CO Mapping"], how="all")
    df_clean = df_clean[df_clean["Unit"].str.strip().fillna("") != ""]
    df_clean = df_clean.reset_index(drop=True)

    return df_clean, col_map, None

def verify_co_mapping(df):
    """
    For each row, checks if the extracted unit number matches the CO number.
    Returns the DataFrame with extra columns: Unit_Num, CO_Num, Status, Issue.
    """
    df = df.copy()
    df["Unit_Num"] = df["Unit"].apply(extract_unit_number)
    df["CO_Num"]   = df["CO Mapping"].apply(extract_co_number)

    statuses = []
    issues   = []

    for _, row in df.iterrows():
        u_num = row["Unit_Num"]
        c_num = row["CO_Num"]
        co_val = str(row["CO Mapping"]).strip()
        unit_val = str(row["Unit"]).strip()

        if u_num is None:
            statuses.append("⚠️ Warning")
            issues.append(f"Could not extract a number from unit label: '{unit_val}'")
        elif c_num is None:
            statuses.append("❌ Error")
            issues.append(f"CO Mapping '{co_val}' has no recognisable number.")
        elif u_num != c_num:
            statuses.append("❌ Mismatch")
            issues.append(f"Unit {u_num} should map to CO{u_num}, but found '{co_val}'.")
        else:
            statuses.append("✅ Correct")
            issues.append("")

    df["Status"] = statuses
    df["Issue"]  = issues
    return df

def color_status(val):
    if "✅" in str(val):
        return "background-color: #d4edda; color: #155724;"
    elif "❌" in str(val):
        return "background-color: #f8d7da; color: #721c24;"
    elif "⚠️" in str(val):
        return "background-color: #fff3cd; color: #856404;"
    return ""

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="CO Verification")
    return output.getvalue()

# ─── Upload ──────────────────────────────────────────────────────────────────

uploaded_file = st.file_uploader("📂 Upload CSV File", type=["csv"])

if uploaded_file:
    df_raw, col_map, err = load_and_parse(uploaded_file)

    if err:
        st.error(err)
        st.stop()

    st.success(f"✅ File loaded: **{uploaded_file.name}** — {len(df_raw)} unit rows found.")

    # ─── Course Filter ────────────────────────────────────────────────────────
    courses = ["All Courses"] + sorted(df_raw["Course"].dropna().unique().tolist())
    selected_course = st.selectbox("🔍 Filter by Course", courses)

    if selected_course != "All Courses":
        df_view = df_raw[df_raw["Course"] == selected_course].copy()
    else:
        df_view = df_raw.copy()

    # ─── Verify ───────────────────────────────────────────────────────────────
    df_result = verify_co_mapping(df_view)

    # ─── Summary Metrics ──────────────────────────────────────────────────────
    total    = len(df_result)
    correct  = (df_result["Status"] == "✅ Correct").sum()
    mismatch = df_result["Status"].str.contains("❌").sum()
    warnings = df_result["Status"].str.contains("⚠️").sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 Total Rows",   total)
    col2.metric("✅ Correct",      correct,  delta=None)
    col3.metric("❌ Mismatches",   mismatch, delta=f"-{mismatch}" if mismatch else None, delta_color="inverse")
    col4.metric("⚠️ Warnings",    warnings)

    st.markdown("---")

    # ─── Filter by Status ─────────────────────────────────────────────────────
    status_filter = st.multiselect(
        "Filter by Status",
        options=["✅ Correct", "❌ Mismatch", "❌ Error", "⚠️ Warning"],
        default=["✅ Correct", "❌ Mismatch", "❌ Error", "⚠️ Warning"]
    )

    df_display = df_result[df_result["Status"].isin(status_filter)] if status_filter else df_result

    display_cols = ["Course", "Unit", "CO Mapping", "Status", "Issue"]

    # ─── Hierarchical View ────────────────────────────────────────────────────
    for course_name, group in df_display.groupby("Course", sort=False):
        course_total    = len(group)
        course_correct  = (group["Status"] == "✅ Correct").sum()
        course_issues   = course_total - course_correct

        badge = f"✅ {course_correct}/{course_total}" if course_issues == 0 \
                else f"❌ {course_issues} issue{'s' if course_issues > 1 else ''} / {course_total}"

        with st.expander(f"📘 {course_name}  —  {badge}", expanded=(course_issues > 0)):
            rows_html = ""
            for _, row in group.iterrows():
                status = row["Status"]
                if "✅" in status:
                    bg, icon = "#d4edda", "✅"
                elif "❌" in status:
                    bg, icon = "#f8d7da", "❌"
                else:
                    bg, icon = "#fff3cd", "⚠️"

                issue_note = f"<br><small style='color:#555;'>{row['Issue']}</small>" if row["Issue"] else ""
                rows_html += f"""
                <tr style="background:{bg};">
                  <td style="padding:7px 12px;font-weight:600;">{icon}</td>
                  <td style="padding:7px 12px;">{row['Unit']}</td>
                  <td style="padding:7px 12px;font-family:monospace;">{row['CO Mapping']}</td>
                  <td style="padding:7px 12px;">{row['Status']}{issue_note}</td>
                </tr>"""

            st.markdown(f"""
            <table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
              <thead>
                <tr style="background:#343a40;color:white;">
                  <th style="padding:8px 12px;text-align:left;width:40px;"></th>
                  <th style="padding:8px 12px;text-align:left;">Unit / Module</th>
                  <th style="padding:8px 12px;text-align:left;">CO Mapping</th>
                  <th style="padding:8px 12px;text-align:left;">Status</th>
                </tr>
              </thead>
              <tbody>{rows_html}</tbody>
            </table>""", unsafe_allow_html=True)

    total_issues = df_display[df_display["Issue"] != ""]
    if total_issues.empty:
        st.success("🎉 All CO Mappings are correct! No issues found.")

    # ─── Download ─────────────────────────────────────────────────────────────
    st.markdown("---")
    dl_col1, dl_col2 = st.columns(2)

    with dl_col1:
        df_csv = df_result[display_cols].copy()
        df_csv["Status"] = df_csv["Status"].str.replace("✅ ", "").str.replace("❌ ", "").str.replace("⚠️ ", "")
        csv_data = df_csv.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ Download Report (CSV)",
            data=csv_data,
            file_name="co_mapping_verification.csv",
            mime="text/csv"
        )

    with dl_col2:
        excel_data = to_excel(df_result[display_cols])
        st.download_button(
            label="⬇️ Download Report (Excel)",
            data=excel_data,
            file_name="co_mapping_verification.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("👆 Upload a CSV file to get started.")
    with st.expander("📖 How does it work?"):
        st.markdown("""
        **The verifier checks:**
        - Extracts the sequence number from any unit label (e.g., `Unit 1`, `Module-2 - Title`, `Chapter 3`)
        - Extracts the number from the CO Mapping (e.g., `CO1`, `CO2`)
        - Flags a **mismatch** if the unit number ≠ CO number

        **Supported unit label formats:**
        | Unit Label | Expected CO |
        |---|---|
        | Unit 1 | CO1 |
        | Module-2 - Some Title | CO2 |
        | Chapter 3 | CO3 |
        | Lecture 4 | CO4 |

        **CSV Format Required:**
        ```
        Course, Unit, CO Mapping
        Course Name, Unit 1, CO1
        , Unit 2, CO2
        ```
        """)