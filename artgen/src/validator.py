import json
import os
from PIL import Image

def load_palette(config_path="config.json"):
    with open(config_path) as f:
        config = json.load(f)
    palette = []
    for hex_color in config["palette"]:
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        palette.append(rgb)
    return palette, config.get("tolerance", 0)

def is_color_allowed(pixel, palette, tolerance):
    r, g, b = pixel[:3]  # ignore alpha channel if present
    for pr, pg, pb in palette:
        if abs(r - pr) <= tolerance and \
           abs(g - pg) <= tolerance and \
           abs(b - pb) <= tolerance:
            return True
    return False

def validate_image(filepath, palette, tolerance):
    img = Image.open(filepath).convert("RGBA")
    invalid_pixels = {}
    for x in range(img.width):
        for y in range(img.height):
            pixel = img.getpixel((x, y))
            if pixel[3] == 0:
                continue  # skip fully transparent pixels
            if not is_color_allowed(pixel, palette, tolerance):
                color = pixel[:3]
                invalid_pixels[color] = invalid_pixels.get(color, 0) + 1
    return invalid_pixels

def validate_all(assets_dir="assets"):
    palette, tolerance = load_palette()
    all_passed = True

    for trait_folder in sorted(os.listdir(assets_dir)):
        folder_path = os.path.join(assets_dir, trait_folder)
        if not os.path.isdir(folder_path):
            continue
        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(".png"):
                continue
            filepath = os.path.join(folder_path, filename)
            invalid = validate_image(filepath, palette, tolerance)
            if invalid:
                all_passed = False
                print(f"  FAIL  {trait_folder}/{filename}")
                for color, count in invalid.items():
                    print(f"         └─ RGB{color} appears {count}x — not in palette")

    print()
    if all_passed:
        print("All images passed palette validation.")
    else:
        print("Some images failed. Fix the colors above before continuing.")

if __name__ == "__main__":
    validate_all()