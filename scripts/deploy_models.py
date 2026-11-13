"""Publish only the medical model service on explicitly free ZeroGPU hardware."""
import json
from pathlib import Path
from huggingface_hub import HfApi, SpaceHardware
from check_services import read_env

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".deployment"
STATE.mkdir(exist_ok=True)
repo_id = "rajj28/case-twin-models"
env = read_env(ROOT / "backend/.env")
api = HfApi(token=env["HF_TOKEN"])

try:
    url = api.create_repo(
        repo_id=repo_id, repo_type="space", space_sdk="gradio",
        space_hardware=SpaceHardware.ZERO_A10G, private=False, exist_ok=True,
        space_secrets=[{"key": "HF_TOKEN", "value": env["HF_TOKEN"]}],
    )
    print("Free model Space registered:", str(url), flush=True)
    api.add_space_secret(repo_id, "HF_TOKEN", env["HF_TOKEN"])
    info = api.upload_folder(
        repo_id=repo_id, repo_type="space", folder_path=ROOT / "deployment/hf-space",
        allow_patterns=["*.py", "*.txt", "README.md", "LICENSE"],
        commit_message="Deploy original medical models on free ZeroGPU",
    )
    runtime = api.get_space_runtime(repo_id)
    state = {"space_id": repo_id, "space_url": str(url), "stage": str(runtime.stage), "requested_hardware": str(runtime.requested_hardware)}
    (STATE / "models.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    path = ROOT / "backend/.env"
    text = path.read_text(encoding="utf-8")
    if "HF_SPACE_ID=" not in text:
        text += "\nHF_SPACE_ID=" + repo_id + "\n"
        path.write_text(text, encoding="utf-8")
    print(json.dumps(state), flush=True)
except Exception as error:
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    print(json.dumps({"operation": "deploy_models", "error": type(error).__name__, "status": status}), flush=True)
    raise SystemExit(1)
