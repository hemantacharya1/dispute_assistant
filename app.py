# app.py

"""
Main entry point for the AI Dispute Assistant Streamlit application.

This script acts as the conductor, orchestrating the UI and the backend logic.
It uses a tabbed layout to separate data analysis from the conversational agent.
"""

import streamlit as st
import pandas as pd

# Import the modules from our package
from dispute_assistant import ui, core, agent

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Dispute Assistant",
    page_icon="🤖",
    layout="wide"
)

# --- Main Application ---
st.title("🤖 AI-Powered Dispute Assistant")

# --- Initialize Session State ---
# No changes here, just ensuring all our keys are initialized
if 'classified_df' not in st.session_state:
    st.session_state['classified_df'] = None
if 'resolutions_df' not in st.session_state:
    st.session_state['resolutions_df'] = None
if 'unified_df' not in st.session_state:
    st.session_state['unified_df'] = None
if 'agent_executor' not in st.session_state:
    st.session_state['agent_executor'] = None
if "messages" not in st.session_state:
    st.session_state.messages = []


# 1. Build the sidebar and get user inputs
disputes_file, txns_file, process_clicked = ui.build_sidebar()

# 2. Process data when the "Analyze" button is clicked
if process_clicked:
    with st.spinner("Analyzing disputes... This may take a moment."):
        try:
            classified_df, resolutions_df = core.process_files(disputes_file, txns_file)
            unified_df = pd.merge(classified_df, resolutions_df, on='dispute_id')
            
            st.session_state['classified_df'] = classified_df
            st.session_state['resolutions_df'] = resolutions_df
            st.session_state['unified_df'] = unified_df
            st.session_state['agent_executor'] = agent.get_agent_executor(unified_df)
            st.session_state.messages = [
                {"role": "assistant", "content": "Analysis complete! How can I help you with the dispute data?"}
            ]
            
        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            st.session_state['unified_df'] = None

# 3. Display results and chat interface IN TABS if data has been processed
if st.session_state['unified_df'] is not None:
    
    # Create the two tabs
    tab_analysis, tab_chatbot = st.tabs(["📊 Analysis & Results", "🤖 AI Chat Assistant"])

    # --- Analysis Tab ---
    with tab_analysis:
        ui.display_results(
            st.session_state['classified_df'],
            st.session_state['resolutions_df']
        )
    
    # --- Chatbot Tab ---
    with tab_chatbot:
        user_prompt = ui.build_chat_interface()
        
        if user_prompt:
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
    # This is the initial landing page before processing
    st.info("Welcome! Please upload your dispute and transaction files in the sidebar to begin analysis.")