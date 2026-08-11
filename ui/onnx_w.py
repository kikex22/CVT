import tkinter as tk
from tkinter import filedialog, messagebox
import os

from core.onnx import convert_to_onnx
from core.paths import (
    existing_parent_or_default,
    first_existing_parent_or_default,
)


class Onnx:
    def __init__(self, root):
        self.root = root
        self.root.title("Convert to ONNX")
        self.root.geometry("600x400")

        self.entry_cfg = None
        self.entry_weights = None
        self.entry_output = None
        self.entry_size = None

        self.build_ui()

    # ======================================================
    # UI
    # ======================================================
    def build_ui(self):
        tk.Label(
            self.root,
            text="Convert to ONNX",
            font=("Arial", 16, "bold"),
            pady=15
        ).pack()

        # -------- CFG --------
        tk.Label(self.root, text="Archivo .cfg:").pack()
        self.entry_cfg = tk.Entry(self.root, width=60)
        self.entry_cfg.pack()
        tk.Button(
            self.root,
            text="Seleccionar",
            command=self.select_cfg
        ).pack(pady=3)

        # -------- WEIGHTS --------
        tk.Label(self.root, text="Archivo .weights:").pack()
        self.entry_weights = tk.Entry(self.root, width=60)
        self.entry_weights.pack()
        tk.Button(
            self.root,
            text="Seleccionar",
            command=self.select_weights
        ).pack(pady=3)

        # -------- OUTPUT ONNX --------
        tk.Label(self.root, text="Archivo de salida .onnx:").pack()
        self.entry_output = tk.Entry(self.root, width=60)
        self.entry_output.pack()
        tk.Button(
            self.root,
            text="Cambiar destino",
            command=self.select_output
        ).pack(pady=3)

        # -------- INPUT SIZE --------
        tk.Label(self.root, text="Input size (ej: 416):").pack(pady=(10, 0))
        self.entry_size = tk.Entry(self.root, width=10)
        self.entry_size.insert(0, "416")
        self.entry_size.pack()

        # -------- CONVERT --------
        tk.Button(
            self.root,
            text="Convertir a ONNX",
            bg="green",
            fg="white",
            command=self.convert
        ).pack(pady=20)

    # ======================================================
    # Selectores
    # ======================================================
    def select_cfg(self):
        path = filedialog.askopenfilename(
            initialdir=first_existing_parent_or_default(
                self.entry_cfg.get(),
                self.entry_weights.get()
            ),
            filetypes=[("CFG files", "*.cfg")]
        )
        if not path:
            return

        self.entry_cfg.delete(0, tk.END)
        self.entry_cfg.insert(0, path)

        # 👉 Proponer ONNX en la MISMA carpeta del CFG
        cfg_dir = os.path.dirname(path)
        base_name = os.path.splitext(os.path.basename(path))[0]
        default_onnx = os.path.join(cfg_dir, f"{base_name}.onnx")

        self.entry_output.delete(0, tk.END)
        self.entry_output.insert(0, default_onnx)

    def select_weights(self):
        path = filedialog.askopenfilename(
            initialdir=first_existing_parent_or_default(
                self.entry_cfg.get(),
                self.entry_weights.get()
            ),
            filetypes=[("Weights files", "*.weights")]
        )
        if not path:
            return

        self.entry_weights.delete(0, tk.END)
        self.entry_weights.insert(0, path)

    def select_output(self):
        path = filedialog.asksaveasfilename(
            initialdir=existing_parent_or_default(self.entry_cfg.get()),
            defaultextension=".onnx",
            filetypes=[("ONNX model", "*.onnx")],
            title="Guardar modelo ONNX como..."
        )
        if not path:
            return

        self.entry_output.delete(0, tk.END)
        self.entry_output.insert(0, path)

    # ======================================================
    # Acción principal
    # ======================================================
    def convert(self):
        cfg = self.entry_cfg.get().strip()
        weights = self.entry_weights.get().strip()
        output = self.entry_output.get().strip()
        size = self.entry_size.get().strip()

        # -------- Validaciones --------
        if not cfg or not weights or not output or not size:
            messagebox.showerror("Error", "Todos los campos son obligatorios")
            return

        if not os.path.exists(cfg):
            messagebox.showerror("Error", f"CFG no existe:\n{cfg}")
            return

        if not os.path.exists(weights):
            messagebox.showerror("Error", f"WEIGHTS no existe:\n{weights}")
            return

        if not size.isdigit():
            messagebox.showerror(
                "Error",
                "Input size debe ser numérico (ej: 416)"
            )
            return

        # -------- CORE --------
        convert_to_onnx(
            cfg=cfg,
            weights=weights,
            output=output,
            input_size=int(size)
        )
