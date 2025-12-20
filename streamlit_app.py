"""
Streamlit UI for DiveLog - AI-powered dive statistics assistant.

This module provides a modern web interface for querying dive statistics
using natural language through the StatisticsAgent.

Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import os
from pathlib import Path

from Utilities.StatisticsAgent import StatisticsAgent
from Utilities.APIKeyDetector import detect_api_keys


# Page configuration
st.set_page_config(
    page_title="DiveLog - AI Assistant",
    page_icon="🤿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .dive-stat-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .example-query {
        background-color: #e1e5eb;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
        cursor: pointer;
    }
    .example-query:hover {
        background-color: #d1d5db;
    }
</style>
""", unsafe_allow_html=True)


def get_provider_from_key_name(key_name: str) -> str:
    """Map API key name to provider code."""
    provider_map = {
        "OpenAI": "openai",
        "Gemini": "gemini",
        "Claude": "claude",
        "Anthropic": "claude",
    }
    # Check for partial matches
    for name, provider in provider_map.items():
        if name.lower() in key_name.lower():
            return provider
    return "gemini"  # Default


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "api_key" not in st.session_state:
        st.session_state.api_key = None
    if "provider" not in st.session_state:
        st.session_state.provider = None


def create_agent(api_key: str, provider: str) -> StatisticsAgent:
    """Create or return cached agent."""
    # Check if we need to create a new agent
    if (st.session_state.agent is None or
        st.session_state.api_key != api_key or
        st.session_state.provider != provider):

        with st.spinner("Initializing AI agent..."):
            try:
                agent = StatisticsAgent(
                    api_key=api_key,
                    dive_folder="Storage/Dives",
                    provider=provider
                )
                st.session_state.agent = agent
                st.session_state.api_key = api_key
                st.session_state.provider = provider
            except Exception as e:
                st.error(f"Failed to initialize agent: {str(e)}")
                return None

    return st.session_state.agent


def render_sidebar():
    """Render the sidebar with settings and info."""
    with st.sidebar:
        st.header("⚙️ Settings")

        # API Key detection
        api_keys = detect_api_keys()

        if not api_keys:
            st.error("No API keys found!")
            st.info(
                "Set one of these environment variables:\n"
                "- `OPENAI_API_KEY`\n"
                "- `GEMINI_API_KEY`\n"
                "- `ANTHROPIC_API_KEY`"
            )
            return None, None

        # Select API provider
        selected_api = st.selectbox(
            "Select LLM Provider",
            list(api_keys.keys()),
            help="Choose which AI model to use for queries"
        )

        api_key = api_keys[selected_api]
        provider = get_provider_from_key_name(selected_api)

        st.divider()

        # Show current provider info
        provider_info = {
            "gemini": ("🔵 Google Gemini", "gemini-1.5-flash"),
            "openai": ("🟢 OpenAI", "gpt-4o-mini"),
            "claude": ("🟣 Anthropic Claude", "claude-sonnet-4-20250514"),
        }
        info = provider_info.get(provider, ("Unknown", "Unknown"))
        st.caption(f"Using: {info[0]}")
        st.caption(f"Model: {info[1]}")

        st.divider()

        # Quick actions
        st.subheader("Quick Actions")

        if st.button("🔄 Reload Dives", use_container_width=True):
            if st.session_state.agent:
                st.session_state.agent.reload_dives()
                st.success("Dives reloaded!")

        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            if st.session_state.agent:
                st.session_state.agent.clear_history()
            st.rerun()

        st.divider()

        # Help section
        with st.expander("❓ Help"):
            st.markdown("""
            **How to use:**
            1. Make sure you have dive data in `Storage/Dives/`
            2. Ask questions in natural language
            3. The AI will analyze your dives and respond

            **Example questions:**
            - "What's my average depth?"
            - "How many dives did I do this year?"
            - "Show me my deepest dives"
            - "Who is my most common buddy?"
            """)

        return api_key, provider


def render_quick_stats(agent: StatisticsAgent):
    """Render quick statistics cards."""
    if not agent or not agent.dives:
        return

    with st.expander("📊 Quick Stats", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        total_dives = len(agent.dives)
        total_time = sum(d.basics.duration for d in agent.dives) / 60

        depths = [max(d.timeline.depths) for d in agent.dives if d.timeline.depths]
        avg_depth = sum(depths) / len(depths) if depths else 0
        max_depth = max(depths) if depths else 0

        with col1:
            st.metric("Total Dives", f"{total_dives}")

        with col2:
            st.metric("Total Time", f"{total_time/60:.1f} hours")

        with col3:
            st.metric("Avg Depth", f"{avg_depth:.1f}m")

        with col4:
            st.metric("Max Depth", f"{max_depth:.1f}m")


def render_example_queries():
    """Render clickable example queries."""
    examples = [
        "What's my average dive depth?",
        "How many dives did I do in 2024?",
        "Show me all dives deeper than 20 meters",
        "What's my total dive time?",
        "Who is my most common dive buddy?",
        "List my 5 deepest dives",
        "How much time have I spent below 15 meters?",
        "Show me dives at [location name]",
    ]

    with st.expander("💡 Example Questions", expanded=False):
        cols = st.columns(2)
        for i, example in enumerate(examples):
            col = cols[i % 2]
            with col:
                if st.button(example, key=f"example_{i}", use_container_width=True):
                    return example
    return None


def render_chat_interface(agent: StatisticsAgent):
    """Render the main chat interface."""
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your dives..."):
        process_query(agent, prompt)


def process_query(agent: StatisticsAgent, query: str):
    """Process a user query and display the response."""
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your dives..."):
            try:
                response = agent.process_query(query)
            except Exception as e:
                response = f"Error: {str(e)}"
        st.markdown(response)

    # Add assistant response to chat
    st.session_state.messages.append({"role": "assistant", "content": response})


def main():
    """Main application entry point."""
    # Initialize session state
    init_session_state()

    # Title
    st.title("🤿 DiveLog - AI Dive Statistics Assistant")

    # Render sidebar and get configuration
    result = render_sidebar()
    if result is None:
        st.warning("Please configure an API key to continue.")
        return

    api_key, provider = result

    # Create/get agent
    agent = create_agent(api_key, provider)

    if agent is None:
        st.error("Failed to initialize the agent. Please check your API key.")
        return

    # Show dive count
    if agent.dives:
        st.success(f"📊 Loaded {len(agent.dives)} dives from your log")
        render_quick_stats(agent)
    else:
        st.warning(
            "No dives found. Add some dives using the Tkinter app "
            "or import .fit files to `Storage/Dives/`"
        )

    # Example queries (can trigger input)
    example_query = render_example_queries()

    # Main chat interface
    st.subheader("💬 Ask about your dives")
    render_chat_interface(agent)

    # Process example query if clicked
    if example_query:
        process_query(agent, example_query)
        st.rerun()


if __name__ == "__main__":
    main()
