import tkinter as tk 
from ui.train_w import TrainWindow
from ui.inferences_w import Inferences
from ui.onnx_w import Onnx 
from ui.tensor_w import Tensor

class Menu():
    def __init__(self,root):
        self.root=root
        self.root.title("Computer Vision Tools")
        self.root.geometry("640x640")
        
        title_font= ("Arial",18, "bold")
        btn_font=("Arial",12)

        tk.Label(
            root,
            text="What are you looking for?",
            font=title_font,
            pady=20
        ).pack()

        #==Buttons==
        tk.Button(
            root,
            text="Train Darknet",
            width=25,
            height=2,
            font=btn_font,
            command=self.open_train,
            
        ).pack(pady=10)

        tk.Button(
            root,
            text="Test Darknet2",
            width=25,
            height=2,
            font=btn_font,
            command=self.test_models,
            
        ).pack(pady=10)

        tk.Button(
            root,
            text="Convert to Onnx",
            width=25,
            height=2,
            font=btn_font,
            command=self.convert_models_onnx,
            
        ).pack(pady=10)

        tk.Button(
            root,
            text="Convert to Tensorrt",
            width=25,
            height=2,
            font=btn_font,
            command=self.convert_models_tensor,
            
        ).pack(pady=10)

        

    def open_train(self):
        TrainWindow(tk.Toplevel(self.root))
    
    def test_models(self):
        Inferences(tk.Toplevel(self.root))

    def convert_models_onnx(self):
        Onnx(tk.Toplevel(self.root))
        

    def convert_models_tensor(self):
        Tensor(tk.Toplevel(self.root))
        pass