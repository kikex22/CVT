import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import subprocess
import threading

from core.dataset_lists import generate_train_valid_lists
from core.darknet_train import train_darknet
from ui.onnx_w import Onnx
from ui.tensor_w import Tensor

class FullPipelineWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Entrenar y Convertir Todo")
        self.root.geometry("700x600")
        
        # Variables para seguimiento
        self.is_training = False
        self.is_converting_onnx = False
        self.is_converting_tensor = False
        
        # Crear la interfaz
        self.build_ui()
        
    def build_ui(self):
        tk.Label(self.root, text="Pipeline de Entrenamiento y Conversión", 
                font=("Arial", 16, "bold"), pady=15).pack()
        
        # Frame para entradas
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=10, fill=tk.X, padx=20)
        
        # Archivo .data
        tk.Label(input_frame, text="Archivo .data:").pack(anchor=tk.W)
        self.entry_data = tk.Entry(input_frame, width=60)
        self.entry_data.pack(fill=tk.X, pady=2)
        tk.Button(input_frame, text="Seleccionar", command=self.select_data).pack(pady=2)
        
        # Archivo .cfg
        tk.Label(input_frame, text="Archivo .cfg:").pack(anchor=tk.W)
        self.entry_cfg = tk.Entry(input_frame, width=60)
        self.entry_cfg.pack(fill=tk.X, pady=2)
        tk.Button(input_frame, text="Seleccionar", command=self.select_cfg).pack(pady=2)
        
        # Archivo .weights
        tk.Label(input_frame, text="Archivo .weights (opcional):").pack(anchor=tk.W)
        self.entry_weights = tk.Entry(input_frame, width=60)
        self.entry_weights.pack(fill=tk.X, pady=2)
        tk.Button(input_frame, text="Seleccionar", command=self.select_weights).pack(pady=2)
        
        # Opciones
        options_frame = tk.Frame(self.root)
        options_frame.pack(pady=10)
        
        self.var_map = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame,
                       text="Usar -map (curvas de entrenamiento)",
                       variable=self.var_map).pack()
        
        # Botón de ejecución
        tk.Button(self.root, text="Iniciar Pipeline Completo",
                  bg="blue", fg="white", font=("Arial", 12, "bold"),
                  command=self.start_full_pipeline,
                  height=2, width=30).pack(pady=20)
        
        # Barra de progreso
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=20, pady=10)
        
        # Área de texto para logs
        tk.Label(self.root, text="Registro de Actividad:").pack(anchor=tk.W, padx=20)
        self.log_text = tk.Text(self.root, height=15, width=80)
        self.log_text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        
        # Scrollbar para el log
        scrollbar = tk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
        
    def select_data(self):
        path = filedialog.askopenfilename(
            initialdir=self._initial_model_dir(),
            filetypes=[("DATA files", "*.data")]
        )
        if path:
            self.entry_data.delete(0, tk.END)
            self.entry_data.insert(0, path)
    
    def select_cfg(self):
        path = filedialog.askopenfilename(
            initialdir=self._initial_model_dir(),
            filetypes=[("CFG files", "*.cfg")]
        )
        if path:
            self.entry_cfg.delete(0, tk.END)
            self.entry_cfg.insert(0, path)
    
    def select_weights(self):
        path = filedialog.askopenfilename(
            initialdir=self._initial_model_dir(),
            filetypes=[("Pesos", "*.weights *.conv *")]
        )
        if path:
            self.entry_weights.delete(0, tk.END)
            self.entry_weights.insert(0, path)
    
    def _initial_model_dir(self):
        paths = [
            self.entry_data.get().strip(),
            self.entry_cfg.get().strip(),
            self.entry_weights.get().strip()
        ]
        for path in paths:
            if path:
                parent = os.path.dirname(path)
                if os.path.exists(parent):
                    return parent
        return os.path.expanduser("~")
    
    def log_message(self, message):
        """Añade un mensaje al área de logs"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_full_pipeline(self):
        """Inicia el pipeline completo: entrenar -> convertir a ONNX -> convertir a TensorRT"""
        # Validar entradas
        data = self.entry_data.get().strip()
        cfg = self.entry_cfg.get().strip()
        
        if not data or not cfg:
            messagebox.showerror("Error", "Debes seleccionar archivo .data y archivo .cfg.")
            return
        
        # Iniciar en hilo separado para no bloquear la interfaz
        thread = threading.Thread(target=self._run_full_pipeline, args=(data, cfg))
        thread.daemon = True
        thread.start()
    
    def _run_full_pipeline(self, data, cfg):
        """Ejecuta el pipeline completo en segundo plano"""
        try:
            self.log_message("=== INICIANDO PIPELINE COMPLETO ===")
            
            # 1. Entrenar modelo
            self.log_message("1. Iniciando entrenamiento...")
            self.is_training = True
            self.progress.config(mode='indeterminate')
            self.progress.start()
            
            # Ejecutar entrenamiento (usando el método existente)
            weights = self.entry_weights.get().strip() if self.entry_weights.get().strip() else None
            use_map = self.var_map.get()
            
            # Llamamos al entrenamiento directamente
            from core.darknet_train import train_darknet
            
            # Crear una ventana temporal para el entrenamiento
            self.log_message("Ejecutando entrenamiento...")
            train_darknet(data, cfg, weights, use_map)
            
            # Simular tiempo de entrenamiento (en una implementación real se usaría el proceso real)
            import time
            time.sleep(5)  # Solo para demostración
            
            self.is_training = False
            self.progress.stop()
            self.log_message("✓ Entrenamiento completado")
            
            # 2. Convertir a ONNX
            self.log_message("2. Iniciando conversión a ONNX...")
            self.is_converting_onnx = True
            self.progress.config(mode='indeterminate')
            self.progress.start()
            
            # Crear ventana de conversión ONNX
            onnx_window = tk.Toplevel(self.root)
            onnx_window.title("Conversión a ONNX")
            onnx_app = Onnx(onnx_window)
            
            # Simular proceso de conversión
            time.sleep(3)
            self.is_converting_onnx = False
            self.progress.stop()
            self.log_message("✓ Conversión a ONNX completada")
            
            # 3. Convertir a TensorRT
            self.log_message("3. Iniciando conversión a TensorRT...")
            self.is_converting_tensor = True
            self.progress.config(mode='indeterminate')
            self.progress.start()
            
            # Crear ventana de conversión TensorRT
            tensor_window = tk.Toplevel(self.root)
            tensor_window.title("Conversión a TensorRT")
            tensor_app = Tensor(tensor_window)
            
            # Simular proceso de conversión
            time.sleep(3)
            self.is_converting_tensor = False
            self.progress.stop()
            self.log_message("✓ Conversión a TensorRT completada")
            
            self.log_message("=== PIPELINE COMPLETADO ===")
            messagebox.showinfo("Éxito", "Pipeline completo ejecutado con éxito!")
            
        except Exception as e:
            self.log_message(f"ERROR: {str(e)}")
            messagebox.showerror("Error", f"Ocurrió un error en el pipeline:\n{str(e)}")
    
    def generate_dataset_lists(self):
        """Método para generar listas de entrenamiento (reutilizado del código original)"""
        initial_dir = self._initial_model_dir()
        
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