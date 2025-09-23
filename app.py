import streamlit as st
import pandas as pd
import io

# --- Core Logic (from your Main.py) ---
# I've moved the main function from Main.py directly into this script.
# It's modified to accept the file content directly and return a DataFrame
# instead of reading from and writing to disk.

def process_data(uploaded_file, metadata_cols, questions_per_block, total_blocks, case_type):
    """
    Processes the uploaded data in memory and returns a DataFrame.
    """
    # --- Load file based on its name's extension ---
    file_name = uploaded_file.name
    if file_name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    elif file_name.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(uploaded_file, engine='openpyxl')
    else:
        # Show an error in the Streamlit app if the file type is wrong
        st.error(f"Unsupported file type: {file_name}")
        return None

    question_cols = df.columns[len(metadata_cols):]
    output_rows = []

    for _, row in df.iterrows():
        # Extract metadata
        metadata = row[metadata_cols].to_dict()

        # Clean and safely convert question columns to int
        answers_raw = row[question_cols].astype('object').fillna(0)

        def clean_val(x):
            if isinstance(x, str):
                x = x.strip()
            try:
                return int(float(x)) # Use float conversion for safety
            except (ValueError, TypeError):
                return 0

        answers = answers_raw.apply(clean_val)

        # Split answers into blocks
        blocks = []
        for i in range(total_blocks):
            start = i * questions_per_block
            end = start + questions_per_block
            block_pattern = answers.iloc[start:end].tolist()
            blocks.append(block_pattern)

        # --- Case Selection ---
        # Note: Your UI.py provided "KDMC CASE" and "Normal Case". I've mapped them here.
        # Let's assume "KDMC CASE" corresponds to your original "Case 1".
        # You can adjust the string if needed.
        if case_type == "KDMC CASE" and len(blocks) > 17:
             block1_count = sum(1 for val in blocks[0] if val != 0)     # Block 1 (index 0)
             block18_count = sum(1 for val in blocks[17] if val != 0)   # Block 18 (index 17)
             max_rows = block1_count + block18_count
        else:  # "Normal Case"
            max_rows = max([sum(1 for val in block if val != 0) for block in blocks]) if blocks else 0

        # Generate output rows with sequence
        for i in range(max_rows):
            new_row = metadata.copy()
            for j, block_pattern in enumerate(blocks):
                # Using f-string for column names like Q1, Q2, etc.
                new_row[f'Q{j+1}'] = block_pattern[i] if i < len(block_pattern) else 0
            output_rows.append(new_row)

    if not output_rows:
        return pd.DataFrame() # Return empty dataframe if no rows were generated

    # Return the final result as a DataFrame
    return pd.DataFrame(output_rows)


# --- UI Components (from your UI.py) ---
# This section remains largely the same, but now it calls the function above.

st.set_page_config(page_title="OSCAN To STD FLN Data", layout="wide")
st.title("📊 OSCAN To STD FLN Data Converter")

# --- File upload ---
uploaded_file = st.file_uploader("Upload your file (CSV or XLSX)", type=["csv", "xlsx"])

# --- User inputs in sidebar ---
st.sidebar.header("⚙️ Processing Settings")

metadata_input = st.sidebar.text_area(
    "Enter columns before Question1 (comma-separated):",
    value="S.No,File,UDISECODE,TotalStudents,Class,Category"
)
# Clean up the user input for column names
metadata_cols = [c.strip() for c in metadata_input.split(",") if c.strip()]


questions_per_block = st.sidebar.number_input("Enter number of rows per question block:", min_value=1, value=40)
total_blocks = st.sidebar.number_input("Enter total number of questions:", min_value=1, value=31)

case_type = st.sidebar.selectbox(
    "Select Case Type:",
    ["Normal Case", "KDMC CASE"] # Swapped order to make "Normal Case" the default
)

# --- Run Processing ---
if uploaded_file is not None:
    if st.button("🚀 Process File", type="primary"):
        if not metadata_cols:
            st.warning("Please enter at least one metadata column name.")
        else:
            with st.spinner("Processing your file... Please wait."):
                # Call the processing function directly
                final_df = process_data(
                    uploaded_file,
                    metadata_cols,
                    questions_per_block,
                    total_blocks,
                    case_type
                )

                if final_df is not None:
                    st.success("✅ Processing complete!")
                    st.dataframe(final_df.head()) # Show a preview of the output

                    # Convert DataFrame to CSV in memory for download
                    csv_data = final_df.to_csv(index=False).encode('utf-8')

                    st.download_button(
                       label="📥 Download Output as CSV",
                       data=csv_data,
                       file_name=f"output_{uploaded_file.name}.csv",
                       mime="text/csv",
                    )
else:
    st.info("Please upload a file and click 'Process File' to begin.")



