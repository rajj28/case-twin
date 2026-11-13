"""Create one explicitly free Render web service, with server-only credentials."""
import json
from pathlib import Path
import requests
from check_services import read_env

ROOT=Path(__file__).resolve().parents[1]
env=read_env(ROOT/"backend/.env")
deploy=read_env(ROOT/".deploy.env")
session=requests.Session()
session.headers.update({"Authorization":"Bearer "+deploy["RENDER_API_KEY"],"Accept":"application/json"})
base="https://api.render.com/v1"

def fail(response):
    message=response.text
    for value in list(env.values())+list(deploy.values()):
        if len(value)>12:message=message.replace(value,"[redacted]")
    print(json.dumps({"operation":"deploy_web","status":response.status_code,"message":message[:1000]}),flush=True)
    raise SystemExit(1)

owners=session.get(base+"/owners",timeout=30)
if not owners.ok:fail(owners)
owner=next((row["owner"] for row in owners.json() if row["owner"]["id"]=="tea-cvtb283uibrs73dhaqug"),None)
if not owner:raise RuntimeError("Expected workspace was not found; no service was created.")
listed=session.get(base+"/services",params={"ownerId":owner["id"],"limit":100},timeout=30)
if not listed.ok:fail(listed)
service=next((row["service"] for row in listed.json() if row["service"].get("repo")=="https://github.com/rajj28/case-twin" and row["service"].get("name")=="case-twin"),None)
if service:
    if service.get("serviceDetails",{}).get("plan")!="free":raise RuntimeError("Existing service is not free; refusing to modify it.")
else:
    variables={
        "HF_TOKEN":env["HF_TOKEN"],"HF_SPACE_ID":"rajj28/case-twin-models",
        "HF_SPACE_URL":"https://rajj28-case-twin-models.hf.space",
        "QDRANT_URL":env["QDRANT_URL"],"QDRANT_API_KEY":env["QDRANT_API_KEY"],
        "COLLECTION_NAME":"chest_xrays_demo","DISCOVERY_PROVIDER":"osm",
        "LANGCHAIN_TRACING_V2":"false",
    }
    payload={"type":"web_service","name":"case-twin","ownerId":owner["id"],"repo":"https://github.com/rajj28/case-twin","branch":"main","autoDeployTrigger":"off","envVars":[{"key":k,"value":v} for k,v in variables.items()],"serviceDetails":{"runtime":"docker","plan":"free","region":"oregon","numInstances":1,"healthCheckPath":"/health","envSpecificDetails":{"dockerfilePath":"./Dockerfile.free","dockerContext":"."}}}
    assert payload["serviceDetails"]["plan"]=="free"
    response=session.post(base+"/services",json=payload,timeout=45)
    if not response.ok:fail(response)
    service=response.json().get("service",response.json())
state={"service_id":service["id"],"name":service["name"],"url":service.get("serviceDetails",{}).get("url"),"plan":service.get("serviceDetails",{}).get("plan"),"repo":service.get("repo")}
(ROOT/".deployment/web.json").write_text(json.dumps(state,indent=2),encoding="utf-8")
print(json.dumps(state),flush=True)
