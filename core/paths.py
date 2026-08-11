import json
import os
import shutil
import socket
from functools import lru_cache
from pathlib import Path


COMPUTER_VISION_DIR = Path.home() / "Computer_Vision"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


CONFIG_ALIASES = {
    "darknet_train_bin": ["darknet_train_bin", "darknet_bin"],
    "darknet_infer_bin": ["darknet_infer_bin", "darknet_bin"],
}


def current_device():
    configured_device = os.environ.get("CVT_DEVICE", "").strip().lower()
    aliases = {
        "desktop": "pc",
        "computer": "pc",
        "notebook": "laptop",
    }
    if configured_device:
        return aliases.get(configured_device, configured_device)

    hostname = socket.gethostname().strip().lower()
    if "laptop" in hostname or "notebook" in hostname:
        return "laptop"

    try:
        proc_version = Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        proc_version = ""

    if "microsoft" in proc_version or "wsl" in proc_version:
        return "laptop"

    return "pc"


def _profiles():
    home = Path.home()
    common_system_bins = {
        "darknet_infer_bin": [
            Path("/usr/bin/darknet"),
            home / "Documents" / "darknet" / "darknet",
            home / "documents" / "darknet" / "darknet",
            shutil.which("darknet"),
        ],
        "trtexec_bin": [
            Path("/usr/bin/trtexec"),
            Path("/usr/src/tensorrt/bin/trtexec"),
            Path("/usr/local/tensorrt/bin/trtexec"),
            shutil.which("trtexec"),
        ],
    }

    return {
        "pc": {
            "computer_vision_dir": [
                home / "Computer_Vision",
                home / "documents",
                home / "Documents" / "Computer_Vision",
            ],
            "darknet_train_bin": [
                home / "Documents" / "darknet" / "darknet",
                home / "documents" / "darknet" / "darknet",
                Path("/usr/bin/darknet"),
                shutil.which("darknet"),
            ],
            "yolov4_project_dir": [
                home / "Documents" / "pytorch-YOLOv4",
                home / "documents" / "pytorch-YOLOv4",
                home / "pytorch-YOLOv4",
                home / "Computer_Vision" / "pytorch-YOLOv4",
            ],
            **common_system_bins,
        },
        "laptop": {
            "computer_vision_dir": [
                home / "Computer_Vision",
                home / "documents",
                home / "Documents" / "Computer_Vision",
            ],
            "darknet_train_bin": [
                home / "documents" / "darknet" / "darknet",
                home / "Documents" / "darknet" / "darknet",
                Path("/usr/bin/darknet"),
                shutil.which("darknet"),
            ],
            "yolov4_project_dir": [
                home / "documents" / "pytorch-YOLOv4",
                home / "Documents" / "pytorch-YOLOv4",
                home / "pytorch-YOLOv4",
                home / "Computer_Vision" / "pytorch-YOLOv4",
            ],
            **common_system_bins,
        },
    }


def _device_candidates(name):
    profiles = _profiles()
    profile = profiles.get(current_device(), profiles["pc"])
    return profile.get(name, [])


@lru_cache(maxsize=1)
def _local_config():
    config_paths = []
    configured_path = os.environ.get("CVT_CONFIG", "").strip()
    if configured_path:
        config_paths.append(Path(configured_path).expanduser())

    config_paths.append(PROJECT_ROOT / "config" / "local.json")

    for config_path in config_paths:
        if not config_path.is_file():
            continue

        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[CVT_CONFIG] No pude leer {config_path}: {exc}")
            return {}

        if isinstance(config, dict):
            print(f"[CVT_CONFIG] Config local cargada: {config_path}")
            return config

        print(f"[CVT_CONFIG] Config ignorada, debe ser un objeto JSON: {config_path}")
        return {}

    return {}


def _local_config_candidates(name):
    config = _local_config()
    for key in CONFIG_ALIASES.get(name, [name]):
        value = config.get(key)
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return value
    return []


def _first_existing(candidates):
    expanded = [
        Path(candidate).expanduser()
        for candidate in candidates
        if candidate
    ]

    for candidate in expanded:
        if candidate.exists():
            return candidate

    return expanded[0] if expanded else Path.home()


def _resolve_path(name, *env_vars):
    for env_var in env_vars:
        configured_path = os.environ.get(env_var, "").strip()
        if configured_path:
            return Path(configured_path).expanduser()

    local_candidates = _local_config_candidates(name)
    if local_candidates:
        return _first_existing(local_candidates)

    return _first_existing(_device_candidates(name))


def darknet_train_bin():
    return str(_resolve_path(
        "darknet_train_bin",
        "CVT_DARKNET_TRAIN_BIN",
        "CVT_DARKNET_BIN",
    ))


def darknet_infer_bin():
    return str(_resolve_path(
        "darknet_infer_bin",
        "CVT_DARKNET_INFER_BIN",
        "CVT_DARKNET_BIN",
    ))


def trtexec_bin():
    return str(_resolve_path("trtexec_bin", "CVT_TRTEXEC_BIN"))


def yolov4_project_dir():
    return _resolve_path("yolov4_project_dir", "CVT_YOLOV4_DIR")


def export_onnx_script():
    return str(yolov4_project_dir() / "export_onnx.py")


def yolov4_venv_activate():
    return str(yolov4_project_dir() / "venv" / "bin" / "activate")


def default_cv_dir():
    configured_dir = os.environ.get("CVT_COMPUTER_VISION_DIR", "").strip()
    if configured_dir:
        return str(Path(configured_dir).expanduser())

    cv_dir = _first_existing(
        _local_config_candidates("computer_vision_dir")
        or _device_candidates("computer_vision_dir")
    )
    if cv_dir.is_dir():
        return str(cv_dir)
    return str(Path.home())


def existing_parent_or_default(path):
    if path:
        parent = Path(path).expanduser().parent
        if parent.is_dir():
            return str(parent)
    return default_cv_dir()


def first_existing_parent_or_default(*paths):
    for path in paths:
        if path:
            parent = Path(path).expanduser().parent
            if parent.is_dir():
                return str(parent)
    return default_cv_dir()
