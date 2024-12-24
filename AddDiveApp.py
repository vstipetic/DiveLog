import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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
        
        # Output selection frame
        output_frame = ttk.Frame(self)
        output_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        
        # Output folder selection
        ttk.Label(output_frame, text="Save Location:").grid(row=0, column=0, padx=5, pady=5)
        self.output_path = ttk.Entry(output_frame)
        self.output_path.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(output_frame, text="Browse", command=self.browse_output).grid(row=0, column=2, padx=5, pady=5)
        
        # Output filename
        ttk.Label(output_frame, text="Save As:").grid(row=1, column=0, padx=5, pady=5)
        self.output_filename = ttk.Entry(output_frame)
        self.output_filename.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(output_frame, text=".pickle").grid(row=1, column=2, padx=0, pady=5)
        
        # Gear selection
        ttk.Label(self, text="Used Gear:").grid(row=2, column=0, padx=5, pady=5)
        self.gear_frame = ttk.Frame(self)
        self.gear_frame.grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        
        self.gear_paths = {}
        for idx, gear_type in enumerate(["Mask", "Suit", "Gloves", "Boots"]):
            ttk.Label(self.gear_frame, text=f"{gear_type}:").grid(row=idx, column=0, padx=5, pady=2)
            entry = ttk.Entry(self.gear_frame)
            entry.grid(row=idx, column=1, padx=5, pady=2)
            ttk.Button(self.gear_frame, text="Browse", 
                      command=lambda t=gear_type, e=entry: self.browse_gear(t, e)).grid(row=idx, column=2, padx=5, pady=2)
            self.gear_paths[gear_type] = entry
            
        # Metadata
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
        
        # Location frame
        self.location_frame = ttk.LabelFrame(self, text="Location")
        self.location_frame.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        
        # Location name
        ttk.Label(self.location_frame, text="Name:").grid(row=0, column=0, padx=5, pady=2)
        self.location_name = ttk.Entry(self.location_frame)
        self.location_name.grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        
        # Description
        ttk.Label(self.location_frame, text="Description:").grid(row=1, column=0, padx=5, pady=2)
        self.location_desc = ttk.Entry(self.location_frame)
        self.location_desc.grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        
        # Gas information frame
        gas_frame = ttk.LabelFrame(self, text="Gas Information")
        gas_frame.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        ttk.Label(gas_frame, text="Start Pressure (bar):").grid(row=0, column=0, padx=5, pady=2)
        self.start_pressure = ttk.Entry(gas_frame)
        self.start_pressure.grid(row=0, column=1, columnspan=2, padx=5, pady=2, sticky="ew")

        ttk.Label(gas_frame, text="End Pressure (bar):").grid(row=1, column=0, padx=5, pady=2)
        self.end_pressure = ttk.Entry(gas_frame)
        self.end_pressure.grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        
        # Save button
        ttk.Button(self, text="Save Dive", command=self.save_dive).grid(row=6, column=0, columnspan=3, pady=20)
        
        self.grid(padx=10, pady=10)
        
    def browse_fit(self):
        """Browse for input .fit file"""
        filename = filedialog.askopenfilename(
            filetypes=[("FIT files", "*.fit"), ("All files", "*.*")]
        )
        if filename:
            self.fit_path.delete(0, tk.END)
            self.fit_path.insert(0, filename)
            # Set default output filename based on input file
            default_name = Path(filename).stem
            self.output_filename.delete(0, tk.END)
            self.output_filename.insert(0, default_name)

    def browse_output(self):
        """Browse for output folder"""
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.delete(0, tk.END)
            self.output_path.insert(0, folder)

    def browse_gear(self, gear_type: str, entry: ttk.Entry):
        """Browse for gear pickle files"""
        filename = filedialog.askopenfilename(
            filetypes=[("Pickle files", "*.pickle"), ("All files", "*.*")]
        )
        if filename:
            entry.delete(0, tk.END)
            entry.insert(0, filename)

    def save_dive(self):
        if not self.fit_path.get() or not self.output_path.get() or not self.output_filename.get():
            messagebox.showerror("Error", "Please select input file, output location, and provide a filename")
            return
            
        # Create output path using the selected directory and custom filename
        output_path = Path(self.output_path.get()) / f"{self.output_filename.get()}.pickle"
        
        # Check if file already exists
        if output_path.exists():
            if not messagebox.askyesno("Warning", "File already exists. Do you want to overwrite it?"):
                return
        
        # Parse group names into a set
        group = set(filter(None, [name.strip() for name in self.group_entry.get().split(',')]))
        
        add_dive(
            fit_file_path=self.fit_path.get(),
            output_path=str(output_path),
            location_name=self.location_name.get(),
            location_description=self.location_desc.get(),
            buddy=self.buddy_entry.get(),
            divemaster=self.divemaster_entry.get() or None,
            group=group,
            start_pressure=int(self.start_pressure.get() or 0),
            end_pressure=int(self.end_pressure.get() or 0),
            suit=self.gear_paths.get("Suit").get() or None,
            mask=self.gear_paths.get("Mask").get() or None,
            gloves=self.gear_paths.get("Gloves").get() or None,
            boots=self.gear_paths.get("Boots").get() or None
        )
        
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DiveAdderApp(root)
    root.mainloop()
