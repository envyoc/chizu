import json
import os
import math
from PIL import Image

def load_palette(config_path="config.json"):
    with open(config_path) as f:
        config = json.load(f)
    palette = []
    for hex_color in config["palette"]:
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        palette.append(rgb)
    return palette

def closest_palette_index(pixel, palette):
    r, g, b = pixel[:3]
    return min(range(len(palette)), key=lambda i: math.sqrt(
        (r - palette[i][0])**2 +
        (g - palette[i][1])**2 +
        (b - palette[i][2])**2
    ))

def convert_image(filepath, palette):
    img = Image.open(filepath).convert("RGBA")
    indices = []
    for y in range(img.height):
        for x in range(img.width):
            pixel = img.getpixel((x, y))
            if pixel[3] == 0:
                indices.append(255)  # 255 = transparent
            else:
                indices.append(closest_palette_index(pixel, palette))
    return bytes(indices)

def convert_all(assets_dir="assets", output_dir="output/indexed"):
    palette = load_palette()
    os.makedirs(output_dir, exist_ok=True)

    for trait_folder in sorted(os.listdir(assets_dir)):
        folder_path = os.path.join(assets_dir, trait_folder)
        if not os.path.isdir(folder_path):
            continue
        out_folder = os.path.join(output_dir, trait_folder)
        os.makedirs(out_folder, exist_ok=True)
        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(".png"):
                continue
            filepath = os.path.join(folder_path, filename)
            data = convert_image(filepath, palette)
            out_path = os.path.join(out_folder, filename.replace(".png", ".bin"))
            with open(out_path, "wb") as f:
                f.write(data)
            print(f"  CONVERTED  {trait_folder}/{filename} → {len(data)} bytes")

if __name__ == "__main__":
    convert_all()