"""Check configured services without logging credentials or response bodies."""
import concurrent.futures
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]

def read_env(path):
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result

def check(label, url, headers, params=None):
    try:
        response = requests.get(url, headers=headers, params=params, timeout=35)
        result = {"service": label, "status": response.status_code}
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.ok:
            if label == "huggingface":
                result.update({k: body.get(k) for k in ("name", "createdAt", "isPro", "canPay")})
                result["auth_role"] = body.get("auth", {}).get("accessToken", {}).get("role")
                result["spaces"] = [x.get("id") for x in body.get("spaces", [])]
            elif label == "qdrant":
                result["collections"] = body.get("result", {}).get("collections", [])
            elif label == "render":
                result["owners"] = [{"id": x.get("owner", {}).get("id"), "name": x.get("owner", {}).get("name"), "type": x.get("owner", {}).get("type")} for x in body]
            elif label == "gemini":
                result["models"] = [x.get("name") for x in body.get("models", []) if "flash" in x.get("name", "")][:12]
            elif label.startswith("model_access"):
                result["model_type"] = body.get("model_type")
        return result
    except requests.RequestException as error:
        return {"service": label, "network_error": type(error).__name__}

def main():
    env = read_env(ROOT / "backend/.env")
    deploy = read_env(ROOT / ".deploy.env")
    hf_headers = {"Authorization": "Bearer " + env.get("HF_TOKEN", "")}
    calls = [
        ("huggingface", "https://huggingface.co/api/whoami-v2", hf_headers),
        ("model_access_medgemma", "https://huggingface.co/google/medgemma-4b-it/resolve/main/config.json", hf_headers),
        ("model_access_medsiglip", "https://huggingface.co/google/medsiglip-448/resolve/main/config.json", hf_headers),
        ("qdrant", env.get("QDRANT_URL", "").rstrip("/") + "/collections", {"api-key": env.get("QDRANT_API_KEY", "")}),
        ("render", "https://api.render.com/v1/owners", {"Authorization": "Bearer " + deploy.get("RENDER_API_KEY", "")}),
        ("gemini", "https://generativelanguage.googleapis.com/v1beta/models", {"x-goog-api-key": env.get("GEMINI_API_KEY", "")}),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda args: check(*args), calls))
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
