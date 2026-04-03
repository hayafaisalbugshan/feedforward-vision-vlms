"""
Stimulus generation script for the VLM Visual Agnosia experiment.

Starting from a folder of grayscale line drawings (e.g. Snodgrass & Vanderwart),
this script generates two stimulus conditions per image:

  1. Degraded line drawing  — 50% of line pixels randomly removed
  2. Mooney image           — Gaussian blur + threshold to high-contrast two-tone

Usage:
    python generate_stimuli.py --input stimuli/originals --output stimuli

Download Snodgrass & Vanderwart-like line drawings here (CC-BY-NC-SA):
    https://figshare.com/articles/dataset/Snodgrass_Vanderwart_Like_Objects/3102781
"""

import os
import argparse
import numpy as np
from PIL import Image, ImageFilter

# How much of the line drawing to remove (0.0 = none, 1.0 = all)
DEGRADATION_LEVEL = 0.50

# Gaussian blur radius before thresholding for Mooney generation
MOONEY_BLUR_RADIUS = 3.0

# Threshold (0-255): pixels below this become black, above become white
MOONEY_THRESHOLD = 128


def make_degraded(img_gray: np.ndarray, removal_rate: float = DEGRADATION_LEVEL) -> Image.Image:
    """
    Remove a random fraction of dark (line) pixels from a grayscale line drawing.
    Line pixels are defined as pixels darker than 200 (on 0-255 scale).
    """
    degraded = img_gray.copy()
    line_mask = degraded < 200                        # find line pixels
    line_coords = np.argwhere(line_mask)              # get their coordinates
    n_remove = int(len(line_coords) * removal_rate)
    remove_idx = np.random.choice(len(line_coords), n_remove, replace=False)
    remove_coords = line_coords[remove_idx]
    degraded[remove_coords[:, 0], remove_coords[:, 1]] = 255   # set to white
    return Image.fromarray(degraded)


def make_mooney(pil_img: Image.Image,
                blur_radius: float = MOONEY_BLUR_RADIUS,
                threshold: int = MOONEY_THRESHOLD) -> Image.Image:
    """
    Convert a grayscale image to a high-contrast two-tone Mooney image.
    Steps: Gaussian blur → threshold to pure black/white.
    """
    blurred = pil_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    arr = np.array(blurred)
    mooney = np.where(arr < threshold, 0, 255).astype(np.uint8)
    return Image.fromarray(mooney)


def process_folder(input_dir: str, output_dir: str, seed: int = 42):
    np.random.seed(seed)

    degraded_dir = os.path.join(output_dir, "degraded")
    mooney_dir = os.path.join(output_dir, "mooney")
    os.makedirs(degraded_dir, exist_ok=True)
    os.makedirs(mooney_dir, exist_ok=True)

    image_files = [f for f in os.listdir(input_dir)
                   if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))]

    if not image_files:
        print(f"No images found in {input_dir}")
        return

    print(f"Processing {len(image_files)} images...")

    for fname in sorted(image_files):
        name = os.path.splitext(fname)[0]
        path = os.path.join(input_dir, fname)

        img = Image.open(path).convert("L")   # convert to grayscale
        arr = np.array(img)

        # Generate and save degraded version
        degraded_img = make_degraded(arr)
        degraded_img.save(os.path.join(degraded_dir, f"{name}.png"))

        # Generate and save Mooney version
        mooney_img = make_mooney(img)
        mooney_img.save(os.path.join(mooney_dir, f"{name}.png"))

        print(f"  {name} -> degraded/ and mooney/")

    print(f"\nDone. Stimuli saved to {output_dir}/degraded/ and {output_dir}/mooney/")
    print(f"Total matched pairs: {len(image_files)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate degraded and Mooney stimuli from line drawings.")
    parser.add_argument("--input", default="stimuli/originals",
                        help="Folder containing original line drawing images")
    parser.add_argument("--output", default="stimuli",
                        help="Output folder (degraded/ and mooney/ will be created inside)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    process_folder(args.input, args.output, args.seed)
