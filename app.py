# app.py

"""
Main entry point for the AI Dispute Assistant Streamlit application.

This version provides two data loading options: uploading custom files or
using a pre-packaged sample dataset for a quick demonstration.
"""

import streamlit as st
import pandas as pd

from dispute_assistant import ui, core, agent

# --- Page Configuration ---
st.set_page_config(page_title="AI Dispute Assistant", page_icon="🤖", layout="wide")

# --- Helper Function for Analysis ---
def run_analysis(disputes_data, transactions_data):
    """A helper function to run the core analysis and set the session state."""
    with st.spinner("Analyzing disputes... This may take a moment."):
        try:
            classified_df, resolutions_df = core.process_files(disputes_data, transactions_data)
            unified_df = pd.merge(classified_df, resolutions_df, on='dispute_id')
            
            st.session_state['classified_df'] = classified_df
            st.session_state['resolutions_df'] = resolutions_df
            st.session_state['unified_df'] = unified_df
            st.session_state['agent_executor'] = agent.get_agent_executor(unified_df)
            st.session_state.messages = [
                {"role": "assistant", "content": "Analysis complete! How can I help you with the dispute data?"}
            ]
            st.session_state.active_view = "Analysis"
            
        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            st.session_state['unified_df'] = None

# --- Main Application ---
st.title("🤖 AI-Powered Dispute Assistant")

# Initialize Session State (if not already done)
if 'unified_df' not in st.session_state:
    st.session_state['unified_df'] = None
if "active_view" not in st.session_state:
    st.session_state.active_view = "Analysis"

# 1. Build the sidebar and get user actions
disputes_file, txns_file, upload_clicked, sample_clicked = ui.build_sidebar()

# 2. Handle the "Load Sample Data" action
if sample_clicked:
    run_analysis('data/disputes.csv', 'data/transactions.csv')

# 3. Handle the "Analyze Uploaded Files" action
if upload_clicked:
    run_analysis(disputes_file, txns_file)

# 4. Display the main interface if data is loaded
if st.session_state['unified_df'] is not None:
    view_options = ["📊 Analysis & Results", "🤖 AI Chat Assistant"]
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        selected_view = st.radio(
            "Select a View",
            options=view_options,
            key='active_view_selector',
            horizontal=True,
            label_visibility="collapsed"
        )
    st.session_state.active_view = "Analysis" if selected_view == view_options[0] else "Chatbot"

    if st.session_state.active_view == "Analysis":
        ui.display_results(st.session_state['classified_df'], st.session_state['resolutions_df'])
    
    elif st.session_state.active_view == "Chatbot":
        user_prompt = ui.build_chat_interface()
        if user_prompt:
            st.session_state.active_view = "Chatbot"
            with st.spinner("AI Assistant is thinking..."):
                try:
                    agent_executor = st.session_state['agent_executor']
                    response = agent_executor.invoke({"input": user_prompt})
                    ai_response = response['output']
                except Exception as e:
                    ai_response = f"Sorry, I encountered an error: {e}"
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                st.rerun()
else:
    st.info("Welcome! Please use an option in the sidebar to begin analysis.")