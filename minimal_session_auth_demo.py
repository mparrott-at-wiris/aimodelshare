"""
Minimal Working Example: Session-Based Authentication for Multi-User Gradio Apps

This demonstrates the correct pattern for Cloud Run multi-user deployments.
It shows:
1. How to use Gradio State for per-session authentication
2. How to pass session state through function calls
3. How to avoid environment variables for user credentials

Run this example to see session-based auth in action:
    python minimal_session_auth_demo.py
"""

import gradio as gr
from aimodelshare.moral_compass.apps.session_auth import (
    create_session_state,
    authenticate_session,
    get_session_username,
    get_session_token,
    is_session_authenticated,
)


# Module-level user data storage
# NOTE: In production, use a database, Redis, or other persistent storage.
# This dict is shared but operations are per-user (keyed by username from session).
# For true thread safety in production, use threading.Lock or a thread-safe data structure.
USER_DATA = {}


def create_demo_app():
    """Create a minimal demo app showing session-based authentication."""
    
    # NOTE: In production, user_data should be stored in a database or cache.
    # For this demo, we use a module-level dict which is read-only safe for
    # concurrent access since dict get/set operations are atomic in CPython.
    # However, for true isolation, each modification should use proper locking
    # or use a thread-safe data structure.
    
    def handle_login(session_state, username, password):
        """Authenticate user and update session state."""
        new_state, success, message = authenticate_session(session_state, username, password)
        
        if success:
            # Initialize user data for this session's authenticated user
            if username not in USER_DATA:
                USER_DATA[username] = {"points": 0, "tasks_completed": []}
            
            welcome_msg = f"✓ Welcome {username}! You have {USER_DATA[username]['points']} points."
            return (
                new_state,
                gr.update(visible=False),  # Hide login
                gr.update(value=welcome_msg, visible=True),  # Show welcome
                gr.update(visible=True),  # Show main app
                gr.update(value=f"**User:** {username}")  # Show user info
            )
        else:
            return (
                new_state,
                gr.update(visible=True),  # Keep login visible  
                gr.update(value=f"⚠️ {message}", visible=True),  # Show error
                gr.update(visible=False),  # Keep main app hidden
                gr.update(value="")  # Clear user info
            )
    
    def complete_task(session_state, task_name):
        """Complete a task and award points (session-aware)."""
        username = get_session_username(session_state)
        
        if not is_session_authenticated(session_state):
            return "⚠️ Please sign in to complete tasks."
        
        # Award points to the authenticated user (from their session)
        if username not in USER_DATA:
            USER_DATA[username] = {"points": 0, "tasks_completed": []}
        
        USER_DATA[username]["points"] += 100
        USER_DATA[username]["tasks_completed"].append(task_name)
        
        points = USER_DATA[username]["points"]
        tasks = len(USER_DATA[username]["tasks_completed"])
        
        return f"✓ Task '{task_name}' completed! You now have {points} points ({tasks} tasks completed)."
    
    def show_leaderboard(session_state):
        """Show leaderboard highlighting current user."""
        username = get_session_username(session_state)
        
        # Build leaderboard (keyed by username, so multi-user safe)
        leaderboard = sorted(
            [(user, data["points"]) for user, data in USER_DATA.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        if not leaderboard:
            return "No users have completed tasks yet."
        
        html = "### 🏆 Leaderboard\n\n"
        html += "| Rank | User | Points |\n"
        html += "|------|------|--------|\n"
        
        for rank, (user, points) in enumerate(leaderboard, 1):
            highlight = " **← You**" if user == username else ""
            html += f"| {rank} | {user}{highlight} | {points} |\n"
        
        return html
    
    # Build the Gradio app
    with gr.Blocks(title="Session Auth Demo", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🔐 Multi-User Session Authentication Demo")
        gr.Markdown(
            """
            This demo shows how session-based authentication works for Cloud Run deployments.
            
            **Try it:**
            1. Open this app in two different browsers
            2. Login as different users in each browser
            3. Complete tasks in each browser
            4. See that each user has their own points and data
            5. Verify no cross-contamination between sessions
            """
        )
        
        # Session state - ONE per user session (NEVER shared!)
        session_state = gr.State(value=create_session_state())
        
        # Login section
        with gr.Row(visible=True) as login_section:
            with gr.Column():
                gr.Markdown("### Sign In")
                gr.Markdown("Use your modelshare.ai credentials, or use demo/demo for testing.")
                username_input = gr.Textbox(label="Username", placeholder="Enter username")
                password_input = gr.Textbox(label="Password", type="password", placeholder="Enter password")
                login_btn = gr.Button("Sign In", variant="primary")
        
        login_status = gr.Markdown("", visible=False)
        
        # Main app (visible after login)
        with gr.Column(visible=False) as main_app:
            user_info = gr.Markdown("")
            
            gr.Markdown("### Complete Tasks")
            task_input = gr.Textbox(label="Task Name", placeholder="e.g., 'Learn about bias'")
            complete_btn = gr.Button("Complete Task", variant="primary")
            task_feedback = gr.Markdown("")
            
            gr.Markdown("### Leaderboard")
            leaderboard_display = gr.Markdown("")
            refresh_btn = gr.Button("Refresh Leaderboard")
        
        # Wire up event handlers
        login_btn.click(
            fn=handle_login,
            inputs=[session_state, username_input, password_input],
            outputs=[session_state, login_section, login_status, main_app, user_info]
        )
        
        complete_btn.click(
            fn=complete_task,
            inputs=[session_state, task_input],  # session_state MUST be first input
            outputs=task_feedback
        )
        
        refresh_btn.click(
            fn=show_leaderboard,
            inputs=[session_state],  # session_state passed to every handler
            outputs=leaderboard_display
        )
    
    return app


if __name__ == "__main__":
    import os
    app = create_demo_app()
    port = int(os.environ.get("PORT", 8080))
    app.launch(server_port=port, share=False)
