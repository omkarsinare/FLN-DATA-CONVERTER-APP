import streamlit as st
import pandas as pd
import io
import base64

# try requests first (more robust), fallback to urllib
try:
    import requests
except Exception:
    requests = None
import urllib.request

# --- Helper: fetch PDF bytes from a URL and embed as base64 iframe ---
def embed_pdf_from_url(url, height=800):
    """
    Fetches PDF bytes from `url` and embeds it in the Streamlit page using a
    base64 data URI so the PDF is shown inline (not downloaded).
    """
    pdf_bytes = None
    # Try requests if available
    if requests:
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            pdf_bytes = r.content
        except Exception:
            pdf_bytes = None

    # Fallback to urllib
    if pdf_bytes is None:
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                pdf_bytes = resp.read()
        except Exception as e:
            st.error(f"Could not load PDF from URL. Error: {e}")
            return

    if not pdf_bytes:
        st.error("PDF could not be loaded (empty content).")
        return

    b64 = base64.b64encode(pdf_bytes).decode('utf-8')
    iframe = f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>'
    st.markdown(iframe, unsafe_allow_html=True)


# --- Your processing function (kept as provided) ---
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

        # case selection
        if case_type == "KDMC CASE" and len(blocks) > 17:
            block1_count = sum(1 for val in blocks[0] if val != 0)
            block18_count = sum(1 for val in blocks[17] if val != 0)
            max_rows = block1_count + block18_count
        else:
            max_rows = max([sum(1 for val in block if val != 0) for block in blocks]) if blocks else 0

        # generate output rows
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

# Sidebar: put the toggle buttons near the bottom (simple divider approach)
st.sidebar.markdown("---")
if not st.session_state.show_manual:
    if st.sidebar.button("📖 User Manual"):
        st.session_state.show_manual = True
        st.rerun()
else:
    if st.sidebar.button("⬅️ Back to Tool"):
        st.session_state.show_manual = False
        st.rerun()

# Raw GitHub raw URL (use raw.githubusercontent.com form for best results)
manual_url = "https://raw.githubusercontent.com/omkarsinare/Converter-/main/User%20Manual.pdf"

# Show manual or main UI based on flag
if st.session_state.show_manual:
    # Replace entire main UI with the embedded PDF
    embed_pdf_from_url(manual_url, height=900)
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
