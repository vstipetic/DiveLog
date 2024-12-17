import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import pickle
import Utilities.ClassUtils.GearClasses as Gear
import Utilities.AddGear as AddGear

class GearAdderApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.master.title("Gear Logger")
        
        # Gear type selection
        ttk.Label(self, text="Gear Type:").grid(row=0, column=0, padx=5, pady=5)
        self.gear_type = ttk.Combobox(self, values=["Mask", "Suit", "Gloves", "Boots"])
        self.gear_type.grid(row=0, column=1, padx=5, pady=5)
        self.gear_type.bind('<<ComboboxSelected>>', self.update_fields)
        
        # Common fields
        ttk.Label(self, text="Name:").grid(row=1, column=0, padx=5, pady=5)
        self.name_entry = ttk.Entry(self)
        self.name_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(self, text="Description:").grid(row=2, column=0, padx=5, pady=5)
        self.desc_entry = ttk.Entry(self)
        self.desc_entry.grid(row=2, column=1, padx=5, pady=5)
        
        self.is_rental = tk.BooleanVar()
        ttk.Checkbutton(self, text="Rental Gear", variable=self.is_rental).grid(row=3, column=0, columnspan=2, pady=5)
        
        # Variable fields (shown/hidden based on gear type)
        self.thickness_frame = ttk.Frame(self)
        ttk.Label(self.thickness_frame, text="Thickness (mm):").grid(row=0, column=0, padx=5, pady=5)
        self.thickness_entry = ttk.Entry(self.thickness_frame)
        self.thickness_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.size_frame = ttk.Frame(self)
        ttk.Label(self.size_frame, text="Size:").grid(row=0, column=0, padx=5, pady=5)
        self.size_entry = ttk.Entry(self.size_frame)
        self.glove_size = ttk.Combobox(self.size_frame, values=["S", "M", "L", "XL"])
        
        # File selection
        ttk.Label(self, text="Save Location:").grid(row=7, column=0, padx=5, pady=5)
        self.path_entry = ttk.Entry(self)
        self.path_entry.grid(row=7, column=1, padx=5, pady=5)
        ttk.Button(self, text="Browse", command=self.browse_location).grid(row=7, column=2, padx=5, pady=5)
        
        ttk.Label(self, text="File Name:").grid(row=8, column=0, padx=5, pady=5)
        self.filename_entry = ttk.Entry(self)
        self.filename_entry.grid(row=8, column=1, padx=5, pady=5)
        ttk.Label(self, text=".pickle").grid(row=8, column=2, padx=5, pady=5)
        
        # Save button
        ttk.Button(self, text="Save", command=self.save_gear).grid(row=9, column=0, columnspan=3, pady=20)
        
        self.grid(padx=10, pady=10)

    def update_fields(self, event=None):
        # Hide all variable fields first
        self.thickness_frame.grid_remove()
        self.size_frame.grid_remove()
        self.size_entry.grid_remove()
        self.glove_size.grid_remove()
        
        gear_type = self.gear_type.get()
        
        if gear_type in ["Suit", "Gloves", "Boots"]:
            self.thickness_frame.grid(row=6, column=0, columnspan=2)
            self.size_frame.grid(row=6, column=1, columnspan=2)
            
            if gear_type == "Gloves":
                self.glove_size.grid(row=0, column=1, padx=5, pady=5)
            else:
                self.size_entry.grid(row=0, column=1, padx=5, pady=5)

    def browse_location(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)

    def save_gear(self):
        gear_type = self.gear_type.get()
        if not gear_type or not self.filename_entry.get() or not self.path_entry.get():
            return
            
        output_path = Path(self.path_entry.get()) / f"{self.filename_entry.get()}.pickle"
        
        common_args = {
            "name": self.name_entry.get(),
            "output_path": str(output_path),
            "number_of_dives": 0,
            "total_dive_time": 0,
            "description": self.desc_entry.get() or None,
            "is_rental": self.is_rental.get()
        }
        
        if gear_type == "Mask":
            AddGear.add_mask(**common_args)
        else:
            thickness = int(self.thickness_entry.get())
            if gear_type == "Gloves":
                size = Gear.GloveSize[self.glove_size.get()]
            else:
                size = int(self.size_entry.get())
                
            if gear_type == "Suit":
                AddGear.add_suit(thickness=thickness, size=size, **common_args)
            elif gear_type == "Gloves":
                AddGear.add_gloves(thickness=thickness, size=size, **common_args)
            elif gear_type == "Boots":
                AddGear.add_boots(thickness=thickness, size=size, **common_args)
        
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GearAdderApp(root)
    root.mainloop()
