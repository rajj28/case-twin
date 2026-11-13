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

Clinical note extraction includes regex heuristics. Ranking scores and profile completeness are not calibrated diagnostic probabilities. Image comparison currently includes simulated fallback bounding boxes when localization fails; these are not verified findings. Hospital search can use generated fallback results; verify them independently. This prototype is for research and demonstration, not clinical decision-making.

## License

MIT. See [LICENSE](LICENSE) for the required copyright and permission notice.
