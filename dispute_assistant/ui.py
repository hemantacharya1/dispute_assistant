# dispute_assistant/ui.py

"""
UI component module for the Streamlit application.

This module contains functions that create and manage the user interface elements,
such as the sidebar, results display, and chat interface. This separation helps
keep the main app.py file clean and focused on orchestration.
"""

import streamlit as st
import pandas as pd


def build_sidebar():
    """
    Creates the sidebar UI for both uploading custom files and loading sample data.

    Returns:
        A tuple containing:
        - disputes_file (UploadedFile or None)
        - transactions_file (UploadedFile or None)
        - process_upload_clicked (bool)
        - process_sample_clicked (bool)
    """
    st.sidebar.header("Data Input Options")
    
    # --- Option 1: Upload Custom Files ---
    st.sidebar.subheader("1. Upload Your Own Data")
    disputes_file = st.sidebar.file_uploader("Upload Disputes CSV", type=["csv"])
    transactions_file = st.sidebar.file_uploader("Upload Transactions CSV", type=["csv"])

    process_upload_clicked = st.sidebar.button(
        "Analyze Uploaded Files", # MODIFIED: More specific label
        type="primary",
        use_container_width=True,
        disabled=(not disputes_file or not transactions_file)
    )

    st.sidebar.markdown("---")

    # --- Option 2: Use Sample Data ---
    st.sidebar.subheader("2. Use Sample Data")
    st.sidebar.markdown("Click below to analyze the sample `disputes.csv` and `transactions.csv` included with the app.")
    
    process_sample_clicked = st.sidebar.button(
        "Load Sample Data", # NEW: The new button
        use_container_width=True
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("This application is a demo for an AI-powered dispute resolution assistant.")

    return disputes_file, transactions_file, process_upload_clicked, process_sample_clicked


def display_results(classified_df, resolutions_df):
    """
    Displays the processed results on the main page of the Streamlit app.

    Args:
        classified_df (pd.DataFrame): The DataFrame with classified disputes.
        resolutions_df (pd.DataFrame): The DataFrame with suggested resolutions.
    """
    st.header("Analysis Results")
    st.success("Processing complete. The tables below show the classification and resolution suggestions.")

    # --- Display Classified Disputes with Editable Status (Bonus) ---
    st.subheader("Dispute Classifications")
    st.markdown("You can edit the `status` of a dispute directly in the table below.")

    # Use st.data_editor to make the status column editable
    edited_df = st.data_editor(
        classified_df,
        column_config={
            "status": st.column_config.SelectboxColumn(
                "Status",
                help="The current status of the dispute",
                options=["New", "In Review", "Resolved", "Closed"],
                required=True,
            )
        },
        disabled=["dispute_id", "predicted_category", "confidence", "explanation"],
        hide_index=True,
        use_container_width=True
    )
    
    # Store the edited dataframe back into session state
    st.session_state['classified_df'] = edited_df

    st.download_button(
        label="Download Classified Disputes as CSV",
        data=edited_df.to_csv(index=False).encode('utf-8'),
        file_name='classified_disputes.csv',
        mime='text/csv',
    )
    
    st.markdown("---")

    # --- Display Resolution Suggestions ---
    st.subheader("Resolution Suggestions")
    st.dataframe(resolutions_df, hide_index=True, use_container_width=True)
    st.download_button(
        label="Download Resolutions as CSV",
        data=resolutions_df.to_csv(index=False).encode('utf-8'),
        file_name='resolutions.csv',
        mime='text/csv',
    )
    
    st.markdown("---")

    # --- Display Dispute Trends Visualization (Bonus) ---
    st.subheader("Dispute Trends")
    category_counts = edited_df['predicted_category'].value_counts()
    st.bar_chart(category_counts)


def build_chat_interface():
    """
    Creates the chat UI for interacting with the AI agent.

    Manages chat history and user input.
    """
    st.subheader("🤖 Chat with the AI Assistant")
    st.markdown("""
    Ask questions about your processed data in natural language.
    The assistant is aware of the conversation history.
    """)

    # Initialize chat history in session state if it doesn't exist
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "How can I help you with the dispute data?"}
        ]

    # Display prior chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Get user input
    if prompt := st.chat_input("Ask a question about your data..."):
        # Add user message to history and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # The main app.py will handle getting the response and displaying it
        return prompt # Return the user's prompt to the main script
    
    return None