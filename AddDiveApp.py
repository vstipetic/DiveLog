import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from Utilities.AddDive import add_dive

class DiveAdderApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.master.title("Dive Logger")
        
        # Fit file selection
        ttk.Label(self, text="Dive Data (.fit):").grid(row=0, column=0, padx=5, pady=5)
        self.fit_path = ttk.Entry(self)
        self.fit_path.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self, text="Browse", command=self.browse_fit).grid(row=0, column=2, padx=5, pady=5)
        
        # Gear selection
        ttk.Label(self, text="Used Gear:").grid(row=1, column=0, padx=5, pady=5)
        self.gear_frame = ttk.Frame(self)
        self.gear_frame.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        
        self.gear_paths = {}
        for idx, gear_type in enumerate(["Mask", "Suit", "Gloves", "Boots"]):
            ttk.Label(self.gear_frame, text=f"{gear_type}:").grid(row=idx, column=0, padx=5, pady=2)
            entry = ttk.Entry(self.gear_frame)
            entry.grid(row=idx, column=1, padx=5, pady=2)
            ttk.Button(self.gear_frame, text="Browse", 
                      command=lambda t=gear_type, e=entry: self.browse_gear(t, e)).grid(row=idx, column=2, padx=5, pady=2)
            self.gear_paths[gear_type] = entry
            
        # Metadata
        ttk.Label(self, text="Metadata (Optional):").grid(row=2, column=0, columnspan=3, pady=10)
        
        metadata_frame = ttk.Frame(self)
        metadata_frame.grid(row=3, column=0, columnspan=3, padx=5, pady=5)
        
        ttk.Label(metadata_frame, text="Buddy:").grid(row=0, column=0, padx=5, pady=2)
        self.buddy_entry = ttk.Entry(metadata_frame)
        self.buddy_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(metadata_frame, text="Divemaster:").grid(row=1, column=0, padx=5, pady=2)
        self.divemaster_entry = ttk.Entry(metadata_frame)
        self.divemaster_entry.grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(metadata_frame, text="Group:").grid(row=2, column=0, padx=5, pady=2)
        self.group_entry = ttk.Entry(metadata_frame)
        self.group_entry.grid(row=2, column=1, padx=5, pady=2)
        
        ttk.Label(metadata_frame, text="Location Name:").grid(row=3, column=0, padx=5, pady=2)
        self.location_name_entry = ttk.Entry(metadata_frame)
        self.location_name_entry.grid(row=3, column=1, padx=5, pady=2)
        
        ttk.Label(metadata_frame, text="Location Description:").grid(row=4, column=0, padx=5, pady=2)
        self.location_desc_entry = ttk.Entry(metadata_frame)
        self.location_desc_entry.grid(row=4, column=1, padx=5, pady=2)
        
        # Save location
        ttk.Label(self, text="Save Location:").grid(row=4, column=0, padx=5, pady=5)
        self.save_path = ttk.Entry(self)
        self.save_path.grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(self, text="Browse", command=self.browse_save).grid(row=4, column=2, padx=5, pady=5)
        
        ttk.Label(self, text="File Name:").grid(row=5, column=0, padx=5, pady=5)
        self.filename_entry = ttk.Entry(self)
        self.filename_entry.grid(row=5, column=1, padx=5, pady=5)
        ttk.Label(self, text=".pickle").grid(row=5, column=2, padx=5, pady=5)
        
        # Save button
        ttk.Button(self, text="Save Dive", command=self.save_dive).grid(row=6, column=0, columnspan=3, pady=20)
        
        self.grid(padx=10, pady=10)
        
    def browse_fit(self):
        filename = filedialog.askopenfilename(filetypes=[("FIT files", "*.fit")])
        if filename:
            self.fit_path.delete(0, tk.END)
            self.fit_path.insert(0, filename)
            
    def browse_gear(self, gear_type, entry):
        filename = filedialog.askopenfilename(filetypes=[("Pickle files", "*.pickle")])
        if filename:
            entry.delete(0, tk.END)
            entry.insert(0, filename)
            
    def browse_save(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_path.delete(0, tk.END)
            self.save_path.insert(0, folder)
            
    def save_dive(self):
        if not self.fit_path.get() or not self.filename_entry.get() or not self.save_path.get():
            return
            
        output_path = Path(self.save_path.get()) / f"{self.filename_entry.get()}.pickle"
        
        # Get group as set
        group = set(g.strip() for g in self.group_entry.get().split(',')) if self.group_entry.get() else None
        
        # Create dive using AddDive utility
        add_dive(
            fit_file_path=self.fit_path.get(),
            output_path=str(output_path),
            location_name=self.location_name_entry.get(),
            location_description=self.location_desc_entry.get(),
            buddy=self.buddy_entry.get(),
            divemaster=self.divemaster_entry.get() or None,
            group=group,
            mask=self.gear_paths["Mask"].get() or None,
            suit=self.gear_paths["Suit"].get() or None,
            gloves=self.gear_paths["Gloves"].get() or None,
            boots=self.gear_paths["Boots"].get() or None
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = DiveAdderApp(root)
    root.mainloop()
