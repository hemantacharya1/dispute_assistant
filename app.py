# app.py

"""
Main entry point for the AI Dispute Assistant Streamlit application.

This script acts as the conductor, orchestrating the UI and the backend logic.
It uses functions from the `dispute_assistant` package to build the UI,
process data, and handle user interactions with a conversational agent.
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
            # Call the core processing function
            classified_df, resolutions_df = core.process_files(disputes_file, txns_file)
            
            # **Data Unification Step**
            unified_df = pd.merge(classified_df, resolutions_df, on='dispute_id')
            
            # Store results in session state
            st.session_state['classified_df'] = classified_df
            st.session_state['resolutions_df'] = resolutions_df
            st.session_state['unified_df'] = unified_df
            
            # **Initialize the Agent**
            st.session_state['agent_executor'] = agent.get_agent_executor(unified_df)
            
            # Reset chat history for the new data
            st.session_state.messages = [
                {"role": "assistant", "content": "Analysis complete! How can I help you with the dispute data?"}
            ]
            
        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            # Clear out old data on error
            st.session_state['unified_df'] = None

# 3. Display results and chat interface if data has been processed
if st.session_state['unified_df'] is not None:
    # Display the static results tables first
    ui.display_results(
        st.session_state['classified_df'],
        st.session_state['resolutions_df']
    )
    
    # Build the chat interface and get user input
    user_prompt = ui.build_chat_interface()
    
    # 4. Handle chat interaction
    if user_prompt:
        with st.spinner("AI Assistant is thinking..."):
            try:
                # Retrieve the persistent agent from session state
                agent_executor = st.session_state['agent_executor']
                
                # Invoke the agent to get a response
                response = agent_executor.invoke({"input": user_prompt})
                ai_response = response['output']

            except Exception as e:
                ai_response = f"Sorry, I encountered an error: {e}"

            # Add AI response to chat history and display it
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            # This is a bit of a trick to force a re-run to show the latest message
            st.rerun()

else:
    st.info("Welcome! Please upload your dispute and transaction files in the sidebar to begin analysis.")