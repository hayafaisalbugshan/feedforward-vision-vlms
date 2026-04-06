"""
Stimulus generation script for the VLM Visual Agnosia experiment.

Starting from a folder of grayscale line drawings (e.g. Snodgrass & Vanderwart),
this script generates four stimulus conditions per image:

  1. Degraded line drawings — at multiple degradation levels (default: 25%, 50%, 75%)
  2. Mooney image           — Gaussian blur + threshold to high-contrast two-tone
  3. Inverted Mooney        — same as Mooney but black/white flipped (contamination control)

Usage:
    python generate_stimuli.py --input stimuli/originals --output stimuli
    python generate_stimuli.py --input stimuli/originals --output stimuli --levels 0.25 0.50 0.75

Download Snodgrass & Vanderwart-like line drawings here (CC-BY-NC-SA):
    https://figshare.com/articles/dataset/Snodgrass_Vanderwart_Like_Objects/3102781
"""

import os
import time
import argparse
import numpy as np
from PIL import Image, ImageFilter

# Gaussian blur radius before thresholding for Mooney generation
# Increased from 3.0 to 7.0 — higher blur destroys more local structure,
# forcing reliance on global form (the whole point of Mooney images).
# At 3.0 models scored 80%+; humans score ~34%, so local features were leaking through.
MOONEY_BLUR_RADIUS = 7.0

# Threshold (0-255): pixels below this become black, above become white
MOONEY_THRESHOLD = 128

# Default degradation levels to generate (added 0.90 to find model failure ceiling)
DEFAULT_LEVELS = [0.25, 0.50, 0.75, 0.90]


def make_degraded(img_gray: np.ndarray, removal_rate: float) -> Image.Image:
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


def make_inverted_mooney(pil_img: Image.Image,
                         blur_radius: float = MOONEY_BLUR_RADIUS,
                         threshold: int = MOONEY_THRESHOLD) -> Image.Image:
    """
    Generate an inverted Mooney image (white/black flipped after thresholding).

    Contamination control: if a model has seen the exact Mooney images during
    training, standard Mooney accuracy may be spuriously high. Inverted Mooneys
    preserve the perceptual challenge (gestalt completion still required) but
    produce a novel pixel pattern unlikely to appear in training data.

    If contamination drives accuracy, VLM performance should drop more steeply
    on inverted vs. standard Mooneys — but human performance should be similar
    (humans use top-down completion regardless of polarity).
    """
    blurred = pil_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    arr = np.array(blurred)
    mooney = np.where(arr < threshold, 255, 0).astype(np.uint8)  # flipped
    return Image.fromarray(mooney)


def process_folder(input_dir: str, output_dir: str,
                   levels: list, seed: int = 42):
    np.random.seed(seed)

    # Create output directories for each condition
    mooney_dir = os.path.join(output_dir, "mooney")
    mooney_inv_dir = os.path.join(output_dir, "mooney_inverted")
    os.makedirs(mooney_dir, exist_ok=True)
    os.makedirs(mooney_inv_dir, exist_ok=True)

    degraded_dirs = {}
    for level in levels:
        pct = int(level * 100)
        d = os.path.join(output_dir, f"degraded_{pct}")
        os.makedirs(d, exist_ok=True)
        degraded_dirs[level] = d

    image_files = [f for f in os.listdir(input_dir)
                   if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))]

    if not image_files:
        print(f"No images found in {input_dir}")
        return

    print(f"Processing {len(image_files)} images at degradation levels: {[int(l*100) for l in levels]}%")

    skipped = []

    for fname in sorted(image_files):
        name = os.path.splitext(fname)[0]
        path = os.path.join(input_dir, fname)

        try:
            img = Image.open(path).convert("L")   # convert to grayscale
            arr = np.array(img)

            # Generate degraded versions at each level
            for level, out_dir in degraded_dirs.items():
                degraded_img = make_degraded(arr, removal_rate=level)
                _save_with_retry(degraded_img, os.path.join(out_dir, f"{name}.png"))

            # Generate standard Mooney
            mooney_img = make_mooney(img)
            _save_with_retry(mooney_img, os.path.join(mooney_dir, f"{name}.png"))

            # Generate inverted Mooney (contamination control)
            mooney_inv_img = make_inverted_mooney(img)
            _save_with_retry(mooney_inv_img, os.path.join(mooney_inv_dir, f"{name}.png"))

            level_str = ", ".join([f"degraded_{int(l*100)}/" for l in levels])
            print(f"  {name} -> {level_str} mooney/, mooney_inverted/")

        except (TimeoutError, OSError) as e:
            print(f"  WARNING: skipping {name} — {e}")
            skipped.append(name)

    conditions = [f"degraded_{int(l*100)}/" for l in levels] + ["mooney/", "mooney_inverted/"]
    print(f"\nDone. Stimuli saved to: {', '.join(conditions)}")
    print(f"Total processed: {len(image_files) - len(skipped)}/{len(image_files)}")
    if skipped:
        print(f"Skipped (file lock/timeout): {skipped}")
        print("Tip: if on iCloud Desktop, move the project to ~/vlm-visual-agnosia and re-run.")


def _save_with_retry(img: Image.Image, path: str, retries: int = 3, delay: float = 2.0):
    """Save a PIL image, retrying on timeout (common with iCloud-synced folders)."""
    for attempt in range(retries):
        try:
            img.save(path)
            return
        except (TimeoutError, OSError):
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate degraded and Mooney stimuli from line drawings.")
    parser.add_argument("--input", default="stimuli/originals",
                        help="Folder containing original line drawing images")
    parser.add_argument("--output", default="stimuli",
                        help="Output folder (condition subfolders created inside)")
    parser.add_argument("--levels", nargs="+", type=float, default=DEFAULT_LEVELS,
                        help="Degradation levels as fractions, e.g. --levels 0.25 0.50 0.75 0.90")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    process_folder(args.input, args.output, args.levels, args.seed)
