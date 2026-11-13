"""Idempotently embed the public demo cases with the original MedSigLIP model."""
import json
import os
import sys
import uuid
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/"backend/.env")
sys.path.insert(0,str(ROOT/"backend"))
from hf_space import embed_image

name="chest_xrays_demo"
client=QdrantClient(url=os.environ["QDRANT_URL"],api_key=os.environ["QDRANT_API_KEY"])
if not client.collection_exists(name):
    client.create_collection(name,vectors_config=models.VectorParams(size=1152,distance=models.Distance.COSINE))
else:
    config=client.get_collection(name).config.params.vectors
    if not isinstance(config,models.VectorParams) or config.size!=1152:
        raise RuntimeError("Existing demo collection uses a different vector configuration; it was not changed.")
records=json.loads((ROOT/"public/demo-cases/manifest.json").read_text(encoding="utf-8"))
for i,record in enumerate(records):
    identifier=str(uuid.uuid5(uuid.NAMESPACE_URL,"casetwin:multicare:"+record["file"]))
    if client.retrieve(name,ids=[identifier],with_payload=False):
        print(f"Case {i+1}/{len(records)} already indexed",flush=True);continue
    image=Image.open(ROOT/"public/demo-cases"/record["file"]).convert("RGB")
    vector=embed_image(image)
    client.upsert(name,points=[models.PointStruct(id=identifier,vector=vector,payload=record["payload"])],wait=True)
    print(f"Indexed case {i+1}/{len(records)} with MedSigLIP",flush=True)
print("Demo collection points:",client.get_collection(name).points_count)
