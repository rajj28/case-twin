"""Build a small, attributed CC BY chest-X-ray subset from MultiCaRe 3.0.1."""
import ast
import json
import zipfile
from pathlib import Path
import pyarrow.parquet as pq
from PIL import Image
import io

ROOT = Path(__file__).resolve().parents[1]
data = ROOT / ".local-data"
output = ROOT / "public/demo-cases"
output.mkdir(parents=True, exist_ok=True)
images = json.loads((data / "eligible-images.json").read_text())
metadata = {row["article_id"]: row["article_metadata"] for row in pq.read_table(data / "metadata.parquet").to_pylist()}
cases = {}
for row in pq.read_table(data / "cases.parquet").to_pylist():
    for case in row["cases"] or []:
        cases[case["case_id"]] = case

manifest=[]
seen=set()
with zipfile.ZipFile(data / "PMC2.zip") as archive:
    entries={Path(name).name:name for name in archive.namelist() if not name.endswith("/")}
    for item in images:
        case=cases.get(item["patient_id"])
        article_id=item["patient_id"].split("_")[0]
        info=metadata.get(article_id,{})
        if not case or article_id in seen or info.get("license")!="CC BY":continue
        if item["image_component"]!="undivided" or item["radiology_view"]!="frontal":continue
        if item["file"] not in entries:continue
        raw=archive.read(entries[item["file"]])
        image=Image.open(io.BytesIO(raw))
        if min(image.size)<250:continue
        (output/item["file"]).write_bytes(raw)
        source_url="https://pmc.ncbi.nlm.nih.gov/articles/"+article_id+"/"
        title=info["title"]
        sex=case.get("sex") or case.get("gender") or ""
        age=case.get("age")
        try:labels=ast.literal_eval(item.get("ml_labels_for_supervised_classification") or "[]")
        except (SyntaxError,ValueError):labels=[]
        image_url="/demo-cases/"+item["file"]
        payload={
            "case_id":item["patient_id"],"image_id":item["file_id"],
            "diagnosis":title,"diagnosis_label_source":"publication_title",
            "age":age,"gender":sex,"image_url":image_url,
            "case_text":case.get("case_text", ""),
            "patient":{"age_years":age,"sex":sex,"comorbidities":[],"medications":[]},
            "presentation":{"hpi":case.get("case_text", "")},
            "assessment":{"diagnosis_primary":title},
            "study":{"modality":"X-ray","body_region":"Chest","view_position":"frontal","image_url":image_url,"caption":item["caption"]},
            "summary":{"one_liner":item["caption"],"key_points":[],"red_flags":[]},
            "outcome":{"success":"","detail":"Outcome has not been curated for this demo record. Refer to the source case report."},
            "provenance":{"dataset_name":"MultiCaRe public demo subset","pmc_id":article_id,"pmid":info.get("pmid"),"doi":info.get("doi"),"article_title":title,"journal":info.get("journal"),"year":info.get("year"),"authors":info.get("authors",[]),"license":"CC BY","source_url":source_url,"dataset_source":"https://zenodo.org/records/20416562"},
            "tags":{"ml_labels":labels,"gt_labels":[],"keywords":info.get("keywords",[])}
        }
        manifest.append({"file":item["file"],"payload":payload})
        seen.add(article_id)
        if len(manifest)==12:break
if len(manifest)<6:raise RuntimeError("Insufficient eligible source-linked images in the selected archive.")
(output/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
lines=["# Public demo case attribution","", "Images and case text are from the MultiCaRe dataset, version 3.0.1 (Mauro Nievas Offidani): https://zenodo.org/records/20416562.", "", "MultiCaRe's collection license is CC BY-NC-SA. Only records whose individual article license is CC BY were selected. Each source article and its authors are credited below; consult the source for the exact license terms. This demo subset is separate from the MIT-licensed application code.","", "Diagnosis labels are publication titles. Outcomes and specialist capabilities have not been clinically curated. No generated patient outcome is asserted.",""]
for record in manifest:
    p=record["payload"];v=p["provenance"]
    lines += ["- "+v["article_title"]+" — "+", ".join(v["authors"])+". "+str(v["year"])+". "+v["source_url"]+" License: CC BY."]
(output/"NOTICE.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print(f"Prepared {len(manifest)} source-linked chest-X-ray cases ({sum((output/r['file']).stat().st_size for r in manifest)//1024} KiB of images).")
