import streamlit as st
import pandas as pd

# --- Helper: embed PDF directly via URL ---
def embed_pdf_via_url(url, height=800):
    """
    Embeds a PDF from a direct URL into the Streamlit app using an iframe.
    """
    iframe = f'<iframe src="{url}" width="100%" height="{height}" style="border:none;"></iframe>'
    st.markdown(iframe, unsafe_allow_html=True)


# --- Your processing function (updated only Normal Case logic) ---
def process_data(uploaded_file, metadata_cols, questions_per_block, total_blocks, case_type):
    """
    Processes the uploaded data in memory and returns a DataFrame.
    """
    file_name = uploaded_file.name
    # Load
    try:
        if file_name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif file_name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.error(f"Unsupported file type: {file_name}")
            return None
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        return None

    # pick question columns based on metadata_cols length
    question_cols = df.columns[len(metadata_cols):]
    output_rows = []

    for _, row in df.iterrows():
        metadata = row[metadata_cols].to_dict()
        answers_raw = row[question_cols].astype('object').fillna(0)

        def clean_val(x):
            if isinstance(x, str):
                x = x.strip()
            try:
                return int(float(x))
            except (ValueError, TypeError):
                return 0

        answers = answers_raw.apply(clean_val)

        # split into blocks (total_blocks is treated as number of blocks)
        blocks = []
        for i in range(total_blocks):
            start = i * questions_per_block
            end = start + questions_per_block
            block_pattern = answers.iloc[start:end].tolist()
            blocks.append(block_pattern)

        # --- Updated Normal Case: Subblock-based repetition logic ---
        if case_type == "KDMC CASE" and len(blocks) > 17:
            # KDMC logic remains same
            block1_count = sum(1 for val in blocks[0] if val != 0)
            block18_count = sum(1 for val in blocks[17] if val != 0)
            max_rows = block1_count + block18_count
        else:
            # New logic for Normal Case (subblock-based)
            subblock_indices = []
            for block in blocks:
                last_nonzero_index = 0
                for q_index, val in enumerate(block, start=1):
                    if val != 0:
                        last_nonzero_index = q_index  # last non-zero subblock number
                subblock_indices.append(last_nonzero_index)
            max_rows = max(subblock_indices) if subblock_indices else 0
        # -------------------------------------------------------------

        # generate output rows (unchanged)
        for i in range(max_rows):
            new_row = metadata.copy()
            for j, block_pattern in enumerate(blocks):
                new_row[f'Q{j+1}'] = block_pattern[i] if i < len(block_pattern) else 0
            output_rows.append(new_row)

    if not output_rows:
        return pd.DataFrame()

    return pd.DataFrame(output_rows)


# --- Streamlit UI & toggle logic ---
st.set_page_config(page_title="OSCAN To STD FLN Data", layout="wide")

# Initialize session_state flag
if "show_manual" not in st.session_state:
    st.session_state.show_manual = False

# Sidebar toggle buttons
st.sidebar.markdown("---")
if not st.session_state.show_manual:
    if st.sidebar.button("📖 User Manual"):
        st.session_state.show_manual = True
        st.rerun()
else:
    if st.sidebar.button("⬅️ Back to Tool"):
        st.session_state.show_manual = False
        st.rerun()

# GitHub raw PDF URL
manual_url = "https://raw.githubusercontent.com/omkarsinare/Converter-/main/User%20Manual.pdf"

# Show manual or main UI based on flag
if st.session_state.show_manual:
    # Replace entire main UI with the embedded PDF
    embed_pdf_via_url(manual_url, height=900)
else:
    # ---- Main App UI (file upload + processing) ----
    st.title("📊 OSCAN To STD FLN Data Converter")

    uploaded_file = st.file_uploader("Upload your file (CSV or XLSX)", type=["csv", "xlsx"])

    st.sidebar.header("⚙️ Processing Settings")
    metadata_input = st.sidebar.text_area(
        "Enter columns before Question1 (comma-separated):",
        value="S.No,File,UDISECODE,TotalStudents,Class,Category"
    )
    metadata_cols = [c.strip() for c in metadata_input.split(",") if c.strip()]

    questions_per_block = st.sidebar.number_input("Enter number of rows per question block:", min_value=1, value=40)
    total_blocks = st.sidebar.number_input("Enter total number of questions (blocks):", min_value=1, value=31)

    case_type = st.sidebar.selectbox("Select Case Type:", ["Normal Case", "KDMC CASE"])

    if uploaded_file is not None:
        if st.button("🚀 Process File"):
            if not metadata_cols:
                st.warning("Please enter at least one metadata column name.")
            else:
                with st.spinner("Processing your file... Please wait."):
                    final_df = process_data(
                        uploaded_file,
                        metadata_cols,
                        questions_per_block,
                        total_blocks,
                        case_type
                    )

                    if final_df is not None:
                        st.success("✅ Processing complete!")
                        st.dataframe(final_df.head())

                        csv_data = final_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Output as CSV",
                            data=csv_data,
                            file_name=f"output_{uploaded_file.name}.csv",
                            mime="text/csv",
                        )
    else:
        st.info("Please upload a file and click 'Process File' to begin.")
