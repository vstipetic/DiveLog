import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from AddDiveApp import DiveAdderApp
from AddGearApp import GearAdderApp
from Utilities.AddDive import bulk_add_dives

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
        # Create statistics window with tabs for dive and gear stats
        stats_window = tk.Toplevel(self.master)
        stats_window.title("Dive Log Statistics")
        stats_window.geometry("600x400")
        
        notebook = ttk.Notebook(stats_window)
        notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        dive_stats_frame = ttk.Frame(notebook)
        gear_stats_frame = ttk.Frame(notebook)
        
        notebook.add(dive_stats_frame, text="Dive Statistics")
        notebook.add(gear_stats_frame, text="Gear Statistics")
        
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