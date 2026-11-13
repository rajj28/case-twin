"""Original medical models, loaded on ZeroGPU's emulated CUDA at startup."""
import spaces  # Must precede torch imports for ZeroGPU CUDA emulation.
import base64
import io
import os
import gradio as gr
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel, AutoProcessor, Gemma3ForConditionalGeneration

TOKEN = os.environ.get("HF_TOKEN")
MEDGEMMA_ID = "google/medgemma-4b-it"
MEDSIGLIP_ID = "google/medsiglip-448"

print("Loading MedSigLIP model and processor...", flush=True)
siglip_processor = AutoImageProcessor.from_pretrained(MEDSIGLIP_ID, token=TOKEN)
siglip_model = AutoModel.from_pretrained(
    MEDSIGLIP_ID, token=TOKEN, torch_dtype=torch.float16
).eval().to("cuda")
print("Loading MedGemma model and processor...", flush=True)
medgemma_processor = AutoProcessor.from_pretrained(MEDGEMMA_ID, token=TOKEN)
medgemma_model = Gemma3ForConditionalGeneration.from_pretrained(
    MEDGEMMA_ID, token=TOKEN, torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True, attn_implementation="eager",
).eval().to("cuda")
print("Both medical models loaded.", flush=True)

def read_image(encoded):
    if not encoded:
        return None
    if len(encoded) > 16_000_000:
        raise gr.Error("Image exceeds the demo upload limit.")
    if encoded.startswith("data:"):
        encoded = encoded.split(",", 1)[1]
    image = Image.open(io.BytesIO(base64.b64decode(encoded, validate=True)))
    if image.width * image.height > 36_000_000:
        raise gr.Error("Image resolution exceeds the demo limit.")
    return image.convert("RGB")

@spaces.GPU(duration=15)
def embed(image_base64):
    image = read_image(image_base64)
    if image is None:
        raise gr.Error("Provide an image.")
    inputs = siglip_processor(images=image, return_tensors="pt")
    inputs = {k: v.to("cuda", dtype=torch.float16) if v.is_floating_point() else v.to("cuda") for k, v in inputs.items()}
    with torch.inference_mode():
        vector = siglip_model.get_image_features(**inputs)
        if not isinstance(vector, torch.Tensor):
            vector = vector.pooler_output
        vector = vector / vector.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    return {"image_embedding": vector[0].float().cpu().tolist(), "model": MEDSIGLIP_ID}

@spaces.GPU(duration=45)
def generate(image_base64, prompt, max_tokens=300):
    if not isinstance(prompt, str) or len(prompt) > 40_000:
        raise gr.Error("Prompt is missing or exceeds the demo limit.")
    image = read_image(image_base64)
    content = []
    if image is not None:
        content.append({"type": "image", "image": image})
    content.append({"type": "text", "text": prompt})
    messages = [{"role": "user", "content": content}]
    inputs = medgemma_processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt",
    )
    inputs = {k: v.to("cuda", dtype=torch.bfloat16) if v.is_floating_point() else v.to("cuda") for k, v in inputs.items()}
    prefix_length = inputs["input_ids"].shape[-1]
    with torch.inference_mode():
        generated = medgemma_model.generate(
            **inputs, max_new_tokens=max(1, min(768, int(max_tokens))), do_sample=False,
        )
    text = medgemma_processor.decode(generated[0, prefix_length:], skip_special_tokens=True)
    return {"generated_text": text, "model": MEDGEMMA_ID}

with gr.Blocks(analytics_enabled=False) as app:
    gr.Markdown("# CaseTwin medical models\nMedGemma + MedSigLIP on quota-limited ZeroGPU. Use the API endpoints from the CaseTwin application.")
    encoded = gr.Textbox(label="Base64 image", lines=2)
    prompt = gr.Textbox(label="Prompt", value="Describe this chest X-ray.")
    tokens = gr.Slider(1, 768, value=300, step=1, label="Maximum output tokens")
    output = gr.JSON(label="Model output")
    gr.Button("Embed with MedSigLIP").click(embed, inputs=[encoded], outputs=[output], api_name="embed", concurrency_limit=1)
    gr.Button("Generate with MedGemma").click(generate, inputs=[encoded, prompt, tokens], outputs=[output], api_name="generate", concurrency_limit=1)

app.queue(max_size=8).launch()
