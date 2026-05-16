import json
import os
import hashlib
from PIL import Image

def hash_image(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def hash_traits(chosen):
    trait_string = json.dumps(chosen, sort_keys=True)
    return hashlib.sha256(trait_string.encode()).hexdigest()

def check_duplicates(output_dir="output/images"):
    seen_hashes = {}
    duplicates = []

    files = [f for f in sorted(os.listdir(output_dir)) if f.endswith(".png")]

    for filename in files:
        filepath = os.path.join(output_dir, filename)
        h = hash_image(filepath)
        if h in seen_hashes:
            duplicates.append((filename, seen_hashes[h]))
            print(f"  DUPE  {filename} is identical to {seen_hashes[h]}")
        else:
            seen_hashes[h] = filename

    print(f"\n  Checked {len(files)} images.")
    if duplicates:
        print(f"  Found {len(duplicates)} duplicate(s) — regenerate these before minting.")
    else:
        print(f"  No duplicates found. All good.")

    return duplicates

if __name__ == "__main__":
    check_duplicates()