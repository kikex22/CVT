import tkinter as tk
from tkinter import filedialog
from core.paths import default_cv_dir, first_existing_parent_or_default
from core.inferences import infer_single_image 
from core.inferences_folder import infer_folder



class Inferences:
    def __init__(self, root):
        self.root = root
        self.root.title("Model Testing")
        self.root.geometry("600x400")

        # Frame dinámico
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

        # Campos (widgets que van a ser destruidos)
        self.entry_data = None
        self.entry_cfg = None
        self.entry_weights = None

        # Variables permanentes (NO dependen de widgets)
        self.model_data_path = None
        self.model_cfg_path = None
        self.model_weights_path = None

        # Primera pantalla
        self.build_select_model_ui()


    # ---------------------------------------------------------
    # PANTALLA 1
    # ---------------------------------------------------------
    def build_select_model_ui(self):
        self.clear_frame()

        tk.Label(self.frame, text="Testing Models Window",
                 font=("Arial", 16, "bold"), pady=15).pack()

        # ---- DATA ----
        tk.Label(self.frame, text="Archivo .data:").pack()
        self.entry_data = tk.Entry(self.frame, width=60)
        self.entry_data.pack()
        tk.Button(self.frame, text="Seleccionar",
                  command=self.select_data).pack(pady=3)

        # ---- CFG ----
        tk.Label(self.frame, text="Archivo .cfg:").pack()
        self.entry_cfg = tk.Entry(self.frame, width=60)
        self.entry_cfg.pack()
        tk.Button(self.frame, text="Seleccionar",
                  command=self.select_cfg).pack(pady=3)

        # ---- WEIGHTS ----
        tk.Label(self.frame, text="Archivo .weights/conv:").pack()
        self.entry_weights = tk.Entry(self.frame, width=60)
        self.entry_weights.pack()
        tk.Button(self.frame, text="Seleccionar",
                  command=self.select_weights).pack(pady=3)

        # Next button → guardar paths antes de destruir widgets
        tk.Button(self.frame, text="Next",
                  bg="green", fg="white",
                  command=self.save_model_and_next).pack(pady=20)


    # ---------------------------------------------------------
    # Guardar paths antes de borrar widgets
    # ---------------------------------------------------------
    def save_model_and_next(self):
        self.model_data_path = self.entry_data.get().strip()
        self.model_cfg_path = self.entry_cfg.get().strip()
        self.model_weights_path = self.entry_weights.get().strip()

        self.build_select_input_ui()


    # ---------------------------------------------------------
    # PANTALLA 2
    # ---------------------------------------------------------
    def build_select_input_ui(self):
        self.clear_frame()

        tk.Label(self.frame, text="Select Input Type",
                 font=("Arial", 16, "bold"), pady=15).pack()

        tk.Button(self.frame, text="Single Photo",
                  width=20, height=2,
                  command=self.choose_photo).pack(pady=10)

        tk.Button(self.frame, text="Folder of Images",
                  width=20, height=2,
                  command=self.choose_folder).pack(pady=10)

        tk.Button(self.frame, text="← Back",
                  command=self.build_select_model_ui).pack(pady=20)


    # ---------------------------------------------------------
    # PROCESAR UNA FOTO
    # ---------------------------------------------------------
    def choose_photo(self):
        path = filedialog.askopenfilename(
            initialdir=default_cv_dir(),
            filetypes=[
                ("Images", ("*.jpg", "*.jpeg", "*.png")),
                ("All files", "*.*")
            ]
        )

        if not path:
            return

        # LLAMAR AL CORE (Darknet inferencia) — YA NO SE USA entry_*
        infer_single_image(
            self.model_data_path,
            self.model_cfg_path,
            self.model_weights_path,
            path
        )


    # ---------------------------------------------------------
    # PROCESAR CARPETA
    # ---------------------------------------------------------
    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=default_cv_dir())
        if not folder:
            return
        
        infer_folder(
            self.model_data_path,
            self.model_cfg_path,
            self.model_weights_path,
            folder,
            delay=3

        )


    # ---------------------------------------------------------
    # Selectores
    # ---------------------------------------------------------
    def select_data(self):
        path = filedialog.askopenfilename(
            initialdir=self._initial_model_dir(
                self.entry_data,
                self.entry_cfg,
                self.entry_weights
            ),
            filetypes=[("DATA files", "*.data")])
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
            self.entry_cfg.delete(0, tk.END)
            self.entry_cfg.insert(0, path)

    def select_weights(self):
        path = filedialog.askopenfilename(
            initialdir=self._initial_model_dir(
                self.entry_cfg,
                self.entry_data,
                self.entry_weights
            ),
            filetypes=[
                ("Pesos", ("*.weights", "*.conv")),
                ("Todos", "*.*")]
        )
        if path:
            self.entry_weights.delete(0, tk.END)
            self.entry_weights.insert(0, path)


    # ---------------------------------------------------------
    # UTIL: limpiar frame
    # ---------------------------------------------------------
    def clear_frame(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

    def _initial_model_dir(self, *entries):
        paths = [
            entry.get().strip()
            for entry in entries
            if entry is not None
        ]
        return first_existing_parent_or_default(*paths)
