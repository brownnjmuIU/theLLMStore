import streamlit as st
from extractors.pdf_extractor import extract_text_from_pdf
from extractors.docs_extractor import extract_text_from_docx
from extractors.pptx_extractor import extract_text_from_pptx
from storage.json_store import save_artifact, list_raw_documents, get_output_root
from processing.pipeline import process_document



st.title("LLM Bundler")

with st.sidebar:
    st.header("Settings")
    st.write("Files are saved to:")
    st.code(str(get_output_root()))

# Create two tabs
tab1, tab2 = st.tabs(["📥 Ingest Document", "⚙️ Process & Chunk"])

# =============================================================================
# TAB 1: INGEST (Stage 3)
# =============================================================================
with tab1:
    st.write("Upload a PDF, Word, or PowerPoint document to extract text.")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "docx", "pptx"]
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        file_name = uploaded_file.name
        file_type = file_name.split(".")[-1].lower()

        st.write(f"**File:** {file_name}")
        st.write(f"**Type:** {file_type.upper()}")

        # Extract text based on file type
        with st.spinner("Extracting text..."):
            if file_type == "pdf":
                result = extract_text_from_pdf(file_bytes)
            elif file_type == "docx":
                result = extract_text_from_docx(file_bytes)
            elif file_type == "pptx":
                result = extract_text_from_pptx(file_bytes)
            else:
                st.error("Unsupported file type")
                st.stop()

        # Display results
        st.success(f"Extracted {len(result['text'])} characters")
        if result.get("page_count") is not None:
            st.write(f"**Pages:** {result['page_count']}")

        # Show preview
        with st.expander("Preview extracted text"):
            st.text(result["text"][:2000] + ("..." if len(result["text"]) > 2000 else ""))

        # Save button
        if st.button("Save as JSON artifact"):
            doc_id, output_path = save_artifact(
                filename=file_name,
                file_type=file_type,
                text=result["text"],
                page_count=result["page_count"]
            )
            st.success("Document saved successfully!")

            with st.expander("Advanced"):
                st.info(f"Document ID: `{doc_id}`")

            with open(output_path, "rb") as f:
                st.download_button(
                    label="Download Raw JSON",
                    data=f.read(),
                    file_name=f"doc_{doc_id}.json",
                    mime="application/json"
                )



# =============================================================================
# TAB 2: PROCESS & CHUNK (Stage 4)
# =============================================================================
with tab2:
    st.write("Select a stored document to clean and chunk.")

    # List available documents
    documents = list_raw_documents()

    if not documents:
        st.warning("No documents found. Upload a document in the 'Ingest' tab first.")
    else:
        # Create selection dropdown
        doc_options = {
            f"{doc['source_filename']} ({doc['doc_id']})": doc
            for doc in documents
        }

        selected_name = st.selectbox(
            "Select document to process",
            options=list(doc_options.keys())
        )

        selected_doc = doc_options[selected_name]

        # Show document info
        st.write(f"**Document ID:** `{selected_doc['doc_id']}`")
        st.write(f"**File type:** {selected_doc['file_type'].upper()}")
        st.write(f"**Text length:** {selected_doc['text_length']} characters")
        st.write(f"**Ingested:** {selected_doc['ingested_at']}")

        # Chunking settings
        st.subheader("Chunking Settings")
        col1, col2 = st.columns(2)
        with col1:
            chunk_size = st.number_input("Chunk size (chars)", min_value=100, max_value=2000, value=800)
        with col2:
            chunk_overlap = st.number_input("Chunk overlap (chars)", min_value=0, max_value=500, value=100)

        # Process button
        if st.button("Process & Chunk"):
            with st.spinner("Processing document..."):
                try:
                    result = process_document(
                        file_path=selected_doc["file_path"],
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )

                    st.success(f"Successfully created {result['total_chunks']} chunks!")

                    with open(result["output_path"], "rb") as f:
                        st.download_button(
                            label="Download Chunk JSON",
                            data=f.read(),
                            file_name=f"doc_{selected_doc['doc_id']}_chunks.json",
                            mime="application/json"
                        )


                    # Show chunk preview
                    with st.expander(f"Preview chunks ({result['total_chunks']} total)"):
                        for i, chunk in enumerate(result["chunks"][:5]):  # Show first 5
                            st.markdown(f"**Chunk {chunk['chunk_index']}** (`{chunk['chunk_id']}`)")
                            st.text(chunk["text"][:300] + ("..." if len(chunk["text"]) > 300 else ""))
                            st.divider()

                        if result["total_chunks"] > 5:
                            st.write(f"... and {result['total_chunks'] - 5} more chunks")

                except Exception as e:
                    st.error(f"Error processing document: {str(e)}")
