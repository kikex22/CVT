import os
from tkinter import messagebox

from core.command_runner import run_command
from core.paths import darknet_infer_bin


def infer_folder(data, cfg, weights, folder_path, delay=1):
    darknet_bin = darknet_infer_bin()

    # ==============================
    # VALIDACIONES
    # ==============================
    if not os.path.exists(darknet_bin):
        messagebox.showerror(
            "Error",
            "No existe DARKNET:\n"
            f"{darknet_bin}\n\n"
            "Puedes ajustar CVT_DARKNET_INFER_BIN o CVT_DARKNET_BIN."
        )
        return

    if not os.path.exists(data):
        messagebox.showerror("Error", f"Archivo .data no existe:\n{data}")
        return

    if not os.path.exists(cfg):
        messagebox.showerror("Error", f"Archivo .cfg no existe:\n{cfg}")
        return

    if not os.path.exists(weights):
        messagebox.showerror("Error", f"Archivo .weights no existe:\n{weights}")
        return

    if not os.path.isdir(folder_path):
        messagebox.showerror("Error", f"Carpeta inválida:\n{folder_path}")
        return

    valid_ext = (".jpg", ".jpeg", ".png")
    images = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_ext)]

    if not images:
        messagebox.showerror("Error", "No hay imágenes válidas en el folder.")
        return

    # Carpeta de salida
    output_dir = os.path.join(folder_path, "output")
    os.makedirs(output_dir, exist_ok=True)

    # ==============================
    # 1️⃣ Crear Script Bash Temporal
    # ==============================
    bash_script = os.path.join(folder_path, "batch_darknet.sh")

    with open(bash_script, "w") as f:
        f.write("#!/bin/bash\n\n")
        f.write('echo "Darknet Batch Processing iniciado..."\n\n')

        for img in images:
            img_path = os.path.join(folder_path, img)
            base, ext = os.path.splitext(img)
            pred_out = os.path.join(output_dir, f"{base}_pred{ext}")

            f.write(f'echo "Procesando: {img_path}"\n')

            # Ejecutar Darknet sin mostrar ventana
            f.write(
                f'"{darknet_bin}" detector test "{data}" "{cfg}" "{weights}" "{img_path}" '
                f'-thresh 0.25 -dont_show\n'
            )

            # Guardar predicción
            f.write(f'cp predictions.jpg "{pred_out}"\n\n')

        f.write('echo "Procesamiento completado."\n\n')

        # ==============================
        # 2️⃣ Mostrar slideshow con feh
        # ==============================
        f.write('echo "Mostrando imágenes detectadas (slideshow)..." \n')
        f.write(f'feh -F -D {delay} "{output_dir}"\n\n')

        f.write('echo "Secuencia finalizada."\n')

    # Hacer script ejecutable
    os.chmod(bash_script, 0o755)

    # ==============================
    # 3️⃣ Ejecutar todo en una sola terminal GNOME
    # ==============================
    run_command(
        command=f'"{bash_script}"',
        title="folder_inference",
        done_message="Batch Darknet finalizado",
    )

    return output_dir
