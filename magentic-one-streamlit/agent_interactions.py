"""
Agent Interactions Handler
Manages agent interaction display and storage for Streamlit UI.
"""

import streamlit as st
import graphviz
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
        if 'agent_flow' not in st.session_state:
            st.session_state.agent_flow = []
        if 'task_completed' not in st.session_state:
            st.session_state.task_completed = False
    
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
        
        # Track agent flow for graph visualization
        self._update_agent_flow(agent)
    
    def add_completion_message(self, elapsed_time: float) -> None:
        """Add a task completion message."""
        # Mark task as completed
        st.session_state.task_completed = True
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
        Display all agent interactions in a two-column layout.
        
        Args:
            container: Streamlit container for display (optional)
        """
        if container and st.session_state.agent_interactions:
            with container.container():
                # Create two-column layout
                col1, col2 = st.columns([2, 1])  # Left column wider for interactions
                
                with col1:
                    st.subheader("🤖 Agent Interactions")
                    for interaction in st.session_state.agent_interactions:
                        with st.expander(f"**{interaction['agent']}** - *{interaction['timestamp']}*", expanded=False):
                            if interaction['type'] == 'image':
                                st.image(interaction['content'])
                            else:
                                st.markdown(interaction['content'])
                
                with col2:
                    self._display_agent_flow_graph()
    
    def get_interactions(self) -> List[Dict[str, Any]]:
        """Get all current interactions."""
        return st.session_state.agent_interactions.copy()
    
    def clear_interactions(self) -> None:
        """Clear all current interactions."""
        st.session_state.agent_interactions.clear()
        if 'agent_flow' in st.session_state:
            st.session_state.agent_flow.clear()
        if 'task_completed' in st.session_state:
            st.session_state.task_completed = False
    
    def _update_agent_flow(self, agent: str) -> None:
        """Update the agent flow for graph visualization."""
        clean_agent = self._clean_agent_name(agent)
        
        # Skip system nodes for the graph
        if clean_agent in ['System', 'System Analytics']:
            return
        
        # Add to flow if not already present or if it's a new occurrence after a different agent
        if not st.session_state.agent_flow or st.session_state.agent_flow[-1] != clean_agent:
            st.session_state.agent_flow.append(clean_agent)
    
    def _clean_agent_name(self, agent: str) -> str:
        """Clean up agent name for graph display."""
        # Remove emojis and extra formatting
        clean_name = agent.replace('🤖 ', '').replace('🌐 ', '').replace('📁 ', '').replace('💻 ', '').replace('👤 ', '').replace('✅ ', '').replace('📊 ', '')
        # Remove "Agent" suffix for cleaner display
        clean_name = clean_name.replace(' Agent', '').replace('Agent', '')
        return clean_name.strip()
    
    def _create_agent_flow_graph(self) -> graphviz.Digraph:
        """Create a Graphviz diagram showing agent interaction flow as a hierarchical tree."""
        dot = graphviz.Digraph(comment='Agent Flow')
        dot.attr(rankdir='TB', size='8,6')
        dot.attr('node', shape='ellipse', style='filled', fontname='Arial', fontsize='10')
        dot.attr('edge', color='#666666', arrowsize='0.8')
        
        # Define colors for different agent types
        agent_colors = {
            'User': '#e3f2fd',
            'Orchestrator': '#f3e5f5', 
            'Web': '#e8f5e8',
            'WebSurfer': '#e8f5e8',
            'File': '#fff3e0',
            'FileSurfer': '#fff3e0',
            'Coder': '#fce4ec'
        }
        
        # Get unique agents from flow (excluding system nodes)
        unique_agents = []
        for agent in st.session_state.agent_flow:
            if agent not in unique_agents and agent not in ['System', 'System Analytics']:
                unique_agents.append(agent)
        
        # Always ensure we have the core nodes
        if 'User' not in unique_agents:
            unique_agents.insert(0, 'User')
        if 'Orchestrator' not in unique_agents:
            if 'User' in unique_agents:
                unique_agents.insert(1, 'Orchestrator')
            else:
                unique_agents.insert(0, 'Orchestrator')
        
        # Add all nodes
        for agent in unique_agents:
            color = agent_colors.get(agent, '#f5f5f5')
            if agent == 'Orchestrator':
                # Make orchestrator more prominent
                dot.node(agent, agent, fillcolor=color, shape='box', style='filled,bold')
            else:
                dot.node(agent, agent, fillcolor=color)
        
        # Create hierarchical structure
        if len(unique_agents) > 1:
            # User initiates to Orchestrator
            if 'User' in unique_agents and 'Orchestrator' in unique_agents:
                dot.edge('User', 'Orchestrator', label='request')
            
            # Orchestrator fans out to other agents (excluding User)
            orchestrator_targets = [agent for agent in unique_agents if agent not in ['User', 'Orchestrator']]
            for target in orchestrator_targets:
                dot.edge('Orchestrator', target, dir='both', label='delegate')
            
            # Only show final response when task is completed
            if st.session_state.get('task_completed', False) and len(orchestrator_targets) > 0 and 'User' in unique_agents:
                dot.edge('Orchestrator', 'User', label='response', color='#4CAF50', style='bold')
        
        return dot
    
    def _display_agent_flow_graph(self) -> None:
        """Display the agent flow graph using Streamlit."""
        if len(st.session_state.agent_flow) > 0:
            st.subheader("🔄 Agent Flow")
            try:
                graph = self._create_agent_flow_graph()
                st.graphviz_chart(graph.source)
            except Exception as e:
                st.error(f"Error displaying graph: {e}")
                # Fallback to text display
                flow_text = " → ".join(st.session_state.agent_flow)
                st.markdown(f"**Flow:** {flow_text}")
        else:
            st.info("No agents active yet. Start a task to see the flow!")
    
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
