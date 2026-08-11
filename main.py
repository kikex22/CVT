import tkinter as tk
from ui.menu import Menu

if __name__ == "__main__":
    root = tk.Tk()

    app = Menu(root)
    root.mainloop()
