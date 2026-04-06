"""
Download validated stimulus sets with published human recognition norms.

This replaces our algorithmically-generated stimuli with datasets where
the SAME images were tested on human participants, making VLM comparisons valid.

Datasets:
  1. FAOT (Colman et al., 2019) — fragmented line-segment objects
     100 images, human recognizability norms from 120 observers per image
     Source: https://github.com/caolman/FAOT (GPL-3.0)

  2. Reining & Wallis (2024) — Mooney images from THINGS objects
     549 Mooney images with psychophysical data
     Source: https://zenodo.org/records/10714959 (CC)
     WARNING: 751 MB download — run with --mooney to include

Usage:
    python download_validated_stimuli.py           # FAOT only (fast)
    python download_validated_stimuli.py --mooney  # FAOT + Mooney (751 MB)
"""

import os
import re
import time
import zipfile
import argparse
import urllib.request
import urllib.error
import csv

FAOT_BASE = "https://raw.githubusercontent.com/caolman/FAOT/master"
FAOT_STIMULI_DIR = "stimuli/faot"
FAOT_NORMS_PATH = "stimuli/faot_norms.csv"
MOONEY_DIR = "stimuli/mooney_validated"
MOONEY_NORMS_PATH = "stimuli/mooney_validated_norms.csv"
ZENODO_URL = "https://zenodo.org/records/10714959/files/psychophysical_evaluation_mooney_image_generation-1.0.0.zip"


def download_file(url, dest_path, description=""):
    """Download a file with a simple progress indicator."""
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                pct = min(int(count * block_size * 100 / total_size), 100)
                print(f"\r  {description}: {pct}%", end="", flush=True)

        urllib.request.urlretrieve(url, dest_path, reporthook=reporthook)
        print()  # newline after progress
        return True
    except urllib.error.HTTPError as e:
        print(f"\n  FAILED ({e.code}): {url}")
        return False
    except Exception as e:
        print(f"\n  FAILED: {e}")
        return False


def extract_label_from_source(source_str):
    """
    Extract the object label from the FAOT source filename.
    e.g. 'Adlington/whisk_ed.bmp' -> 'whisk'
         'Adlington/Tower-Block_ed.bmp' -> 'tower block'
    """
    fname = os.path.basename(source_str)           # 'whisk_ed.bmp'
    name = re.sub(r'_ed\.(bmp|png|jpg)$', '', fname, flags=re.IGNORECASE)
    name = name.replace("-", " ").replace("_", " ").lower().strip()
    return name


def download_faot():
    """Download FAOT images and norms from GitHub."""
    print("=== Downloading FAOT (Colman et al., 2019) ===")
    os.makedirs(FAOT_STIMULI_DIR, exist_ok=True)

    # Download norms CSV
    print("Downloading stimulus_info.csv...")
    csv_url = f"{FAOT_BASE}/stimulus_info.csv"
    csv_path = "stimuli/faot_stimulus_info_raw.csv"
    if not download_file(csv_url, csv_path, "norms"):
        print("ERROR: Could not download FAOT norms. Aborting.")
        return False

    # Parse norms and extract labels
    norms = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = extract_label_from_source(row["source"])
            norms.append({
                "image_id":       row["ID"],           # e.g. img0001.png
                "label":          label,
                "recognizability": float(row["recognizability"]),
                "stability":      float(row["stability"]),
                "source":         row["source"],
                "human_names":    row["names"],
            })

    # Save cleaned norms
    with open(FAOT_NORMS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=norms[0].keys())
        writer.writeheader()
        writer.writerows(norms)
    print(f"Norms saved to {FAOT_NORMS_PATH} ({len(norms)} items)")

    # Download images
    print(f"Downloading {len(norms)} images to {FAOT_STIMULI_DIR}/...")
    failed = []
    for i, row in enumerate(norms):
        img_id = row["image_id"]
        dest = os.path.join(FAOT_STIMULI_DIR, img_id)
        if os.path.exists(dest):
            print(f"  {img_id} already exists, skipping")
            continue
        url = f"{FAOT_BASE}/stimuli/{img_id}"
        ok = download_file(url, dest, f"{i+1}/{len(norms)} {img_id}")
        if not ok:
            failed.append(img_id)
        time.sleep(0.05)  # gentle rate limiting

    if failed:
        print(f"WARNING: {len(failed)} images failed to download: {failed}")
    else:
        print(f"All {len(norms)} FAOT images downloaded successfully.")

    # Print summary of recognizability range
    scores = [r["recognizability"] for r in norms]
    print(f"\nFAOT recognizability range: {min(scores):.2f} – {max(scores):.2f}")
    print(f"Mean human recognizability: {sum(scores)/len(scores):.2f}")
    return True


def download_mooney_zenodo():
    """Download and extract Reining & Wallis (2024) Mooney images from Zenodo."""
    print("\n=== Downloading Reining & Wallis (2024) Mooney images ===")
    print("WARNING: This is a 751 MB download. This may take several minutes.")

    zip_path = "stimuli/mooney_zenodo.zip"
    extract_path = "stimuli/mooney_zenodo_extracted"

    if not os.path.exists(zip_path):
        print("Downloading ZIP from Zenodo...")
        ok = download_file(ZENODO_URL, zip_path, "mooney_zenodo.zip")
        if not ok:
            print("ERROR: Could not download Zenodo dataset.")
            return False
    else:
        print(f"ZIP already exists at {zip_path}, skipping download.")

    print("Extracting ZIP...")
    os.makedirs(extract_path, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_path)

    # Find Mooney image files within extracted folder
    mooney_images = []
    for root, dirs, files in os.walk(extract_path):
        for fname in files:
            if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                full_path = os.path.join(root, fname)
                # Look for files in folders named 'mooney' or similar
                if "mooney" in root.lower() or "binary" in root.lower() or "two_tone" in root.lower():
                    mooney_images.append(full_path)

    if not mooney_images:
        # If no mooney-specific folder found, list all images found for inspection
        all_images = []
        for root, dirs, files in os.walk(extract_path):
            for fname in files:
                if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                    all_images.append(os.path.join(root, fname))
        print(f"Could not find a 'mooney' subfolder. Found {len(all_images)} total images.")
        print("First 10 image paths found:")
        for p in all_images[:10]:
            print(f"  {p}")
        print("\nPlease inspect the extracted folder and update MOONEY_SOURCE_DIR in this script.")
        return False

    # Copy Mooney images to stimuli/mooney_validated/
    os.makedirs(MOONEY_DIR, exist_ok=True)
    copied = 0
    for src_path in mooney_images:
        fname = os.path.basename(src_path)
        dest = os.path.join(MOONEY_DIR, fname)
        if not os.path.exists(dest):
            import shutil
            shutil.copy2(src_path, dest)
            copied += 1

    print(f"Copied {copied} Mooney images to {MOONEY_DIR}/")

    # Note on norms — Reining & Wallis norms are partial (psychophysical methods paper)
    print("\nNOTE: Reining & Wallis (2024) norms are from a methods comparison study,")
    print("not a full naming norm database. Use as directional comparison only.")
    print("Awaiting MoonBase (Imamoglu et al., 2012) for full per-image norms.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mooney", action="store_true",
                        help="Also download Mooney dataset from Zenodo (751 MB)")
    args = parser.parse_args()

    faot_ok = download_faot()

    if args.mooney:
        download_mooney_zenodo()

    print("\n=== Summary ===")
    if faot_ok:
        print(f"FAOT images:  {FAOT_STIMULI_DIR}/  (100 images)")
        print(f"FAOT norms:   {FAOT_NORMS_PATH}")
    if args.mooney:
        print(f"Mooney images: {MOONEY_DIR}/")
    print("\nNext: run the experiment notebook and use load_validated_stimuli() instead of load_stimuli()")
