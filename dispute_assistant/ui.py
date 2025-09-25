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
    Creates the sidebar UI for file uploading and processing.

    Returns:
        tuple: A tuple containing (disputes_file, transactions_file, process_button_clicked).
               The files are file-like objects from Streamlit's uploader.
               The button status is a boolean.
    """
    st.sidebar.header("Data Input")
    st.sidebar.markdown("""
    Upload your raw `disputes.csv` and `transactions.csv` files below.
    The system will process them and provide classifications and resolution suggestions.
    """)

    disputes_file = st.sidebar.file_uploader("Upload Disputes CSV", type=["csv"])
    transactions_file = st.sidebar.file_uploader("Upload Transactions CSV", type=["csv"])

    process_button_clicked = st.sidebar.button(
        "Analyze Disputes",
        type="primary",
        use_container_width=True,
        disabled=(not disputes_file or not transactions_file)
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("This application is a demo for an AI-powered dispute resolution assistant.")

    return disputes_file, transactions_file, process_button_clicked


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