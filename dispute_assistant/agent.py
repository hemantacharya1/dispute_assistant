# dispute_assistant/agent.py

"""
Agent module for the AI Dispute Assistant.

This module is responsible for creating and configuring the LangChain agent
that allows for a conversational experience with the processed dispute data.
"""

import streamlit as st
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType


def get_agent_executor(df: pd.DataFrame):
    """
    Creates and configures a LangChain agent executor for a given DataFrame.

    This agent is designed to have a conversational chat with the data,
    powered by Google's Gemini model.

    Args:
        df (pd.DataFrame): The unified DataFrame containing all dispute information.

    Returns:
        An agent executor object ready to be invoked.
    """
    # Ensure the API key is available
    if 'GOOGLE_API_KEY' not in st.secrets:
        st.error("Google API key not found. Please add it to your Streamlit secrets.")
        st.stop()
        
    google_api_key = st.secrets["GOOGLE_API_KEY"]

    # Initialize the Gemini LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=google_api_key,
        temperature=0, # Set to 0 for deterministic, code-focused output
        convert_system_message_to_human=True # Important for Gemini
    )

    # Create the pandas DataFrame agent
    # We are using the modern AgentType.ZERO_SHOT_REACT_DESCRIPTION which is robust.
    # verbose=True helps in debugging by showing the agent's thought process.
    agent_executor = create_pandas_dataframe_agent(
        llm=llm,
        df=df,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True, # Gracefully handles LLM output errors
        allow_dangerous_code=True # Required for pandas agent execution
    )

    return agent_executor