"""
Experiment 1 — standalone runner.

Runs all 6 conditions (mooney, mooney_inv, degraded_25/50/75/90) across both models.
Checkpoints after every trial to results_checkpoint.csv.

Usage:
    python run_experiment1.py
"""

import os
import base64
import pandas as pd
from tqdm import tqdm
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://litellm.ccv.brown.edu"
)

MODELS = [
    "claude-sonnet-4-5",
    "gpt-5.4",
]

SYSTEM_PROMPT = "You are participating in an object recognition experiment. Respond with only the name of the object you see — a single word or short noun phrase. Do not describe the image. Do not say you are unsure. Just name the object."
USER_PROMPT = "What object is in this image?"

SYNONYMS = {
    "garbage can":    ["trash can", "rubbish bin", "waste bin", "dustbin"],
    "gun":            ["revolver", "pistol", "firearm", "handgun"],
    "kettle":         ["teapot"],
    "pot":            ["saucepan", "cooking pot"],
    "pocketbook":     ["handbag", "purse", "wallet"],
    "wineglass":      ["goblet", "wine glass"],
    "sea horse":      ["seahorse"],
    "roller skate":   ["roller skates"],
    "tennis racket":  ["tennis racquet", "racket", "racquet"],
    "record player":  ["turntable", "gramophone", "phonograph"],
    "jacket":         ["coat", "blazer"],
    "seal":           ["sea lion"],
}


def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def is_correct(response, true_label):
    resp = response.lower().strip()
    label = true_label.lower().replace("_", " ").strip()
    if len(resp.split()) > 8:
        return False
    if label in resp:
        return True
    for syn in SYNONYMS.get(label, []):
        if syn.lower() in resp:
            return True
    return False


def query_model(model, image_path):
    image_data = encode_image(image_path)
    ext = os.path.splitext(image_path)[-1].lower().replace(".", "")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}},
                    {"type": "text", "text": USER_PROMPT}
                ]
            }
        ],
        reasoning_effort=None
    )
    return response.choices[0].message.content.strip().lower()


def load_stimuli(stimuli_dir="stimuli"):
    conditions = {
        "mooney":       os.path.join(stimuli_dir, "mooney"),
        "mooney_inv":   os.path.join(stimuli_dir, "mooney_inverted"),
        "degraded_25":  os.path.join(stimuli_dir, "degraded_25"),
        "degraded_50":  os.path.join(stimuli_dir, "degraded_50"),
        "degraded_75":  os.path.join(stimuli_dir, "degraded_75"),
        "degraded_90":  os.path.join(stimuli_dir, "degraded_90"),
    }
    label_sets = []
    for cdir in conditions.values():
        label_sets.append({os.path.splitext(f)[0] for f in os.listdir(cdir)
                           if f.lower().endswith('.png')})
    matched = sorted(set.intersection(*label_sets))
    stimuli = []
    for label in matched:
        for cname, cdir in conditions.items():
            stimuli.append({"label": label, "condition": cname,
                            "path": os.path.join(cdir, f"{label}.png")})
    print(f"Found {len(matched)} objects × {len(conditions)} conditions = {len(stimuli)} trials")
    return stimuli


def run_experiment(stimuli, models, checkpoint_file="results_checkpoint.csv"):
    if os.path.exists(checkpoint_file):
        existing = pd.read_csv(checkpoint_file)
        done = set(zip(existing["model"], existing["label"], existing["condition"]))
        results = existing.to_dict("records")
        print(f"Resuming from checkpoint: {len(results)} trials already done")
    else:
        done, results = set(), []

    for model in models:
        remaining = [t for t in stimuli if (model, t["label"], t["condition"]) not in done]
        print(f"\nModel: {model} — {len(remaining)} trials remaining")
        for trial in tqdm(remaining):
            response = query_model(model, trial["path"])
            correct = is_correct(response, trial["label"])
            results.append({
                "model": model,
                "label": trial["label"],
                "condition": trial["condition"],
                "response": response,
                "correct": correct
            })
            done.add((model, trial["label"], trial["condition"]))
            pd.DataFrame(results).to_csv(checkpoint_file, index=False)

    df = pd.DataFrame(results)
    print(f"\nDone. {len(df)} total trials saved to {checkpoint_file}")
    return df


if __name__ == "__main__":
    stimuli = load_stimuli()
    run_experiment(stimuli, MODELS)
