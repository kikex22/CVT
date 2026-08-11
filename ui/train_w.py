import tkinter as tk
from tkinter import filedialog, messagebox
import os

from core.dataset_lists import generate_train_valid_lists
from core.darknet_train import train_darknet
from core.paths import first_existing_parent_or_default


class TrainWindow:

    def __init__(self, root):
        self.root = root
        self.root.title("Train Darknet")
        self.root.geometry("600x400")

        # Variables
        self.var_map = tk.BooleanVar(value=True)

        # Campos
        self.entry_data = None
        self.entry_cfg = None
        self.entry_weights = None

        # Construir interfaz gráfica
        self.build_ui()

    # ==========================
    #   BUILD UI
    # ==========================
    def build_ui(self):
        tk.Label(self.root, text="Train Darknet Window",
                 font=("Arial", 16, "bold"), pady=15).pack()

        # ---- DATA ----
        tk.Label(self.root, text="Archivo .data:").pack()
        self.entry_data = tk.Entry(self.root, width=60)
        self.entry_data.pack()
        tk.Button(self.root, text="Seleccionar",
                  command=self.select_data).pack(pady=3)
        
        # -----CFG---
        tk.Label(self.root, text="Archivo .cfg:").pack()
        self.entry_cfg = tk.Entry(self.root, width=60)
        self.entry_cfg.pack()
        tk.Button(self.root, text="Seleccionar",
                  command=self.select_cfg).pack(pady=3)
        
        # ---pesos----
        tk.Label(self.root, text="Archivo .weights/conv:").pack()
        self.entry_weights = tk.Entry(self.root, width=60)
        self.entry_weights.pack()
        tk.Button(self.root, text="Seleccionar",
                  command=self.select_weights).pack(pady=3)

        

        # Opciones
        options_frame = tk.Frame(self.root)
        options_frame.pack(pady=10)

        tk.Checkbutton(options_frame,
                       text="Usar -map (curvas de entrenamiento)",
                       variable=self.var_map).pack(side=tk.LEFT, padx=6)

        tk.Button(options_frame,
                  text="Generar train.txt / valid.txt",
                  command=self.generate_dataset_lists).pack(side=tk.LEFT, padx=6)

        # Iniciar
        tk.Button(self.root, text="Iniciar Entrenamiento",
                  bg="green", fg="white",
                  command=self.start_training).pack(pady=20)

    # ==========================
    #   SELECTORES
    # ==========================
    def select_data(self):
        path = filedialog.askopenfilename(
            initialdir=self._initial_model_dir(
                self.entry_data,
                self.entry_cfg,
                self.entry_weights
            ),
            filetypes=[("DATA files", "*.data")]
        )
        if path:
            self.entry_data.delete(0, tk.END)
            self.entry_data.insert(0, path)

    def select_cfg(self):
        path = filedialog.askopenfilename(
            initialdir=self._initial_model_dir(
                self.entry_data,
                self.entry_cfg,
                self.entry_weights
            ),
            filetypes=[("CFG files", "*.cfg")]
        )
        if path:
            self.entry_cfg.delete(0,tk.END)
            self.entry_cfg.insert(0,path)
    
    def select_weights(self):
        path = filedialog.askopenfilename(
            initialdir=self._initial_model_dir(
                self.entry_cfg,
                self.entry_data,
                self.entry_weights
            ),
            filetypes=[("Pesos", "*.weights *.conv *")]
        )
        if path:
            self.entry_weights.delete(0,tk.END)
            self.entry_weights.insert(0,path)

    
    # ==========================
    #   EJECUTAR ENTRENAMIENTO
    # ==========================
    def start_training(self):
        data = self.entry_data.get().strip()
        cfg = self.entry_cfg.get().strip()
        weights = self.entry_weights.get().strip()
        use_map = self.var_map.get()

        # Llamamos a la función del CORE
        train_darknet(data, cfg, weights, use_map)

    def generate_dataset_lists(self):
        initial_dir = self._initial_dataset_dir()

        train_dir = filedialog.askdirectory(
            title="Selecciona la carpeta train",
            initialdir=initial_dir
        )
        if not train_dir:
            return

        valid_dir = filedialog.askdirectory(
            title="Selecciona la carpeta valid",
            initialdir=os.path.dirname(train_dir)
        )
        if not valid_dir:
            return

        try:
            result = generate_train_valid_lists(train_dir, valid_dir)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return
        except OSError as exc:
            messagebox.showerror("Error", f"No pude escribir los archivos:\n{exc}")
            return

        train_path, train_count = result["train"]
        valid_path, valid_count = result["valid"]

        messagebox.showinfo(
            "Listas generadas",
            "Archivos creados correctamente:\n\n"
            f"{train_path} ({train_count} imagenes)\n"
            f"{valid_path} ({valid_count} imagenes)"
        )

    def _initial_dataset_dir(self):
        return self._initial_model_dir(
            self.entry_data,
            self.entry_cfg,
            self.entry_weights
        )

    def _initial_model_dir(self, *entries):
        paths = [
            entry.get().strip()
            for entry in entries
            if entry is not None
        ]
        return first_existing_parent_or_default(*paths)
