# dispute_assistant/agent.py

"""
Agent module for the AI Dispute Assistant.

This module is responsible for creating and configuring the LangChain agent
that allows for a conversational experience with the processed dispute data.
This version includes a custom prompt to give the agent a better persona
and allow it to handle conversational greetings gracefully.
"""

import streamlit as st
import pandas as pd
from textwrap import dedent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType
from datetime import datetime
# --- Custom Prompt Engineering ---
# This is the new set of instructions for our agent.
TODAY = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

AGENT_PREFIX = dedent(f"""
    You are a friendly and highly skilled AI data assistant working with a pandas DataFrame.
    Your name is "DisputeBot".

    Here are your instructions:
    1.  You are working with a DataFrame named `df`.
    2.  When the user asks a question about the data, you MUST use the `python_repl_ast` tool to find the answer.
    3.  Your thought process should be clear and methodical. First, think about what you need to do. Then, write and execute the code.
    4.  **IMPORTANT**: If the user's input is a greeting, a simple question (like "who are you?"), or conversational, you should NOT use the `python_repl_ast` tool. Instead, you should respond directly with a friendly, conversational answer in the "Final Answer" format.
    5.  Your responses should be helpful, polite, and easy to understand.
    6.  When providing a final answer based on data, synthesize the result into a clear, full sentence. For example, instead of just "3", say "There are 3 disputes with the category FRAUD."
    7.  Do not just return a dataframe. If the user asks to "list" something, format the output as a clean list or summary.
    8.  For Date related queries, Today's date is {TODAY}
    9.  If you are unsure about the user's request or if it is ambiguous, ask for clarification instead of making assumptions.
""").strip()


def get_agent_executor(df: pd.DataFrame):
    """
    Creates and configures a LangChain agent executor for a given DataFrame.

    This agent is designed to have a conversational chat with the data,
    powered by Google's Gemini model and a custom prompt.

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
    # Note: Upgraded to gemini-2.5-flash which is faster and often better for this kind of task.
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=google_api_key,
        temperature=0, # Keep it deterministic for data tasks
        convert_system_message_to_human=True,
    )

    # Create the pandas DataFrame agent with our custom prefix
    agent_executor = create_pandas_dataframe_agent(
        llm=llm,
        df=df,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        prefix=AGENT_PREFIX,
        verbose=True,
        handle_parsing_errors=False,
        allow_dangerous_code=True
    )

    return agent_executor