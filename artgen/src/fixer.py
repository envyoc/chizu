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

def closest_color(pixel, palette):
    r, g, b = pixel[:3]
    return min(palette, key=lambda c: math.sqrt(
        (r - c[0])**2 + (g - c[1])**2 + (b - c[2])**2
    ))

def fix_image(filepath, palette):
    img = Image.open(filepath).convert("RGBA")
    pixels = img.load()
    fixed = 0
    for x in range(img.width):
        for y in range(img.height):
            pixel = pixels[x, y]
            if pixel[3] == 0:
                continue  # skip transparent
            rgb = pixel[:3]
            if rgb not in palette:
                replacement = closest_color(pixel, palette)
                pixels[x, y] = replacement + (pixel[3],)
                fixed += 1
    img.save(filepath)
    return fixed

def fix_all(assets_dir="assets"):
    palette = load_palette()
    for trait_folder in sorted(os.listdir(assets_dir)):
        folder_path = os.path.join(assets_dir, trait_folder)
        if not os.path.isdir(folder_path):
            continue
        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(".png"):
                continue
            filepath = os.path.join(folder_path, filename)
            fixed = fix_image(filepath, palette)
            if fixed:
                print(f"  FIXED  {trait_folder}/{filename} — {fixed} pixels replaced")

if __name__ == "__main__":
    fix_all()