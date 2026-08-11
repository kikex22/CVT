import subprocess
import os
from tkinter import messagebox

from core.paths import darknet_train_bin

def train_darknet(data, cfg, weights=None, use_map=True):
    darknet_bin = darknet_train_bin()

    # Validar que exista Darknet
    if not os.path.exists(darknet_bin):
        messagebox.showerror(
            "Error",
            "No existe el ejecutable DARKNET:\n"
            f"{darknet_bin}\n\n"
            "Puedes ajustar CVT_DARKNET_TRAIN_BIN o CVT_DARKNET_BIN."
        )
        return

    # Validar data y cfg
    if not data or not cfg:
        messagebox.showerror("Error", "Debes seleccionar archivo .data y archivo .cfg.")
        return

    # Construir comando Darknet
    cmd = f'"{darknet_bin}" detector train "{data}" "{cfg}"'

    if weights:
        cmd += f' "{weights}"'

    if use_map:
        cmd += " -map"

    print("Ejecutando:", cmd)

    messagebox.showinfo("Entrenando", "Ejecutando entrenamiento en GNOME Terminal...")

    subprocess.Popen([
        "gnome-terminal",
        "--",
        "bash",
        "-c",
        f"{cmd}; echo ''; echo 'Entrenamiento finalizado'; exec bash"
    ])
