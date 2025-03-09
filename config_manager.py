import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import keyring
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        
        # Load environment variables
        load_dotenv()
    
    def load_config(self):
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return self.get_default_config()
        else:
            return self.get_default_config()
    
    def get_default_config(self):
        """Return default configuration"""
        return {
            "api": {
                "url": "http://127.0.0.1:5000",
                "timeout": 30
            },
            "ui": {
                "theme": "light",
                "font_size": 12,
                "window_size": "600x700"
            },
            "database": {
                "enabled": True,
                "path": "qa_database.db"
            }
        }
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get(self, section, key=None):
        """Get configuration value(s)"""
        if key is None:
            return self.config.get(section, {})
        return self.config.get(section, {}).get(key)
    
    def set(self, section, key, value):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        return self.save_config()
    
    def get_api_key(self, service_name="gemini_api"):
        """Get API key from keyring"""
        try:
            api_key = keyring.get_password(service_name, "api_key")
            
            # If not in keyring, try environment variables
            if not api_key:
                api_key = os.environ.get("GEMINI_API_KEY")
            
            return api_key
        except Exception:
            return None
    
    def set_api_key(self, api_key, service_name="gemini_api"):
        """Store API key in keyring"""
        try:
            keyring.set_password(service_name, "api_key", api_key)
            return True
        except Exception:
            return False

class ConfigDialog:
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog relative to parent
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (500 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (400 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_widgets()
    
    def create_widgets(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # API settings tab
        self.api_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.api_frame, text="API Settings")
        
        ttk.Label(self.api_frame, text="API URL:").grid(row=0, column=0, sticky="w", padx=10, pady=(15, 5))
        
        self.api_url_var = tk.StringVar(value=self.config_manager.get("api", "url"))
        self.api_url_entry = ttk.Entry(self.api_frame, textvariable=self.api_url_var, width=40)
        self.api_url_entry.grid(row=0, column=1, sticky="we", padx=10, pady=(15, 5))
        
        ttk.Label(self.api_frame, text="API Timeout (seconds):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        
        self.api_timeout_var = tk.IntVar(value=self.config_manager.get("api", "timeout"))
        self.api_timeout_spinbox = ttk.Spinbox(self.api_frame, from_=5, to=120, textvariable=self.api_timeout_var, width=5)
        self.api_timeout_spinbox.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # API Key section
        ttk.Separator(self.api_frame).grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        ttk.Label(self.api_frame, text="Google Gemini API Key:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        
        self.api_key_var = tk.StringVar(value=self.config_manager.get_api_key() or "")
        self.api_key_entry = ttk.Entry(self.api_frame, textvariable=self.api_key_var, width=40, show="*")
        self.api_key_entry.grid(row=3, column=1, sticky="we", padx=10, pady=5)
        
        self.show_key_var = tk.BooleanVar(value=False)
        self.show_key_check = ttk.Checkbutton(
            self.api_frame, 
            text="Show API Key", 
            variable=self.show_key_var,
            command=self.toggle_api_key_visibility
        )
        self.show_key_check.grid(row=4, column=1, sticky="w", padx=10, pady=5)
        
        # UI settings tab
        self.ui_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ui_frame, text="UI Settings")
        
        ttk.Label(self.ui_frame, text="Theme:").grid(row=0, column=0, sticky="w", padx=10, pady=(15, 5))
        
        self.theme_var = tk.StringVar(value=self.config_manager.get("ui", "theme"))
        self.theme_combo = ttk.Combobox(self.ui_frame, textvariable=self.theme_var, values=["light", "dark"], state="readonly", width=10)
        self.theme_combo.grid(row=0, column=1, sticky="w", padx=10, pady=(15, 5))
        
        ttk.Label(self.ui_frame, text="Font Size:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        
        self.font_size_var = tk.IntVar(value=self.config_manager.get("ui", "font_size"))
        self.font_size_spinbox = ttk.Spinbox(self.ui_frame, from_=8, to=24, textvariable=self.font_size_var, width=5)
        self.font_size_spinbox.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Database settings tab
        self.db_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.db_frame, text="Database")
        
        self.db_enabled_var = tk.BooleanVar(value=self.config_manager.get("database", "enabled"))
        self.db_enabled_check = ttk.Checkbutton(
            self.db_frame, 
            text="Enable Database Cache", 
            variable=self.db_enabled_var
        )
        self.db_enabled_check.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))
        
        ttk.Label(self.db_frame, text="Database Path:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        
        self.db_path_var = tk.StringVar(value=self.config_manager.get("database", "path"))
        self.db_path_entry = ttk.Entry(self.db_frame, textvariable=self.db_path_var, width=40)
        self.db_path_entry.grid(row=1, column=1, sticky="we", padx=10, pady=5)
        
        # Buttons at the bottom
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_to_defaults).pack(side=tk.LEFT, padx=5)
    
    def toggle_api_key_visibility(self):
        """Toggle API key visibility"""
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")
    
    def save_settings(self):
        """Save all settings"""
        # Save API settings
        self.config_manager.set("api", "url", self.api_url_var.get())
        self.config_manager.set("api", "timeout", self.api_timeout_var.get())
        
        # Save API key
        if self.api_key_var.get():
            self.config_manager.set_api_key(self.api_key_var.get())
        
        # Save UI settings
        self.config_manager.set("ui", "theme", self.theme_var.get())
        self.config_manager.set("ui", "font_size", self.font_size_var.get())
        
        # Save database settings
        self.config_manager.set("database", "enabled", self.db_enabled_var.get())
        self.config_manager.set("database", "path", self.db_path_var.get())
        
        messagebox.showinfo("Settings", "Settings saved successfully")
        self.dialog.destroy()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?"):
            # Get default config
            default_config = self.config_manager.get_default_config()
            
            # Update API settings
            self.api_url_var.set(default_config["api"]["url"])
            self.api_timeout_var.set(default_config["api"]["timeout"])
            
            # Update UI settings
            self.theme_var.set(default_config["ui"]["theme"])
            self.font_size_var.set(default_config["ui"]["font_size"])
            
            # Update database settings
            self.db_enabled_var.set(default_config["database"]["enabled"])
            self.db_path_var.set(default_config["database"]["path"])