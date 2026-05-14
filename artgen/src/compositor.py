import json
import os
import random
from PIL import Image

def load_config(config_path="config.json"):
    with open(config_path) as f:
        return json.load(f)

def pick_traits(config, assets_dir="assets"):
    layer_order = config["layer_order"]
    rarity = config.get("rarity", {})
    chosen = {}

    for layer in layer_order:
        layer_path = os.path.join(assets_dir, layer)
        if not os.path.isdir(layer_path):
            continue

        # check if this layer is skipped entirely
        skip_chance = rarity.get(layer, {}).get("rarity", 0)
        if skip_chance > 0 and random.randint(1, 100) <= skip_chance:
            chosen[layer] = None
            continue

        # pick a random trait from the folder
        options = [f for f in os.listdir(layer_path) if f.endswith(".png")]
        chosen[layer] = random.choice(options)

    return chosen

def composite(chosen, config, assets_dir="assets"):
    base = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for layer in config["layer_order"]:
        trait = chosen.get(layer)
        if trait is None:
            continue
        path = os.path.join(assets_dir, layer, trait)
        img = Image.open(path).convert("RGBA")
        base = Image.alpha_composite(base, img)
    return base

def generate_previews(n=5, assets_dir="assets", output_dir="output/previews"):
    config = load_config()
    os.makedirs(output_dir, exist_ok=True)

    for i in range(n):
        chosen = pick_traits(config, assets_dir)
        img = composite(chosen, config, assets_dir)

        # scale up to 512x512 for easy viewing
        img = img.resize((512, 512), Image.NEAREST)

        out_path = os.path.join(output_dir, f"preview_{i+1}.png")
        img.save(out_path)

        print(f"\n  Preview {i+1}:")
        for layer, trait in chosen.items():
            print(f"    {layer:15} → {trait if trait else 'none'}")

    print(f"\n  Saved {n} previews to {output_dir}/")

if __name__ == "__main__":
    generate_previews(n=5)