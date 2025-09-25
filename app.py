# app.py

"""
Main entry point for the AI Dispute Assistant Streamlit application.

This script acts as the conductor, orchestrating the UI and the backend logic.
It uses functions from the `dispute_assistant` package to build the UI,
process data, and handle user interactions.
"""

import streamlit as st

# Import the modules from our package
from dispute_assistant import ui
from dispute_assistant import core

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Dispute Assistant",
    page_icon="🤖",
    layout="wide"
)

# --- Main Application ---
st.title("🤖 AI-Powered Dispute Assistant")

# --- Initialize Session State ---
# This is crucial for keeping data "live" across user interactions.
if 'classified_df' not in st.session_state:
    st.session_state['classified_df'] = None
if 'resolutions_df' not in st.session_state:
    st.session_state['resolutions_df'] = None

# 1. Build the sidebar and get user inputs
disputes_file, txns_file, process_clicked = ui.build_sidebar()

# 2. Process data when the "Analyze" button is clicked
if process_clicked:
    with st.spinner("Analyzing disputes... This may take a moment."):
        try:
            # Call the core processing function
            classified_df, resolutions_df = core.process_files(disputes_file, txns_file)
            
            # Store results in session state to make them persistent
            st.session_state['classified_df'] = classified_df
            st.session_state['resolutions_df'] = resolutions_df
            
        except Exception as e:
            st.error(f"An error occurred during processing: {e}")

# 3. Display results if they exist in the session state
if st.session_state['classified_df'] is not None:
    ui.display_results(
        st.session_state['classified_df'],
        st.session_state['resolutions_df']
    )
else:
    st.info("Welcome! Please upload your dispute and transaction files in the sidebar to begin analysis.")