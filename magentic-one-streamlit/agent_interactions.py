"""
Agent Interactions Handler
Manages agent interaction display and storage for Streamlit UI.
"""

import streamlit as st
from datetime import datetime
from typing import List, Dict, Any, Optional


class AgentInteractionsHandler:
    """Handles agent interactions display and management."""
    
    def __init__(self):
        """Initialize the agent interactions handler."""
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables for agent interactions."""
        if 'agent_interactions' not in st.session_state:
            st.session_state.agent_interactions = []
        if 'prompt_token' not in st.session_state:
            st.session_state.prompt_token = 0
        if 'completion_token' not in st.session_state:
            st.session_state.completion_token = 0
        if 'elapsed' not in st.session_state:
            st.session_state.elapsed = None
    
    def add_interaction(self, agent: str, content: str, interaction_type: str = 'text') -> None:
        """
        Add a new agent interaction to the session state.
        
        Args:
            agent: The agent name/source
            content: The interaction content
            interaction_type: Type of interaction ('text' or 'image')
        """
        interaction = {
            'agent': agent,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'type': interaction_type,
            'content': content
        }
        st.session_state.agent_interactions.append(interaction)
    
    def add_completion_message(self, elapsed_time: float) -> None:
        """Add a task completion message."""
        self.add_interaction(
            agent='✅ System',
            content=f"Task completed in {elapsed_time:.2f} seconds"
        )
    
    def add_token_summary(self, prompt_tokens: int, completion_tokens: int, elapsed_time: float) -> None:
        """
        Add token usage summary to interactions.
        
        Args:
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
            elapsed_time: Task execution time in seconds
        """
        if prompt_tokens > 0 or completion_tokens > 0:
            token_summary = f"""**📊 Token Usage Summary:**
- **Prompt Tokens:** {prompt_tokens:,}
- **Completion Tokens:** {completion_tokens:,}
- **Total Tokens:** {(prompt_tokens + completion_tokens):,}
- **Elapsed Time:** {elapsed_time:.2f} seconds"""
            
            self.add_interaction(
                agent='📊 System Analytics',
                content=token_summary
            )
    
    def update_session_tokens(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Update session state with token counts."""
        st.session_state.prompt_token = prompt_tokens
        st.session_state.completion_token = completion_tokens
    
    def display_interactions(self, container: Optional[Any] = None) -> None:
        """
        Display all agent interactions.
        
        Args:
            container: Streamlit container for display (optional)
        """
        if container and st.session_state.agent_interactions:
            with container.container():
                for interaction in st.session_state.agent_interactions:
                    with st.expander(f"{interaction['agent']} - {interaction['timestamp']}", expanded=True):
                        if interaction['type'] == 'image':
                            st.image(interaction['content'])
                        else:
                            st.markdown(interaction['content'])
    
    def display_static_interactions(self) -> None:
        """Display interactions in the main UI (not in a container)."""
        if st.session_state.agent_interactions:
            st.subheader("🤖 Agent Interactions")
            for interaction in st.session_state.agent_interactions:
                with st.expander(f"{interaction['agent']} - {interaction['timestamp']}", expanded=True):
                    if interaction['type'] == 'image':
                        st.image(interaction['content'])
                    else:
                        st.markdown(interaction['content'])
    
    def get_interactions(self) -> List[Dict[str, Any]]:
        """Get all current interactions."""
        return st.session_state.agent_interactions.copy()
    
    def clear_interactions(self) -> None:
        """Clear all current interactions."""
        st.session_state.agent_interactions.clear()
    
    @staticmethod
    def format_source_display(source: str) -> str:
        """
        Convert a source identifier into a user-friendly display string with emoji.
        
        Args:
            source: The message source identifier
            
        Returns:
            Formatted string with emoji representing the source
        """
        source_mapping = {
            "user": "👤 User",
            "MagenticOneOrchestrator": "🤖 Orchestrator Agent",
            "WebSurfer": "🌐 Web Agent",
            "FileSurfer": "📁 File Agent",
            "Coder": "💻 Coder Agent"
        }
        return source_mapping.get(source, "💻 Terminal Agent")
