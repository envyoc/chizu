import json
import os

def load_config(config_path="config.json"):
    with open(config_path) as f:
        return json.load(f)

def format_trait(layer, trait_file):
    if trait_file is None:
        return None
    name = trait_file.replace(".png", "")
    name = name.replace("_", " ").replace("-", " ")
    return name.title()

def format_layer(layer):
    return layer.replace("_", " ").title()

def generate_metadata(
    traits_path="output/images/_traits.json",
    output_dir="output/metadata",
    collection_name="ChizuBuds",
    description="A collection of 32x32 pixel art buds.",
    base_image_uri="ipfs://YOUR_CID_HERE/"
):
    os.makedirs(output_dir, exist_ok=True)

    with open(traits_path) as f:
        all_traits = json.load(f)

    config = load_config()
    layer_order = config["layer_order"]

    for entry in all_traits:
        token_id = entry["id"]
        chosen = entry["traits"]

        attributes = []
        for layer in layer_order:
            trait = chosen.get(layer)
            display_layer = format_layer(layer)
            display_trait = format_trait(layer, trait)

            attributes.append({
                "trait_type": display_layer,
                "value": display_trait if display_trait else "None"
            })

        metadata = {
            "name": f"{collection_name} #{token_id}",
            "description": description,
            "image": f"{base_image_uri}{token_id}.png",
            "attributes": attributes
        }

        out_path = os.path.join(output_dir, f"{token_id}.json")
        with open(out_path, "w") as f:
            json.dump(metadata, f, indent=2)

    print(f"  Exported {len(all_traits)} metadata files to {output_dir}/")
    print(f"\n  Remember to replace YOUR_CID_HERE with your IPFS CID after upload.")

if __name__ == "__main__":
    generate_metadata()