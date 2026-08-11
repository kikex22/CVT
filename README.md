# CVT

Computer Vision Tools para entrenar modelos Darknet, probar inferencias y convertir modelos a ONNX/TensorRT.

## Configuracion local

El codigo esta preparado para usarse en PC y laptop. Las rutas especificas de cada maquina van en:

```bash
config/local.json
```

Ese archivo no se sube al repo. Para crearlo:

```bash
cp config/local.example.json config/local.json
```

Edita las rutas si en la laptop no coinciden:

```json
{
  "computer_vision_dir": "~/Computer_Vision",
  "darknet_train_bin": "~/Documents/darknet/darknet",
  "darknet_infer_bin": "/usr/bin/darknet",
  "yolov4_project_dir": "~/Documents/pytorch-YOLOv4",
  "trtexec_bin": "/usr/bin/trtexec"
}
```

Tambien se pueden forzar rutas sin tocar el archivo:

```bash
CVT_CONFIG=/ruta/local.json python3 main.py
CVT_DARKNET_BIN=/ruta/darknet python3 main.py
CVT_YOLOV4_DIR=/ruta/pytorch-YOLOv4 python3 main.py
CVT_TRTEXEC_BIN=/ruta/trtexec python3 main.py
```

## Ejecutar

```bash
python3 main.py
```

En WSL puede que no exista una terminal grafica como `gnome-terminal`. En ese caso CVT ejecuta los comandos en segundo plano y guarda la salida en:

```bash
~/.cache/cvt/logs/
```
