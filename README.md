# Do VLMs Use Feedforward or Feedback Visual Processing?

**Haya Bugshan, Mohammad Essa — CPSY 1950: Deep Learning in Brains, Minds & Machines — Brown University, Spring 2026**

We tested whether vision-language models (VLMs) process images the way humans do — specifically whether they rely on feedforward feature matching or top-down feedback for object recognition. Using Snodgrass & Vanderwart (1980) line drawings across 4,160 trials, we found that VLMs consistently outperform humans on degraded drawings but fail at human levels on Mooney (two-tone) images when sufficiently hard — consistent with a feedforward processing account. A visual priming experiment further showed that models recover Mooney recognition when given a degraded hint in the same prompt, but only because both images co-exist in one forward pass — not true perceptual memory.

---

## Experiments

**Experiment 1** — 260 S&V objects × 6 conditions × 2 models = 1,560 trials  
Conditions: Degraded 25 / 50 / 75 / 90% · Standard Mooney (σ=2.0) · Inverted Mooney

**Experiment 2** — 260 objects × 2 conditions × 2 models = 1,040 trials  
Conditions: Hard Mooney unprimed (σ=4.0) · Hard Mooney primed (degraded_25 shown first)

**Models:** `claude-sonnet-4-5` (Anthropic) · `gpt-5.4` (OpenAI) via Brown CCV LiteLLM

---

## Key Results

| Condition | Claude | GPT-5.4 | Human baseline |
|---|---|---|---|
| Degraded 25% | 92% | 94% | ~63% |
| Degraded 90% | 49% | 81% | ~15% |
| Standard Mooney | 82% | 73% | ~34% |
| Hard Mooney (unprimed) | 27% | 22% | ~20% |
| Hard Mooney (primed) | 80% | 90% | ~65% |

---

## Repo Structure

```
experiment.ipynb          # Main analysis notebook (all figures, both experiments)
run_experiment1.py        # Standalone runner for Experiment 1 (checkpointed)
generate_stimuli.py       # Generates degraded + Mooney stimuli from line drawings
requirements.txt          # Python dependencies
results_checkpoint.csv    # Experiment 1 results (3,120 trials)
results_priming.csv       # Experiment 2 results (1,040 trials)
fig0_stimulus_examples.png
fig1_exp1_results.png
fig2_priming_results.png
fig3_error_types.png
fig4_scatter.png
fig5_agreement.png
fig_table.png
FIXES.md                  # Running log of all changes made post-initial run
```

---

## Reproducing

```bash
pip install -r requirements.txt
cp .env.example .env      # add your API key
python generate_stimuli.py --input stimuli/originals --output stimuli
python run_experiment1.py
# then open experiment.ipynb for analysis and figures
```

**Note:** Stimuli (S&V line drawings) are not included in this repo. Download from:  
Rossion & Pourtois (2004) colorized S&V set — available via figshare.

---

## References

- Snodgrass & Vanderwart (1980). A standardized set of 260 pictures. *JEP: Human Learning and Memory.*
- Snodgrass & Corwin (1988). Pragmatics of measuring recognition memory. *JEP: General.*
- Moore & Cavanagh (1998). Recovery of 3D volume from 2-tone images. *Cognition.*
- Marjieh et al. (2024). Filling in the blanks: Concept representations in VLMs. *NeurIPS.*
