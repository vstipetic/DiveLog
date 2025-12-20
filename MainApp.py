import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from AddDiveApp import DiveAdderApp
from AddGearApp import GearAdderApp
from Utilities.AddDive import bulk_add_dives
from Utilities.StatisticsAgent import StatisticsAgent
from Utilities.APIKeyDetector import detect_api_keys

class MainApplication(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.master.title("Dive Log Manager")
        self.master.geometry("800x600")
        
        # Create main menu
        self.create_menu()
        
        # Welcome message
        welcome_frame = ttk.Frame(self)
        welcome_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        ttk.Label(
            welcome_frame, 
            text="Welcome to Dive Log Manager",
            font=('Helvetica', 16, 'bold')
        ).pack(pady=20)
        
        # Main buttons
        button_frame = ttk.Frame(welcome_frame)
        button_frame.pack(expand=True)
        
        ttk.Button(
            button_frame,
            text="Add New Dive",
            command=self.open_dive_adder,
            width=20
        ).pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Bulk Import Dives",
            command=self.bulk_import_dives,
            width=20
        ).pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Add New Gear",
            command=self.open_gear_adder,
            width=20
        ).pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="View Statistics",
            command=self.show_statistics,
            width=20
        ).pack(pady=10)
        
        self.pack(expand=True, fill='both')
        
    def create_menu(self):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Add New Dive", command=self.open_dive_adder)
        file_menu.add_command(label="Bulk Import Dives", command=self.bulk_import_dives)
        file_menu.add_command(label="Add New Gear", command=self.open_gear_adder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)
        
        # Statistics menu
        stats_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Statistics", menu=stats_menu)
        stats_menu.add_command(label="Dive Statistics", command=self.show_dive_stats)
        stats_menu.add_command(label="Gear Statistics", command=self.show_gear_stats)
    
    def open_dive_adder(self):
        dive_window = tk.Toplevel(self.master)
        dive_app = DiveAdderApp(dive_window)
    
    def open_gear_adder(self):
        gear_window = tk.Toplevel(self.master)
        gear_app = GearAdderApp(gear_window)
    
    def show_statistics(self):
        # First, prompt for dive folder if not already selected
        if not hasattr(self, 'dive_folder'):
            self.dive_folder = filedialog.askdirectory(title="Select Folder Containing Dive Files")
            if not self.dive_folder:
                return
        
        stats_window = tk.Toplevel(self.master)
        stats_window.title("Dive Log Statistics")
        stats_window.geometry("800x600")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(stats_window)
        notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # AI Query tab
        ai_frame = ttk.Frame(notebook)
        notebook.add(ai_frame, text="AI Query")
        
        # API Key selection frame
        api_frame = ttk.Frame(ai_frame)
        api_frame.pack(fill='x', pady=(10, 5), padx=5)
        
        ttk.Label(api_frame, text="Select LLM API:").pack(side='left', padx=(0, 10))
        
        # Detect available API keys
        available_apis = detect_api_keys()
        api_var = tk.StringVar()
        api_dropdown = ttk.Combobox(
            api_frame, 
            textvariable=api_var,
            values=list(available_apis.keys()),
            state='readonly'
        )
        api_dropdown.pack(side='left')
        if available_apis:
            api_dropdown.set(list(available_apis.keys())[0])
        
        # Chat history
        chat_history = tk.Text(ai_frame, height=15, wrap='word', state='disabled')
        chat_history.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Query input frame
        query_frame = ttk.Frame(ai_frame)
        query_frame.pack(fill='x', padx=5, pady=5)
        
        query_entry = ttk.Entry(query_frame)
        query_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        def send_query():
            query = query_entry.get()
            if not query:
                return
            
            # Initialize agent if needed
            if not hasattr(self, 'statistics_agent'):
                selected_api = available_apis[api_var.get()]
                self.statistics_agent = StatisticsAgent(
                    api_key=selected_api,
                    dive_folder=self.dive_folder
                )
            
            # Enable text widget for updating
            chat_history.configure(state='normal')
            chat_history.insert('end', f"\nYou: {query}\n")
            
            try:
                response = self.statistics_agent.process_query(query)
                chat_history.insert('end', f"Agent: {response}\n")
            except Exception as e:
                chat_history.insert('end', f"Error: {str(e)}\n")
            
            chat_history.configure(state='disabled')
            chat_history.see('end')
            query_entry.delete(0, 'end')
        
        send_button = ttk.Button(query_frame, text="Send", command=send_query)
        send_button.pack(side='right')
        
        # Bind Enter key to send query
        query_entry.bind('<Return>', lambda e: send_query())
        
        # Add existing statistics tabs
        dive_stats_frame = ttk.Frame(notebook)
        gear_stats_frame = ttk.Frame(notebook)
        notebook.add(dive_stats_frame, text="Basic Dive Stats")
        notebook.add(gear_stats_frame, text="Basic Gear Stats")
        
        self.populate_dive_stats(dive_stats_frame)
        self.populate_gear_stats(gear_stats_frame)
    
    def show_dive_stats(self):
        stats_window = tk.Toplevel(self.master)
        stats_window.title("Dive Statistics")
        self.populate_dive_stats(stats_window)
    
    def show_gear_stats(self):
        stats_window = tk.Toplevel(self.master)
        stats_window.title("Gear Statistics")
        self.populate_gear_stats(stats_window)
    
    def populate_dive_stats(self, frame):
        # To be implemented: Add dive statistics
        ttk.Label(frame, text="Dive statistics coming soon...").pack(pady=20)
    
    def populate_gear_stats(self, frame):
        # To be implemented: Add gear statistics
        ttk.Label(frame, text="Gear statistics coming soon...").pack(pady=20)
    
    def bulk_import_dives(self):
        # Ask for input directory
        input_dir = filedialog.askdirectory(title="Select Directory with .fit Files")
        if not input_dir:
            return
        
        # Ask for output directory
        output_dir = filedialog.askdirectory(title="Select Output Directory for Dive Files")
        if not output_dir:
            return
        
        try:
            dives = bulk_add_dives(input_dir, output_dir)
            messagebox.showinfo(
                "Import Complete", 
                f"Successfully imported {len(dives)} dives."
            )
        except Exception as e:
            messagebox.showerror(
                "Import Error",
                f"Error during bulk import: {str(e)}"
            )

def main():
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()

if __name__ == "__main__":
    main() 