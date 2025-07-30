"""
Streamlit UI Components
Handles the main UI rendering and user interactions.
"""

import streamlit as st
import asyncio
import uuid
from typing import Optional
from store_result_util import storage_manager
from agent_interactions import AgentInteractionsHandler
from task_executor import MagenticOneExecutor
from dotenv import load_dotenv

load_dotenv()


class StreamlitUI:
    """Main UI handler for the Streamlit application."""
    
    def __init__(self):
        """Initialize the UI components."""
        self.interactions_handler = AgentInteractionsHandler()
        self.executor = MagenticOneExecutor(self.interactions_handler)
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables."""
        if 'output' not in st.session_state:
            st.session_state.output = None
        if 'elapsed' not in st.session_state:
            st.session_state.elapsed = None
    
    def render_sidebar(self) -> tuple:
        """
        Render the sidebar with settings.
        
        Returns:
            Tuple of (use_aoai, selected_model)
        """
        st.sidebar.title('Settings')
        use_aoai = st.sidebar.checkbox("Use Azure OpenAI", value=True)
        
        if use_aoai:
            aoai_model_options = ["gpt-4.1-mini","gpt-4.1", "gpt-4o", "gpt-4o-mini", "o3-mini"]
            selected_model = st.sidebar.selectbox("Select Model", aoai_model_options)
        else:
            selected_model = st.sidebar.text_input(
                "Enter OpenAI Model", 
                value="gpt-4o", 
                placeholder="e.g., gpt-4o, gpt-3.5-turbo"
            )
        
        return use_aoai, selected_model
    
    def render_header(self):
        """Render the main header and info messages."""
        st.title('🤖 Magentic-One Demo')
        
        if storage_manager.is_enabled():
            st.info("💾 Run result storage is enabled - results will be saved to Azure Cosmos DB")
    
    def render_task_execution(self, use_aoai: bool, selected_model: str) -> Optional[str]:
        """
        Render the task execution section.
        
        Args:
            use_aoai: Whether to use Azure OpenAI
            selected_model: Selected model name
            
        Returns:
            User prompt if task was executed, None otherwise
        """
        st.subheader("🚀 Task Execution")
        
        prompt = st.text_input('What is the task today?', value='')
        
        if st.button('Execute') and prompt:
            return self._execute_task(prompt, use_aoai, selected_model)
        
        return None
    
    def _execute_task(self, prompt: str, use_aoai: bool, selected_model: str) -> str:
        """
        Execute a task with the given parameters.
        
        Args:
            prompt: User task prompt
            use_aoai: Whether to use Azure OpenAI
            selected_model: Selected model name
            
        Returns:
            The executed prompt
        """
        # Generate a new run ID
        new_run_id = str(uuid.uuid4())
        st.write(f"**Task is submitted with {selected_model} model.**")
        
        if storage_manager.is_enabled():
            st.write(f"**Run ID:** `{new_run_id}`")
        
        # Create interactions container for real-time updates
        interactions_container = st.empty()
        
        # Execute the task
        results, prompt_tokens, completion_tokens = asyncio.run(
            self.executor.execute_task_with_results(
                prompt, use_aoai, selected_model, interactions_container
            )
        )
        
        # Store elapsed time
        st.session_state.elapsed = results[-1][1] if results[-1] is not None else None
        
        # Store results if enabled
        if storage_manager.is_enabled():
            st.write(f"🔄 **Storing results...** (Run ID: `{new_run_id}`)")
            self._store_results(new_run_id, prompt, results, selected_model, use_aoai, 
                              prompt_tokens, completion_tokens)
            self._display_shareable_url(new_run_id)
        else:
            st.info("💾 **Storage disabled** - Set STORE_RUN_RESULT=true to enable result storage")
        
        return prompt
    
    def _store_results(self, run_id: str, prompt: str, results: list, 
                      model_name: str, use_aoai: bool, prompt_tokens: int, 
                      completion_tokens: int):
        """Store results in Cosmos DB if enabled."""
        elapsed_time = results[-1][1] if results[-1] is not None else 0
        
        storage_manager.store_run_result(
            run_id=run_id,
            prompt=prompt,
            results=results[:-1],  # Exclude the timing tuple
            model_name=model_name,
            use_aoai=use_aoai,
            elapsed_time=elapsed_time,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )
    
    def _display_shareable_url(self, run_id: str):
        """Display the shareable URL for the executed task."""
        import os
        
        # Try to get the external URL from environment variables (Azure Container Apps)
        external_url = os.getenv('WEBSITE_HOSTNAME')  # Azure App Service/Container Apps
        if not external_url:
            external_url = os.getenv('HTTP_HOST')  # Alternative environment variable
        if not external_url:
            external_url = os.getenv('HOST')  # Another common variable
        
        if external_url:
            # Use HTTPS for Azure deployments
            full_url = f"https://{external_url}?run_id={run_id}"
        else:
            # Fallback to Streamlit's detected URL for local development
            current_url = st.get_option("browser.serverAddress") or "http://localhost"
            server_port = st.get_option("browser.serverPort") or 8501
            full_url = f"{current_url}:{server_port}?run_id={run_id}"
        
        st.success("🔗 **Shareable URL:**")
        st.code(full_url, language="text")
    
    def check_stored_result(self) -> bool:
        """
        Check if we should display a stored result instead of the main interface.
        
        Returns:
            True if a stored result was displayed, False otherwise
        """
        query_params = st.query_params
        run_id = query_params.get('run_id', None)
        
        if run_id and storage_manager.is_enabled():
            stored_result = storage_manager.load_run_result(run_id)
            if stored_result:
                self._display_stored_result(stored_result)
                return True
            else:
                st.error(f"Run with ID {run_id} not found")
                st.write("Continuing to main interface...")
        
        return False
    
    def _display_stored_result(self, document: dict):
        """Display a stored run result from Cosmos DB."""
        st.title('🧠🤖 Magentic-One Demo - Stored Result')
        
        # Display metadata
        metadata_items = [
            ("Run ID", document['id']),
            ("Original Prompt", document['prompt']),
            ("Model", document['model_name']),
            ("Azure OpenAI", 'Yes' if document['use_azure_openai'] else 'No'),
            ("Created At", document['created_at']),
            ("Elapsed Time", f"{document['elapsed_time']:.2f} seconds"),
            ("Prompt Tokens", document['prompt_tokens']),
            ("Completion Tokens", document['completion_tokens'])
        ]
        
        for label, value in metadata_items:
            st.write(f"**{label}:** {value}")
        
        # Additional metadata
        if 'document_size_mb' in document:
            st.write(f"**Stored Size:** {document['document_size_mb']:.2f} MB")
        
        if 'total_images' in document and document['total_images'] > 0:
            st.write(f"**Images:** {document['total_images']} stored in blob storage")
        
        if document.get('is_metadata_only', False):
            st.warning("⚠️ This result was too large for storage. Only metadata is available.")
        
        st.write("---")
        st.write("**Execution Results:**")
        
        # Display results
        for result in document['results']:
            self._display_result_item(result)
    
    def _display_result_item(self, result: dict):
        """Display a single result item."""
        # Handle different result types
        if result.get('type') == 'TruncationNote':
            st.warning(f"⚠️ {result['content']}")
            return
            
        if result.get('type') == 'MetadataOnly':
            st.info(f"ℹ️ {result['content']}")
            return
        
        if result['source']:
            agent_display = self.interactions_handler.format_source_display(result['source'])
            st.write(f"**{agent_display}**")
        
        # Handle image content
        if isinstance(result['content'], dict) and result['content'].get('type') == 'image':
            self._display_image_result(result['content'])
        elif result['content'] and isinstance(result['content'], str):
            self._display_text_result(result['content'])
    
    def _display_image_result(self, content: dict):
        """Display image result from blob storage."""
        blob_url = content.get('blob_url')
        if blob_url:
            try:
                with st.spinner("Loading image from secure storage..."):
                    image_bytes = storage_manager.download_image_from_blob(blob_url)
                
                if image_bytes:
                    st.image(image_bytes, caption=f"Image ({content.get('size_kb', 'Unknown')} KB)")
                else:
                    st.error("Failed to download image from blob storage")
                    st.write(f"Image URL: {blob_url}")
            except Exception as e:
                st.error(f"Failed to load image from blob storage: {e}")
                st.write(f"Image URL: {blob_url}")
        elif 'note' in content:
            st.info(f"🖼️ {content['note']}")
        else:
            st.info("🖼️ Image content not available")
    
    def _display_text_result(self, content: str):
        """Display text result content."""
        if "[Content truncated due to size limits]" in content:
            st.warning("⚠️ Content was truncated due to size limits")
        st.markdown(content)
