import subprocess
import os
from tkinter import messagebox

from core.paths import export_onnx_script, yolov4_venv_activate


def convert_to_onnx(cfg, weights, output, input_size):
    """
    Convierte un modelo Darknet a ONNX usando export_onnx.py
    dentro del venv correcto.
    """
    onnx_script = export_onnx_script()
    venv_activate = yolov4_venv_activate()

    # Validaciones
    if not os.path.exists(onnx_script):
        messagebox.showerror(
            "Error",
            "No existe export_onnx.py:\n"
            f"{onnx_script}\n\n"
            "Puedes ajustar CVT_YOLOV4_DIR."
        )
        return

    if not os.path.exists(venv_activate):
        messagebox.showerror(
            "Error",
            "No existe el venv:\n"
            f"{venv_activate}\n\n"
            "Puedes ajustar CVT_YOLOV4_DIR."
        )
        return

    if not os.path.exists(cfg):
        messagebox.showerror("Error", f"CFG no existe:\n{cfg}")
        return

    if not os.path.exists(weights):
        messagebox.showerror("Error", f"WEIGHTS no existe:\n{weights}")
        return

    out_dir = os.path.dirname(output)
    if out_dir and not os.path.exists(out_dir):
        messagebox.showerror("Error", f"Carpeta de salida no existe:\n{out_dir}")
        return

    # Comando con activación de venv
    cmd = (
        f'source "{venv_activate}" && '
        f'python "{onnx_script}" '
        f'--cfg "{cfg}" '
        f'--weights "{weights}" '
        f'--output "{output}" '
        f'--input_size {input_size}'
    )

    print("Ejecutando con venv:", cmd)

    # Ejecutar en GNOME Terminal
    subprocess.Popen([
        "gnome-terminal",
        "--",
        "bash",
        "-c",
        f'{cmd}; echo ""; echo "Conversión ONNX finalizada"; exec bash'
    ])
