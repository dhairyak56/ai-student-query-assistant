import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import requests
import json
import threading
import time
import os

class QueryAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Student Query Assistant")
        self.root.geometry("600x700")
        self.root.minsize(500, 600)
        
        # Set theme colors
        self.colors = {
            "primary": "#4a6fa5",
            "secondary": "#e0e0e0",
            "bg": "#f5f5f5",
            "text": "#333333",
            "success": "#4CAF50",
            "error": "#f44336",
            "warning": "#ff9800"
        }
        
        # API endpoint configuration
        self.api_url = self.get_api_url()
        
        # State variables
        self.is_connected = False
        self.is_sending = False
        self.connection_check_thread = None
        
        # UI Components
        self.create_widgets()
        
        # Start connection check
        self.start_connection_checker()
    
    def get_api_url(self):
        """Get API URL from environment or use default"""
        return os.environ.get("API_URL", "http://127.0.0.1:5000")
    
    def create_widgets(self):
        # Main frame using grid layout
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        # Title and connection status
        title_frame = ttk.Frame(self.main_frame)
        title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        title_frame.columnconfigure(0, weight=1)
        
        self.title_label = ttk.Label(
            title_frame, 
            text="AI Student Query Assistant", 
            font=("Arial", 16, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.connection_indicator = ttk.Label(
            title_frame,
            text="⚠️ Checking connection...",
            foreground=self.colors["warning"]
        )
        self.connection_indicator.grid(row=0, column=1, sticky="e")
        
        # Chat history section
        self.chat_frame = ttk.Frame(self.main_frame)
        self.chat_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        self.chat_frame.columnconfigure(0, weight=1)
        self.chat_frame.rowconfigure(0, weight=1)
        
        self.text_area = scrolledtext.ScrolledText(
            self.chat_frame, 
            wrap=tk.WORD,
            font=("Arial", 12),
            bg="#FFFFFF",
            padx=10,
            pady=10
        )
        self.text_area.grid(row=0, column=0, sticky="nsew")
        self.text_area.config(state=tk.DISABLED)
        
        # Tag configurations for different message types
        self.text_area.tag_configure("user", foreground="#0077cc", font=("Arial", 12, "bold"))
        self.text_area.tag_configure("assistant", foreground="#2e7d32")
        self.text_area.tag_configure("error", foreground="#d32f2f")
        self.text_area.tag_configure("system", foreground="#9e9e9e", font=("Arial", 10, "italic"))
        
        # Input section with modern styling
        self.input_frame = ttk.Frame(self.main_frame)
        self.input_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.input_frame.columnconfigure(0, weight=1)
        
        # Create a custom style for the input field
        style = ttk.Style()
        style.configure("Custom.TEntry", padding=10)
        
        self.entry = ttk.Entry(
            self.input_frame, 
            font=("Arial", 12),
            style="Custom.TEntry"
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.entry.bind("<Return>", self.on_enter_pressed)
        
        # Button frame for submit and clear
        button_frame = ttk.Frame(self.input_frame)
        button_frame.grid(row=0, column=1, sticky="e")
        
        self.submit_button = ttk.Button(
            button_frame, 
            text="Send",
            command=self.get_response
        )
        self.submit_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.clear_button = ttk.Button(
            button_frame, 
            text="Clear", 
            command=self.clear_chat
        )
        self.clear_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Status bar
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(
            self.status_frame, 
            textvariable=self.status_var,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.LEFT, fill=tk.X)
        
        # Add some initial system messages
        self.add_system_message("Welcome to the AI Student Query Assistant!")
        self.add_system_message("Type your question and press Enter or click Send.")
    
    def start_connection_checker(self):
        """Start a thread to periodically check backend connection"""
        if self.connection_check_thread is None or not self.connection_check_thread.is_alive():
            self.connection_check_thread = threading.Thread(target=self.check_connection_periodically)
            self.connection_check_thread.daemon = True
            self.connection_check_thread.start()
    
    def check_connection_periodically(self):
        """Check connection every 30 seconds"""
        while True:
            self.check_connection()
            time.sleep(30)
    
    def check_connection(self):
        """Check if backend API is available"""
        try:
            # Try a health check endpoint
            health_url = f"{self.api_url}/health"
            response = requests.get(health_url, timeout=3)
            
            if response.status_code == 200:
                self.is_connected = True
                self.root.after(0, self.update_connection_indicator, True)
            else:
                self.is_connected = False
                self.root.after(0, self.update_connection_indicator, False)
        except:
            # If the health endpoint doesn't exist, try the query endpoint
            try:
                response = requests.post(
                    f"{self.api_url}/query", 
                    json={"question": "test"}, 
                    timeout=3
                )
                self.is_connected = True
                self.root.after(0, self.update_connection_indicator, True)
            except:
                self.is_connected = False
                self.root.after(0, self.update_connection_indicator, False)
    
    def update_connection_indicator(self, is_connected):
        """Update the connection indicator in the UI thread"""
        if is_connected:
            self.connection_indicator.config(
                text="✅ Connected",
                foreground=self.colors["success"]
            )
        else:
            self.connection_indicator.config(
                text="❌ Not Connected",
                foreground=self.colors["error"]
            )
    
    def on_enter_pressed(self, event):
        """Handle Enter key press in entry field"""
        if not self.is_sending:
            self.get_response()
    
    def add_system_message(self, message):
        """Add a system message to the chat"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f"System: {message}\n\n", "system")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)
        
    def get_response(self):
        """Get response from API for the current query"""
        query = self.entry.get().strip()
        if not query:
            messagebox.showinfo("Info", "Please enter a question")
            return
            
        if len(query) > 500:
            messagebox.showwarning("Warning", "Question is too long (max 500 characters)")
            return
        
        if not self.is_connected:
            self.add_system_message("Cannot connect to the server. Please make sure the backend is running.")
            return
            
        # Update UI to show processing
        self.is_sending = True
        self.status_var.set("Processing query...")
        self.submit_button.config(state=tk.DISABLED)
        self.entry.config(state=tk.DISABLED)
        
        # Start a thread to handle the API call
        threading.Thread(target=self.send_request, args=(query,), daemon=True).start()
    
    def send_request(self, query):
        """Send request to API in a separate thread"""
        try:
            # Add user message to chat first
            self.root.after(0, self.add_user_message, query)
            
            # Add typing indicator
            self.root.after(0, self.add_typing_indicator)
            
            # Make API request
            try:
                response = requests.post(
                    f"{self.api_url}/query", 
                    json={"question": query},
                    timeout=30  # 30 second timeout
                )
            except requests.ConnectionError:
                # Remove typing indicator and show error
                self.root.after(0, self.remove_typing_indicator)
                self.root.after(0, self.add_assistant_message, 
                               "I can't connect to the server right now. Please make sure the backend is running and try again.", 
                               is_error=True)
                return
            
            # Remove typing indicator
            self.root.after(0, self.remove_typing_indicator)
            
            # Process and display response
            if response.status_code == 200:
                answer = response.json().get("answer", "No response")
                self.root.after(0, self.add_assistant_message, answer)
            else:
                # Try to get the error message from the response if available
                try:
                    error_detail = response.json().get("error", "Unknown error")
                    error_msg = f"Error: {error_detail} (Status code: {response.status_code})"
                except:
                    error_msg = f"Error: Server returned status code {response.status_code}"
                    
                self.root.after(0, self.add_assistant_message, error_msg, is_error=True)
                
        except requests.RequestException as e:
            self.root.after(0, self.remove_typing_indicator)
            self.root.after(0, self.add_assistant_message, f"Connection error - {str(e)}", is_error=True)
        except json.JSONDecodeError:
            self.root.after(0, self.remove_typing_indicator)
            self.root.after(0, self.add_assistant_message, 
                           "The server response was invalid. Please check if the backend is running correctly.", 
                           is_error=True)
        except Exception as e:
            self.root.after(0, self.remove_typing_indicator)
            self.root.after(0, self.add_assistant_message, f"An unexpected error occurred: {str(e)}", is_error=True)
        finally:
            # Reset UI state
            self.root.after(0, self.reset_ui_state)
    
    def add_user_message(self, message):
        """Add user message to the chat"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f"You: {message}\n", "user")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)
    
    def add_typing_indicator(self):
        """Add typing indicator to the chat"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, "Assistant: Typing", "assistant")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)
        self.typing_dots = 0
        self.update_typing_indicator()
    
    def update_typing_indicator(self):
        """Update the typing animation"""
        if not hasattr(self, "typing_animation_id"):
            self.typing_animation_id = None
            
        if self.typing_animation_id:
            self.root.after_cancel(self.typing_animation_id)
            self.typing_animation_id = None
            
        if hasattr(self, "typing_dots") and self.typing_dots is not None:
            self.text_area.config(state=tk.NORMAL)
            
            # Find last "Assistant: Typing" line and update dots
            content = self.text_area.get("1.0", tk.END)
            last_typing_pos = content.rfind("Assistant: Typing")
            
            if last_typing_pos >= 0:
                # Calculate position in the text widget
                line_count = content[:last_typing_pos].count('\n') + 1
                char_pos = len("Assistant: Typing") + (self.typing_dots if self.typing_dots <= 3 else 0)
                
                # Delete old dots if any
                if self.typing_dots > 0:
                    start_pos = f"{line_count}.{len('Assistant: Typing')}"
                    end_pos = f"{line_count}.{len('Assistant: Typing') + 3}"
                    self.text_area.delete(start_pos, end_pos)
                
                # Add new dots
                dots = "." * ((self.typing_dots % 4) + 1)
                self.text_area.insert(f"{line_count}.{len('Assistant: Typing')}", dots)
                
                self.typing_dots += 1
                self.typing_animation_id = self.root.after(300, self.update_typing_indicator)
            
            self.text_area.config(state=tk.DISABLED)
    
    def remove_typing_indicator(self):
        """Remove typing indicator"""
        if hasattr(self, "typing_animation_id") and self.typing_animation_id:
            self.root.after_cancel(self.typing_animation_id)
            self.typing_animation_id = None
            
        self.typing_dots = None
        content = self.text_area.get("1.0", tk.END)
        last_typing_pos = content.rfind("Assistant: Typing")
        
        if last_typing_pos >= 0:
            self.text_area.config(state=tk.NORMAL)
            
            # Find and delete the typing indicator line
            line_count = content[:last_typing_pos].count('\n') + 1
            start_pos = f"{line_count}.0"
            end_pos = f"{line_count + 1}.0"
            self.text_area.delete(start_pos, end_pos)
            
            self.text_area.config(state=tk.DISABLED)
    
    def add_assistant_message(self, message, is_error=False):
        """Add assistant message to the chat"""
        self.text_area.config(state=tk.NORMAL)
        
        tag = "error" if is_error else "assistant"
        self.text_area.insert(tk.END, f"Assistant: {message}\n\n", tag)
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)
    
    def reset_ui_state(self):
        """Reset UI state after request completes"""
        self.status_var.set("Ready")
        self.submit_button.config(state=tk.NORMAL)
        self.entry.config(state=tk.NORMAL)
        self.entry.delete(0, tk.END)
        self.entry.focus()
        self.is_sending = False
    
    def clear_chat(self):
        """Clear the chat history"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state=tk.DISABLED)
        self.entry.delete(0, tk.END)
        self.status_var.set("Chat cleared")
        
        # Add welcome message back
        self.add_system_message("Welcome to the AI Student Query Assistant!")
        self.add_system_message("Type your question and press Enter or click Send.")

if __name__ == "__main__":
    root = tk.Tk()
    app = QueryAssistantApp(root)
    root.mainloop()