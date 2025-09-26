# app.py

"""
Main entry point for the AI Dispute Assistant Streamlit application.

This script acts as the conductor, orchestrating the UI and the backend logic.
It uses a stateful tab-like interface to separate data analysis from the 
conversational agent, providing a seamless user experience.
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
# All our session state keys are initialized here for clarity
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
# **NEW**: Add a key to track our active view (the "tab")
if "active_view" not in st.session_state:
    st.session_state.active_view = "Analysis"


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
            # After processing, default to the analysis view
            st.session_state.active_view = "Analysis" 
            
        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            st.session_state['unified_df'] = None

# 3. Display results and chat interface if data has been processed
if st.session_state['unified_df'] is not None:
    
    # **REPLACEMENT FOR TABS**: Use a radio button bar to control the view
    view_options = ["📊 Analysis & Results", "🤖 AI Chat Assistant"]
    # We use a trick with st.columns to center the radio buttons
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        selected_view = st.radio(
            "Select a View",
            options=view_options,
            # Link the radio button's state to our session state variable
            key='active_view_selector', 
            horizontal=True,
            label_visibility="collapsed"
        )
    
    # Update the active_view state based on the radio button selection
    st.session_state.active_view = "Analysis" if selected_view == view_options[0] else "Chatbot"

    # --- Conditionally display content based on the selected view ---
    if st.session_state.active_view == "Analysis":
        ui.display_results(
            st.session_state['classified_df'],
            st.session_state['resolutions_df']
        )
    
    elif st.session_state.active_view == "Chatbot":
        user_prompt = ui.build_chat_interface()
        
        if user_prompt:
            # When a user chats, we explicitly set the active view to stay on the chatbot
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
    # This is the initial landing page before processing
    st.info("Welcome! Please upload your dispute and transaction files in the sidebar to begin analysis.")