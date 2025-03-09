import tkinter as tk
from tkinter import messagebox, Menu
import logging
import threading
import os
import sys
import webbrowser
from functools import partial
import requests

# Import our custom modules
from config_manager import ConfigManager, ConfigDialog
from database_manager import DatabaseManager
from ai_student_query_assistant import QueryAssistantApp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Student Query Assistant")
        
        # Initialize config manager
        self.config_manager = ConfigManager()
        
        # Apply stored window size
        window_size = self.config_manager.get("ui", "window_size")
        self.root.geometry(window_size)
        
        # Initialize database if enabled
        if self.config_manager.get("database", "enabled"):
            db_path = self.config_manager.get("database", "path")
            self.db_manager = DatabaseManager(db_path)
        else:
            self.db_manager = None
        
        # Create menu bar
        self.create_menu()
        
        # Initialize the main app
        self.app = QueryAssistantApp(self.root)
        
        # Set API URL from config
        api_url = self.config_manager.get("api", "url")
        if api_url:
            self.app.api_url = api_url
        
        # Extend the application with additional features
        self.extend_app()
        
        # Start periodic tasks
        self.start_background_tasks()
    
    def create_menu(self):
        """Create the menu bar"""
        menubar = Menu(self.root)
        
        # File menu
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Settings", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Tools menu
        tools_menu = Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Clear Conversation", command=self.clear_conversation)
        
        if self.db_manager:
            tools_menu.add_command(label="Database Statistics", command=self.show_db_stats)
            tools_menu.add_command(label="Clean Database Cache", command=self.clean_database)
        
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="User Guide", command=self.show_user_guide)
        help_menu.add_command(label="Check API Status", command=self.check_api_status)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def extend_app(self):
        """Extend the QueryAssistantApp with additional features"""
        # Keep a reference to the original get_response method
        original_get_response = self.app.get_response
        
        # Override with our extended version that uses the database
        def extended_get_response():
            query = self.app.entry.get().strip()
            if not query:
                messagebox.showinfo("Info", "Please enter a question")
                return
                
            if len(query) > 500:
                messagebox.showwarning("Warning", "Question is too long (max 500 characters)")
                return
            
            # Check database cache if enabled
            cached_answer = None
            if self.db_manager and self.config_manager.get("database", "enabled"):
                cached_answer = self.db_manager.get_cached_answer(query)
            
            if cached_answer:
                # Display cached answer
                self.app.add_user_message(query)
                self.app.add_assistant_message(cached_answer + "\n(Retrieved from cache)")
                self.app.entry.delete(0, tk.END)
                self.app.status_var.set("Answered from cache")
            else:
                # No cached answer, use original method
                original_get_response()
                
                # After getting a response, we'll cache it
                # This is done in a background thread to avoid blocking UI
                if self.db_manager and self.config_manager.get("database", "enabled"):
                    # We need to find a way to access the latest response
                    # For now, we'll use a hack to extract it from the text area
                    def cache_latest_response():
                        # Wait a bit for the response to be added to the text area
                        self.root.after(1000, self._cache_latest_qa_pair, query)
                    
                    threading.Thread(target=cache_latest_response, daemon=True).start()
        
        # Replace the method
        self.app.get_response = extended_get_response
    
    def _cache_latest_qa_pair(self, query):
        """Cache the latest Q&A pair from the text area"""
        if not self.db_manager:
            return
            
        try:
            # Get content from text area
            self.app.text_area.config(state=tk.NORMAL)
            content = self.app.text_area.get("1.0", tk.END)
            self.app.text_area.config(state=tk.DISABLED)
            
            # Find the last assistant response
            parts = content.split("Assistant: ")
            if len(parts) > 1:
                last_response = parts[-1].split("\n\n")[0].strip()
                
                # Cache the Q&A pair
                if last_response and not "(Retrieved from cache)" in last_response:
                    clean_response = last_response.replace("\n(Retrieved from cache)", "")
                    self.db_manager.cache_qa_pair(query, clean_response)
        except Exception as e:
            logger.error(f"Error caching Q&A pair: {e}")
    
    def start_background_tasks(self):
        """Start background tasks"""
        # Schedule database cleanup if enabled
        if self.db_manager and self.config_manager.get("database", "enabled"):
            # Clean database every 24 hours
            def scheduled_db_cleanup():
                self.db_manager.clean_old_entries()
                # Schedule again after 24 hours
                self.root.after(24 * 60 * 60 * 1000, scheduled_db_cleanup)
            
            # Start the first run after 1 hour
            self.root.after(60 * 60 * 1000, scheduled_db_cleanup)
    
    def open_settings(self):
        """Open settings dialog"""
        config_dialog = ConfigDialog(self.root, self.config_manager)
        
        # Update app with new settings if dialog is closed
        self.root.wait_window(config_dialog.dialog)
        
        # Update API URL
        self.app.api_url = self.config_manager.get("api", "url")
        
        # Restart database manager if settings changed
        if self.config_manager.get("database", "enabled"):
            db_path = self.config_manager.get("database", "path")
            if self.db_manager is None or self.db_manager.db_path != db_path:
                if self.db_manager:
                    self.db_manager.close()
                self.db_manager = DatabaseManager(db_path)
        else:
            if self.db_manager:
                self.db_manager.close()
                self.db_manager = None
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.app.clear_chat()
    
    def show_db_stats(self):
        """Show database statistics"""
        if not self.db_manager:
            messagebox.showinfo("Database", "Database is not enabled")
            return
            
        stats = self.db_manager.get_stats()
        
        stats_text = f"Database Statistics:\n\n"
        stats_text += f"Total Entries: {stats['total_entries']}\n"
        stats_text += f"Database Size: {stats['db_size_mb']} MB\n\n"
        
        stats_text += "Popular Questions:\n"
        for q in stats.get('popular_questions', []):
            question = q['question']
            if len(question) > 50:
                question = question[:50] + "..."
            stats_text += f"- {question} (accessed {q['access_count']} times)\n"
        
        messagebox.showinfo("Database Statistics", stats_text)
    
    def clean_database(self):
        """Clean the database cache"""
        if not self.db_manager:
            messagebox.showinfo("Database", "Database is not enabled")
            return
            
        if messagebox.askyesno("Clean Database", "Are you sure you want to clean the database cache?"):
            deleted = self.db_manager.clean_old_entries(max_age_days=7)
            messagebox.showinfo("Database Cleaned", f"Removed {deleted} entries from the database cache.")
    
    def check_api_status(self):
        """Check API status"""
        api_url = self.config_manager.get("api", "url")
        
        # Show checking message
        self.app.status_var.set("Checking API status...")
        self.root.update_idletasks()
        
        # Check in a separate thread
        def check_api():
            try:
                # Try health endpoint first
                health_url = f"{api_url}/health"
                try:
                    response = requests.get(health_url, timeout=5)
                    if response.status_code == 200:
                        self.root.after(0, lambda: self.app.status_var.set("API is online and healthy"))
                        self.root.after(0, lambda: messagebox.showinfo("API Status", "The API server is online and responding normally."))
                        return
                except:
                    pass
                
                # Try query endpoint as fallback
                response = requests.post(
                    f"{api_url}/query", 
                    json={"question": "test"}, 
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.root.after(0, lambda: self.app.status_var.set("API is online"))
                    self.root.after(0, lambda: messagebox.showinfo("API Status", "The API server is online and responding."))
                else:
                    self.root.after(0, lambda: self.app.status_var.set(f"API error: {response.status_code}"))
                    self.root.after(0, lambda: messagebox.showwarning("API Status", f"The API server returned an error code: {response.status_code}"))
            except Exception as e:
                self.root.after(0, lambda: self.app.status_var.set("API connection failed"))
                self.root.after(0, lambda: messagebox.showerror("API Status", f"Could not connect to the API server:\n{str(e)}\n\nMake sure the backend is running (python backend_api.py)."))
        
        threading.Thread(target=check_api, daemon=True).start()
    
    def show_user_guide(self):
        """Show user guide"""
        user_guide = tk.Toplevel(self.root)
        user_guide.title("User Guide")
        user_guide.geometry("600x500")
        user_guide.transient(self.root)
        user_guide.grab_set()
        
        # Center the window
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (600 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (500 // 2)
        user_guide.geometry(f"+{x}+{y}")
        
        # Create a frame with scrollbar
        frame = tk.Frame(user_guide)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add text widget
        text = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=text.yview)
        
        # Add content
        guide_content = """
        # AI Student Query Assistant - User Guide
        
        Welcome to the AI Student Query Assistant! This application helps students get quick answers to their questions.
        
        ## Getting Started
        
        1. Make sure the backend API is running (python backend_api.py)
        2. Type your question in the input field
        3. Press Enter or click Send to get an answer
        
        ## Features
        
        - **Instant Answers**: Get answers to common student questions
        - **Database Cache**: Frequently asked questions are cached for faster responses
        - **Conversation History**: Review your question history within the session
        
        ## Tips
        
        - Keep questions clear and concise
        - For best results, ask one question at a time
        - If the API is not responding, check the backend status
        
        ## Troubleshooting
        
        - If the application displays "Not Connected", make sure the backend API is running
        - Check the API status from the Help menu
        - If you encounter errors, try clearing the conversation
        
        ## Settings
        
        Access the settings from the File menu to configure:
        - API connection details
        - Database cache options
        - UI preferences
        
        ## Support
        
        For support or to report issues, please contact the system administrator.
        """
        
        text.insert(tk.END, guide_content)
        text.config(state=tk.DISABLED)
        
        # Close button
        close_button = tk.Button(user_guide, text="Close", command=user_guide.destroy)
        close_button.pack(pady=10)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
        AI Student Query Assistant
        Version 1.0
        
        A smart assistant for answering student questions.
        
        Features:
        - AI-powered responses
        - Database caching for faster replies
        - User-friendly interface
        
        Created with ❤️ for students
        """
        
        messagebox.showinfo("About", about_text)
    
    def on_exit(self):
        """Handle application exit"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            # Clean up resources
            if self.db_manager:
                self.db_manager.close()
            
            # Save window size
            window_size = f"{self.root.winfo_width()}x{self.root.winfo_height()}"
            self.config_manager.set("ui", "window_size", window_size)
            
            # Exit
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApplication(root)
    root.protocol("WM_DELETE_WINDOW", app.on_exit)
    root.mainloop()