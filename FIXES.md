# VLM Visual Agnosia — Fix Log

Running record of all changes made to the experiment pipeline post-initial-run.

---

## Fix 1 — `is_correct` scoring: underscore normalization + synonym matching
**File:** `experiment.ipynb` (Cell 8)  
**Problem:** Two bugs caused real correct responses to be scored as False:
1. Labels stored with underscores (`frying_pan`) were compared against model responses with spaces (`"frying pan"`) → False
2. Synonyms not handled: `garbage_can` → `"trash can"`, `gun` → `"revolver"`, `pot` → `"saucepan"`, `kettle` → `"teapot"`, `pocketbook` → `"handbag"`, etc.

**Impact on results:** Degraded accuracy inflated downward; true accuracy is higher than 84.5% / 68.3%

**Fix:** 
- Normalize labels by replacing underscores with spaces before comparison
- Added `SYNONYMS` dict mapping label → list of accepted alternatives
- `is_correct` now checks label (normalized) OR any synonym

---

## Fix 2 — Error type analysis
**File:** `experiment.ipynb` (new cell after Cell 12)  
**Problem:** Accuracy alone doesn't distinguish apperceptive from associative failure. The Marr-level argument requires knowing *what kind* of error the model makes.  
**Fix:** Added `classify_error` function that tags each False trial as one of:
- `synonym_artifact` — response is a known synonym (scoring error, not a real error)
- `semantic_neighbor` — response is in the same category (e.g., `seal` → `walrus`)
- `confabulation` — response is unrelated / bizarre (e.g., `sandwich` → `tambourine`)
- `refusal` — model said it couldn't identify the object

---

## Fix 3 — Inverted Mooney condition in `generate_stimuli.py`
**File:** `generate_stimuli.py`  
**Problem:** No contamination control. If models have seen the exact Mooney images during training, high accuracy is spurious.  
**Fix:** Added `--inverted` flag and `make_inverted_mooney` function. Inverted Mooneys flip black↔white after thresholding — the perceptual challenge is preserved but the exact pixel pattern is novel. Saves to `stimuli/mooney_inverted/`. If contamination drives performance, accuracy should drop more steeply on inverted vs. standard Mooneys for VLMs but not for humans.

---

## Fix 4 — Multiple degradation levels in `generate_stimuli.py`
**File:** `generate_stimuli.py`  
**Problem:** Only 50% degradation level — can't plot an accuracy curve across conditions.  
**Fix:** Added `--levels` flag (default: `0.25 0.50 0.75`). Saves each level to its own subfolder: `stimuli/degraded_25/`, `stimuli/degraded_50/`, `stimuli/degraded_75/`. Notebook updated to load and plot accuracy across levels.

---

## Fix 5 — `generate_stimuli.py` iCloud timeout handling
**File:** `generate_stimuli.py`  
**Problem:** Script crashed with `TimeoutError: [Errno 60] Operation timed out` on `lips.png` because the Desktop folder is iCloud-synced and iCloud held a file lock during writes.  
**Fix:** Added `_save_with_retry` helper (3 attempts, 2s delay) and wrapped each image's processing in a `try/except (TimeoutError, OSError)` block that skips and warns rather than crashing. Also prints a tip to move the project off Desktop if timeouts persist.

---

## Fix 12 — Error type plot updated to include hallucination
**File:** `experiment.ipynb` (Cell 18)  
**Problem:** `error_types` list in the plot was `["semantic_neighbor", "part_whole", "confabulation"]` — `hallucination` was classified correctly but never shown in the figure. Y-axis was also hardcoded to 0.25, potentially clipping bars.  
**Fix:** Added `hallucination` as first error type (dark red), dynamic y-axis, and count labels on each bar.

---

## Fix 11 — Hallucination guard in `is_correct` and `classify_error`
**Files:** `experiment.ipynb` (Cells 10, 18); `results.csv` rescored  
**Problem:** 17 responses (1.8%) were massive blobs of unrelated text (Chinese MCQs, social media posts) that happened to contain the target word via substring match, scoring as `True`. E.g. `trumpet` → 12-word Chinese passage containing "trumpet"; `table` → 60-word social media post.  
**Fix:**
- Added `len(resp.split()) > 8 → return False` guard to `is_correct`
- Added `hallucination` as first error type in `classify_error` (checked before semantic/confabulation)
- `results.csv` rescored — 6 false positives corrected

**Corrected accuracy (post all fixes):**
| Condition | Accuracy |
|---|---|
| degraded_25 | 86.3% |
| degraded_50 | 77.6% |
| degraded_75 | 67.1% |
| degraded_90 | 62.7% |
| mooney | 25.5% |
| mooney_inv | 21.1% |

---

## Fix 10 — Switched to validated stimuli with published human norms
**Files:** `download_validated_stimuli.py` (new), `experiment.ipynb` (Cells 7–8, 12, 14)  
**Problem:** Human baselines (Snodgrass & Corwin 1988; Koch et al. 1995) were from different images tested with different degradation methods. Comparing VLM performance on our generated stimuli to those norms is not a valid comparison.  
**Fix:**
- Created `download_validated_stimuli.py` to fetch FAOT (Colman et al., 2019) from GitHub and Reining & Wallis (2024) Mooney images from Zenodo
- FAOT: 100 fragmented images, per-image human recognizability norms from 120 observers; saved to `stimuli/faot/` and `stimuli/faot_norms.csv`
- Added `load_validated_stimuli()` to notebook — loads FAOT + Mooney validated images into the same `{label, condition, path}` format as `load_stimuli()`
- Updated `run_experiment` cell to call `load_validated_stimuli()` instead of `load_stimuli()`
- Updated `plot_accuracy` to show per-image scatter (VLM vs. human recognizability) as primary figure, with correlation coefficient
- Emailed Fatma Imamoglu (fatmaimamoglu@gmail.com) to request MoonBase (Imamoglu et al., 2012) for Mooney norms

---

## Fix 9 — Harder Mooney images + degraded_90 condition
**File:** `generate_stimuli.py`, `experiment.ipynb` (Cells 6, 12, 14)  
**Problem:** Models scored 80.1% on Mooney images vs. human baseline of ~34%. At `blur_radius=3.0`, enough local texture/edge information leaked through for the model to recognize objects without needing global form completion — defeating the purpose of Mooney stimuli.  
**Fix:**
- `MOONEY_BLUR_RADIUS` increased from `3.0` → `7.0` (destroys more local structure, forces global gestalt completion)
- Added `degraded_90` condition (90% of line pixels removed) to find the model's failure ceiling
- Human baseline for `degraded_90` estimated at ~15% (extrapolated from Snodgrass & Corwin trend)
- All 161 images regenerated across 6 conditions
- Notebook `load_stimuli`, `plot_accuracy`, and `plot_with_human_baseline` updated to include `degraded_90`

---

## Fix 8 — Error type analysis: condition names and plot updated
**File:** `experiment.ipynb` (Cell 16)  
**Problem:** Plot loop referenced `["degraded", "mooney"]` — old condition names that no longer exist after Fix 6 introduced `degraded_25/50/75` and `mooney_inv`. Plot would crash or show empty bars.  
**Fix:**
- Added `condition_group` column that maps `degraded_25/50/75` → `"degraded (all levels)"` for aggregated error analysis
- Plot expanded to 3 panels: Mooney / Inverted Mooney / Degraded (aggregated)
- Aggregating across degradation levels gives a stable error-type estimate rather than splitting already-small error counts three ways

---

## Fix 7 — Model swap: `gemini-3-flash-preview` → `claude-sonnet-4-5`
**File:** `experiment.ipynb` (Cell 2)  
**Problem:** `gemini-3-flash-preview` is listed at `/v1/models` but returns `400 Invalid model name` on `/chat/completions`. `gemini-3.1-flash-lite-preview` returns `null` content for vision inputs. Neither is usable.  
**Fix:** Switched `MODELS` to `["claude-sonnet-4-5"]` — confirmed working (returns correct vision responses). `gemini-2.5-pro` left commented out for when frontier access is granted.

---

## Fix 6 — `load_stimuli` and plots updated for all 5 conditions
**File:** `experiment.ipynb` (Cells 6, 12, 14)  
**Problem:** `load_stimuli` only loaded `mooney/` and `degraded/` — the new `degraded_25/`, `degraded_50/`, `degraded_75/`, and `mooney_inverted/` folders weren't included.  
**Fix:**
- `load_stimuli` now loads all 5 conditions, returns only labels present in every folder
- `plot_accuracy` updated to two-panel figure: degradation curve (left) + Mooney vs. inverted Mooney bar (right)
- `plot_with_human_baseline` updated with per-level human baselines from literature (Snodgrass & Corwin, 1988; Koch et al., 1995)

---
