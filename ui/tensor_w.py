import tkinter as tk
from tkinter import filedialog,messagebox
import os
from core.paths import default_cv_dir, existing_parent_or_default
from core.tensor import Trt

class Tensor:
    def __init__(self,root):
        self.root=root
        self.root.title("Convert to Tensorrt")
        self.root.geometry("600x400")

        self.entry_onnx= None
        self.entry_engine = None
        self.entry_workspace = None
        self.var_precision = tk.StringVar(value="fp16")  # fp32 | fp16 | int8


        self.build_ui()

    def build_ui(self):
        tk.Label(
            self.root,
            text="Convert to Tensorrt",
            font=("Arial", 16, "bold"),
            pady=15
        ).pack()

        tk.Label(self.root, text="Archivo .onnx:").pack()
        self.entry_onnx = tk.Entry(self.root, width=60)
        self.entry_onnx.pack()
        tk.Button(
            self.root,
            text="Seleccionar",
            command=self.select_onnx
        ).pack(pady=3)
        
        #engine
        tk.Label(self.root, text="Archivo de salida .engine:").pack()
        self.entry_engine = tk.Entry(self.root, width=60)
        self.entry_engine.pack()
        tk.Button(
            self.root,
            text="Cambiar destino",
            command=self.select_engine
        ).pack(pady=3)

        # -------- PRECISIÓN --------
        tk.Label(self.root, text="Precisión:").pack(pady=(10, 0))

        tk.Radiobutton(
            self.root,
            text="FP32 (máxima compatibilidad)",
            variable=self.var_precision,
            value="fp32"
        ).pack(anchor="w", padx=120)

        tk.Radiobutton(
            self.root,
            text="FP16 (recomendado)",
            variable=self.var_precision,
            value="fp16"
        ).pack(anchor="w", padx=120)

        tk.Radiobutton(
            self.root,
            text="INT8 (requiere calibración)",
            variable=self.var_precision,
            value="int8"
        ).pack(anchor="w", padx=120)


        # -------- WORKSPACE --------
        tk.Label(self.root, text="Workspace (MiB):").pack()
        self.entry_workspace = tk.Entry(self.root, width=10)
        self.entry_workspace.insert(0, "4096")
        self.entry_workspace.pack()

        # -------- CONVERT --------
        tk.Button(
            self.root,
            text="Convertir a TensorRT",
            bg="green",
            fg="white",
            command=self.convert
        ).pack(pady=20)

    #selectores

    def select_onnx(self):
        path = filedialog.askopenfilename(
            initialdir=default_cv_dir(),
            filetypes=[("ONNX files", "*.onnx")]
        )
        if not path:
            return

        self.entry_onnx.delete(0, tk.END)
        self.entry_onnx.insert(0, path)
        
        model_dir=os.path.dirname(path)
        base_name=os.path.splitext(os.path.basename(path))[0]
        default_engine=os.path.join(model_dir,f"{base_name}.engine")

        self.entry_engine.delete(0,tk.END)
        self.entry_engine.insert(0,default_engine)

    def select_engine(self):
        path = filedialog.asksaveasfilename(
            initialdir=existing_parent_or_default(self.entry_onnx.get()),
            defaultextension=".engine",
            filetypes=[("TensorRT engine", "*.engine")],
            title="Guardar engine como..."
        )
        if not path:
            return

        self.entry_engine.delete(0, tk.END)
        self.entry_engine.insert(0, path)
    
    def convert(self):
        onnx = self.entry_onnx.get().strip()
        engine = self.entry_engine.get().strip()
        workspace = self.entry_workspace.get().strip()
        precision = self.var_precision.get()

        if not onnx or not engine or not workspace:
            messagebox.showerror("Error", "Todos los campos son obligatorios")
            return

        if not workspace.isdigit():
            messagebox.showerror("Error", "Workspace debe ser numérico (MiB)")
            return

        Trt(
            onnx_path=onnx,
            engine_path=engine,
            precision=precision,
            workspace=int(workspace),
            verbose=True
        )
