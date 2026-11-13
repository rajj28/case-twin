"""Gradio's HTTP event API, with secrets confined to server-side headers."""
import base64
import io
import json
import os
from functools import lru_cache
import requests

@lru_cache(maxsize=1)
def space_url():
    configured = os.getenv("HF_SPACE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    repo_id = os.getenv("HF_SPACE_ID", "").strip()
    if not repo_id:
        raise RuntimeError("HF_SPACE_ID is not configured.")
    result = requests.get(
        f"https://huggingface.co/api/spaces/{repo_id}",
        headers=_headers(), timeout=30,
    )
    result.raise_for_status()
    host = result.json().get("host")
    if not host:
        raise RuntimeError("Medical model Space has not exposed a running host yet.")
    return host.rstrip("/")

def _headers():
    token = os.getenv("HF_TOKEN", "").strip()
    return {"Authorization": "Bearer " + token} if token else {}

def image_base64(image):
    if image is None:
        return ""
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")

def call_space(endpoint, data):
    url = f"{space_url()}/gradio_api/call/{endpoint}"
    response = requests.post(url, headers=_headers(), json={"data": data}, timeout=35)
    if response.status_code in (429, 503):
        raise RuntimeError("Medical model service is busy or its free quota is exhausted. Please try later.")
    response.raise_for_status()
    event_id = response.json().get("event_id")
    if not event_id:
        raise RuntimeError("Medical model service did not enqueue the request.")
    with requests.get(f"{url}/{event_id}", headers=_headers(), stream=True, timeout=(15, 180)) as stream:
        stream.raise_for_status()
        event = ""
        for line in stream.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                payload = json.loads(line[5:].strip())
                if event == "complete":
                    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
                        raise RuntimeError("Medical model service returned an unexpected response.")
                    return payload[0]
                if event == "error":
                    raise RuntimeError("Medical model request failed. Check Space status and the remaining ZeroGPU quota.")
    raise RuntimeError("Medical model service closed before producing a result.")

def embed_image(image):
    result = call_space("embed", [image_base64(image)])
    embedding = result.get("image_embedding")
    if not isinstance(embedding, list) or len(embedding) != 1152 or not any(embedding):
        raise RuntimeError("MedSigLIP returned an invalid embedding.")
    return embedding

def generate(image, prompt, max_tokens=300, stop_sequences=None):
    result = call_space("generate", [image_base64(image), prompt, int(max_tokens)])
    text = result.get("generated_text")
    if not isinstance(text, str):
        raise RuntimeError("MedGemma returned an invalid response.")
    for stop in stop_sequences or []:
        text = text.split(stop, 1)[0]
    return [{"generated_text": text}]
