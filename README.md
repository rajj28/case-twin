# CaseTwin

**From medical image to clinical context.**

CaseTwin is a clinical research prototype that connects chest X-rays with similar published cases, compares their documented findings, and helps assemble specialist referral drafts.

## What it does

- Upload chest X-ray images and clinical notes.
- Retrieve similar cases with MedSigLIP embeddings and Qdrant, with clinical context used for reranking.
- Compare a selected historical case and inspect its available publication provenance.
- Ask follow-up questions using the current patient profile and selected case as context.
- Explore hospital and specialist search results on a map.
- Generate a printable referral draft for review.

## Stack

React 18, TypeScript, Vite, Tailwind CSS, Zustand, and Leaflet on the frontend. FastAPI, MedGemma, MedSigLIP, Gemini, Qdrant, and CrewAI on the backend.

## Run locally

Requires Node.js 20+, Python 3.11+, and configured external model endpoints and services.

```sh
npm ci
cp .env.example .env
npm run dev
```

In a second terminal:

```sh
cd backend
python -m venv .venv
# Activate .venv for your shell before installing dependencies.
pip install -r requirements.txt
cp .env.example .env
# Fill in backend/.env with your own service credentials.
uvicorn main:app --reload --port 8000
```

Use `Copy-Item` in place of `cp` when appropriate for your Windows shell. Run `npm run build` to type-check and build the frontend.

## Data and service setup

The case corpus, source images, and populated Qdrant collection are not bundled. Supply your own permitted dataset and configure the endpoints in `backend/.env`. The embedding-generation script is a Colab export and needs an external dataset, images, and notebook setup.

Set `VITE_API_URL` for the backend and optionally `VITE_IMAGE_BASE_URL` for relative image paths. Production deployments must use your own service URLs and credentials.

## Prototype limitations

Clinical note extraction includes regex heuristics. Ranking scores and profile completeness are not calibrated diagnostic probabilities. Image comparison displays model-produced bounding boxes only; missing coordinates remain unknown. Hospital search can use generated fallback results; verify them independently. This prototype is for research and demonstration, not clinical decision-making.

## License

MIT. See [LICENSE](LICENSE) for the required copyright and permission notice.

## Free demo deployment

The `Dockerfile.free` builds React and serves it alongside FastAPI on a single Render Free web service. `render.yaml` explicitly selects the Free plan. Model inference runs on the separate Hugging Face ZeroGPU Space defined in `deployment/hf-space`, using the original MedGemma and MedSigLIP models. Set `HF_SPACE_ID`, `HF_TOKEN`, `QDRANT_URL`, `QDRANT_API_KEY`, and `COLLECTION_NAME` as server secrets/settings. Never put credentials in `VITE_*` variables.

ZeroGPU has a daily GPU allowance; requests stop when that allowance is exhausted. Render Free services sleep after inactivity. No paid inference fallback is configured.

The free deployment uses OpenStreetMap for hospital locations and source websites, OSRM for available drive-time estimates, and hospital website structured data or explicitly named public directory links for physician profiles. Unreadable directories return a clear no-results state; hospital affiliation is not inferred from a health-system directory link. It does not assert equipment availability or fabricated capability percentages. Gemini/You.com generation is not used in this deployment. The original agent-based discovery remains available only in the original deployment mode with its separate provider setup.

`public/demo-cases` contains 12 attributed public chest-X-ray cases from MultiCaRe 3.0.1, separate from the original project's unavailable corpus. Individual selected article licenses are CC BY; see `public/demo-cases/NOTICE.md` for source/collection licensing and attribution. Index this subset with `python scripts/index_demo_data.py` after the model Space is running. The script creates only `chest_xrays_demo`, retains existing points, and never deletes another collection. Publication titles are used as case labels; outcomes have not been curated.
