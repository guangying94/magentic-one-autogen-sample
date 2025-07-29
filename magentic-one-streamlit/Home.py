"""
Magentic-One Streamlit Demo
A streamlined interface for running MagenticOne tasks with real-time agent interactions.
"""

from dotenv import load_dotenv
from streamlit_ui import StreamlitUI

# Load environment variables
load_dotenv()


def main():
    """Main application entry point."""
    # Initialize the UI handler
    ui = StreamlitUI()
    
    # Check if we should display a stored result
    if ui.check_stored_result():
        return
    
    # Render the main interface
    ui.render_header()
    use_aoai, selected_model = ui.render_sidebar()
    
    # Handle task execution
    ui.render_task_execution(use_aoai, selected_model)
    
    # Display agent interactions
    #ui.render_interactions()


if __name__ == "__main__":
    main()