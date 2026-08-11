import os
from tkinter import messagebox

from core.command_runner import run_command
from core.paths import trtexec_bin


def Trt(
    onnx_path,
    engine_path,
    precision="fp16",   # fp32 | fp16 | int8
    workspace=4096,
    verbose=True,
    show_background_message=True,
):
    trtexec = trtexec_bin()

    if not os.path.exists(trtexec):
        messagebox.showerror(
            "Error",
            "No existe trtexec:\n"
            f"{trtexec}\n\n"
            "Puedes ajustar CVT_TRTEXEC_BIN."
        )
        return

    if not os.path.exists(onnx_path):
        messagebox.showerror("Error", f"ONNX no existe:\n{onnx_path}")
        return

    out_dir = os.path.dirname(engine_path)
    if out_dir and not os.path.exists(out_dir):
        messagebox.showerror("Error", f"Carpeta de salida no existe:\n{out_dir}")
        return

    cmd = (
        f'"{trtexec}" '
        f'--onnx="{onnx_path}" '
        f'--saveEngine="{engine_path}" '
        f'--memPoolSize=workspace:{workspace} '
    )

    # -------- PRECISIÓN --------
    if precision == "fp16":
        cmd += "--fp16 "
    elif precision == "int8":
        messagebox.showwarning(
            "INT8",
            "INT8 requiere calibración.\n"
            "Si no usas calibrador, el engine puede fallar."
        )
        cmd += "--int8 "
    # fp32 → no se añade ningún flag

    if verbose:
        cmd += "--verbose "

    print("Ejecutando:", cmd)

    return run_command(
        command=cmd,
        title="tensorrt_conversion",
        done_message="TensorRT ENGINE generado",
        show_background_message=show_background_message,
    )
