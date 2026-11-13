---
title: CaseTwin Medical Models
emoji: 🩻
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 5.49.1
python_version: 3.10.13
app_file: app.py
pinned: false
license: mit
---

# CaseTwin medical model service

MedGemma (`google/medgemma-4b-it`) and MedSigLIP (`google/medsiglip-448`) on Hugging Face ZeroGPU. Model access requires acceptance of Google's Health AI Developer Foundations terms. Set `HF_TOKEN` as a Space secret, never a repository file.

The `embed` and `generate` APIs use the original medical model families. GPU calls consume the caller's daily ZeroGPU allowance. No paid fallback is configured. Research demonstration only.

Model cards: https://huggingface.co/google/medgemma-4b-it and https://huggingface.co/google/medsiglip-448.
