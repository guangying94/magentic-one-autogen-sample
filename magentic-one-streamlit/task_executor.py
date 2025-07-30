"""
MagenticOne Task Executor
Handles the execution of MagenticOne tasks with real-time UI updates.
"""

import os
import time
import asyncio
from typing import Optional, AsyncGenerator, Any, Tuple
from autogen_ext.models.openai import OpenAIChatCompletionClient, AzureOpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from agent_interactions import AgentInteractionsHandler


class MagenticOneExecutor:
    """Handles MagenticOne task execution with real-time UI updates."""
    
    def __init__(self, interactions_handler: AgentInteractionsHandler):
        """
        Initialize the executor.
        
        Args:
            interactions_handler: Handler for managing agent interactions
        """
        self.interactions_handler = interactions_handler
    
    def _create_client(self, use_aoai: bool, model_name: str):
        """
        Create the appropriate OpenAI client.
        
        Args:
            use_aoai: Whether to use Azure OpenAI
            model_name: Model name to use
            
        Returns:
            OpenAI client instance
        """
        if use_aoai:
            return AzureOpenAIChatCompletionClient(
                azure_endpoint=os.getenv('AZURE_OPEN_AI_ENDPOINT'),
                model=model_name,
                api_version="2024-12-01-preview",
                api_key=os.getenv('AZURE_OPEN_AI_KEY')
            )
        else:
            return OpenAIChatCompletionClient(
                model=model_name,
                api_key=os.getenv('OPEN_AI_API_KEY')
            )
    
    async def run_task_stream(self, 
                             user_prompt: str, 
                             use_aoai: bool, 
                             model_name: str,
                             interactions_container: Optional[Any] = None) -> AsyncGenerator[Any, None]:
        """
        Execute a task and yield results with real-time UI updates.
        
        Args:
            user_prompt: The task prompt from the user
            use_aoai: Whether to use Azure OpenAI API
            model_name: Model name to use
            interactions_container: Streamlit container for real-time updates
            
        Yields:
            Various message chunks and task results
        """
        start_time = time.time()
        client = self._create_client(use_aoai, model_name)
        
        m1 = MagenticOne(client=client, code_executor=LocalCommandLineCodeExecutor())
        
        async for chunk in m1.run_stream(task=user_prompt):
            if chunk.__class__.__name__ != 'TaskResult':
                # Process agent interaction
                agent_name = self.interactions_handler.format_source_display(chunk.source)
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                interaction_type = 'text'
                
                # Handle multimodal messages (images)
                if hasattr(chunk, 'type') and chunk.type == 'MultiModalMessage':
                    content = 'data:image/png;base64,' + chunk.content[1].to_base64()
                    interaction_type = 'image'
                
                # Add interaction and update display
                self.interactions_handler.add_interaction(agent_name, content, interaction_type)
                self.interactions_handler.display_interactions(interactions_container)
                
            else:
                # Add completion message
                elapsed_time = time.time() - start_time
                self.interactions_handler.add_completion_message(elapsed_time)
                self.interactions_handler.display_interactions(interactions_container)
                
            yield chunk
        
        # Yield timing information
        yield None, time.time() - start_time
    
    async def execute_task_with_results(self,
                                      user_prompt: str,
                                      use_aoai: bool,
                                      model_name: str,
                                      interactions_container: Optional[Any] = None) -> Tuple[list, int, int]:
        """
        Execute a task and collect all results with token usage.
        
        Args:
            user_prompt: The task prompt from the user
            use_aoai: Whether to use Azure OpenAI API
            model_name: Model name to use
            interactions_container: Streamlit container for real-time updates
            
        Returns:
            Tuple of (results, prompt_tokens, completion_tokens)
        """
        results = []
        prompt_tokens = 0
        completion_tokens = 0
        
        # Collect all results from the stream
        async for chunk in self.run_task_stream(user_prompt, use_aoai, model_name, interactions_container):
            results.append(chunk)
        
        # Calculate token usage
        for result in results:
            if result is not None and result.__class__.__name__ == 'TaskResult':
                for message in result.messages:
                    if message.source != "user" and message.models_usage:
                        prompt_tokens += message.models_usage.prompt_tokens
                        completion_tokens += message.models_usage.completion_tokens
        
        # Update session state and add token summary
        self.interactions_handler.update_session_tokens(prompt_tokens, completion_tokens)
        
        # Add token usage summary if tokens were used
        if prompt_tokens > 0 or completion_tokens > 0:
            elapsed_time = results[-1][1] if results[-1] is not None else 0
            self.interactions_handler.add_token_summary(prompt_tokens, completion_tokens, elapsed_time)
            self.interactions_handler.display_interactions(interactions_container)
        
        return results, prompt_tokens, completion_tokens
