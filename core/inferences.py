import os
from tkinter import messagebox

from core.command_runner import run_command
from core.paths import darknet_infer_bin


def infer_single_image(data, cfg, weights, image):
    darknet_bin = darknet_infer_bin()

    print(">> infer_single_image() llamado")
    print("DATA:", data)
    print("CFG:", cfg)
    print("WEIGHTS:", weights)
    print("IMAGE:", image)

    # Validaciones
    if not os.path.exists(darknet_bin):
        messagebox.showerror(
            "Error",
            "No existe DARKNET:\n"
            f"{darknet_bin}\n\n"
            "Puedes ajustar CVT_DARKNET_INFER_BIN o CVT_DARKNET_BIN."
        )
        return

    if not os.path.exists(data):
        messagebox.showerror("Error", f"No existe .data:\n{data}")
        return

    if not os.path.exists(cfg):
        messagebox.showerror("Error", f"No existe .cfg:\n{cfg}")
        return

    if not os.path.exists(weights):
        messagebox.showerror("Error", f"No existe .weights:\n{weights}")
        return

    if not os.path.exists(image):
        messagebox.showerror("Error", f"La imagen no existe:\n{image}")
        return

    # Comando Darknet detector test
    cmd = (
        f'"{darknet_bin}" detector test '
        f'"{data}" "{cfg}" "{weights}" "{image}" '
        f'-thresh 0.25'
    )

    print("CMD:", cmd)

    # Ejecutar inferencia y abrir predictions.jpg si el sistema lo permite.
    run_command(
        command=f"{cmd}; xdg-open predictions.jpg",
        title="single_image_inference",
        done_message="Inferencia lista",
    )
