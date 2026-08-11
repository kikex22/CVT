from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def generate_image_list(folder, output_name):
    image_dir = Path(folder).expanduser().resolve()
    if not image_dir.is_dir():
        raise ValueError(f"Carpeta invalida:\n{image_dir}")

    images = sorted(
        path.resolve()
        for path in image_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not images:
        raise ValueError(f"No encontre imagenes .jpg/.jpeg/.png en:\n{image_dir}")

    output_path = image_dir.parent / output_name
    output_path.write_text(
        "".join(f"{path}\n" for path in images),
        encoding="utf-8"
    )

    return output_path, len(images)


def generate_train_valid_lists(train_dir, valid_dir):
    train_path, train_count = generate_image_list(train_dir, "train.txt")
    valid_path, valid_count = generate_image_list(valid_dir, "valid.txt")

    return {
        "train": (train_path, train_count),
        "valid": (valid_path, valid_count),
    }
