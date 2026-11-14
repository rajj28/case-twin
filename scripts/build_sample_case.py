"""Package the attributed, indexed public case for judge download/upload testing."""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / "public/demo-cases"
records = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
record = next(row for row in records if row["payload"]["provenance"]["pmc_id"] == "PMC2249601")
source = record["payload"]["provenance"]
note = """67-year-old woman with an incidental peripheral opacity in the left lower lung. Previous left mastectomy for breast cancer 13 years earlier, followed by tamoxifen. Non-smoker and otherwise in good general health. Chest X-ray shows a sharply defined, non-cavitating lesion approximately 3 cm across. CT demonstrates a 3 x 4 cm peripheral left lower-lobe mass without mediastinal or axillary lymphadenopathy. Please structure the available case information and retrieve similar published cases.

Source attribution (not additional patient history):
Public case PMC2249601. Authors: {authors}.
Original publication: {url}
Individual article license: CC BY. Dataset: MultiCaRe 3.0.1, https://zenodo.org/records/20416562.
This case is already included in the demo index. Retrieving it verifies the application workflow, not diagnostic accuracy.
""".format(authors=", ".join(source["authors"]), url=source["source_url"])

archive = folder / "CaseTwin-Sample-Case.zip"
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
    bundle.write(folder / record["file"], "CaseTwin-Sample-Xray.webp")
    bundle.writestr("Clinical-note.txt", note)
print(f"Created {archive.name}: X-ray + attributed clinical note ({archive.stat().st_size} bytes).")
