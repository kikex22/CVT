import tkinter as tk
from tkinter import filedialog, messagebox, ttk
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

        run = Trt(
            onnx_path=onnx,
            engine_path=engine,
            precision=precision,
            workspace=int(workspace),
            verbose=True,
            show_background_message=False,
        )

        if run and run.log_path and not run.opened_terminal:
            self.show_tensorrt_monitor(run, engine)

    def show_tensorrt_monitor(self, run, engine_path):
        monitor = tk.Toplevel(self.root)
        monitor.title("TensorRT")
        monitor.geometry("760x440")

        status_var = tk.StringVar(value="Compilando TensorRT...")
        tk.Label(
            monitor,
            textvariable=status_var,
            font=("Arial", 13, "bold"),
            pady=10
        ).pack()

        progress = ttk.Progressbar(monitor, mode="indeterminate")
        progress.pack(fill=tk.X, padx=16, pady=(0, 10))
        progress.start(10)

        tk.Label(monitor, text=f"Log: {run.log_path}").pack(anchor="w", padx=16)

        log_text = tk.Text(monitor, height=16, width=90)
        log_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=10)

        scrollbar = tk.Scrollbar(log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=log_text.yview)

        close_button = tk.Button(
            monitor,
            text="Cerrar",
            command=monitor.destroy,
            state=tk.DISABLED,
        )
        close_button.pack(pady=(0, 12))

        last_pos = [0]

        def append_log():
            try:
                with open(run.log_path, "r", encoding="utf-8", errors="replace") as log_file:
                    log_file.seek(last_pos[0])
                    chunk = log_file.read()
                    last_pos[0] = log_file.tell()
            except OSError:
                chunk = ""

            if chunk:
                log_text.insert(tk.END, chunk)
                log_text.see(tk.END)

        def poll():
            if not monitor.winfo_exists():
                return

            append_log()
            exit_code = run.process.poll()

            if exit_code is None:
                monitor.after(1000, poll)
                return

            progress.stop()
            close_button.config(state=tk.NORMAL)

            if exit_code == 0 and os.path.exists(engine_path):
                status_var.set("TensorRT ENGINE generado")
                messagebox.showinfo("TensorRT", f"ENGINE generado:\n{engine_path}")
            else:
                status_var.set(f"TensorRT termino con error ({exit_code})")
                messagebox.showerror(
                    "TensorRT",
                    "La conversion termino con error.\n\n"
                    f"Log:\n{run.log_path}"
                )

        poll()
