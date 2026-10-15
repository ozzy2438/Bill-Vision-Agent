"""Download only the selected Docling layout model; Tesseract English is system-provided."""
import hashlib
import json
from datetime import datetime, timezone

from huggingface_hub import HfApi, snapshot_download
from docling.datamodel.pipeline_options import LayoutOptions

from billvision.config import settings


def main():
    model = LayoutOptions().model_spec
    destination = settings.docling_artifacts_path
    marker = destination / "download-complete.json"
    if marker.exists():
        manifest = json.loads(marker.read_text())
        if all((destination / name).is_file() and hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest for name, digest in manifest["sha256"].items()):
            print("Docling artifacts already present and checksums verified.")
            return
        raise SystemExit("Existing model files fail checksum verification; inspect before replacing them.")
    info = HfApi().model_info(model.repo_id, revision="8f39ad3c0b4c58e9c2d2c84a38465abf757272d8", files_metadata=True)
    print(f"Downloading {model.repo_id} at commit {info.sha}", flush=True)
    path = destination / model.model_repo_folder
    snapshot_download(repo_id=model.repo_id, revision=info.sha, local_dir=path)
    for sibling in info.siblings:
        if sibling.lfs:
            with (path / sibling.rfilename).open("rb") as artifact:
                if hashlib.file_digest(artifact, "sha256").hexdigest() != sibling.lfs.sha256:
                    raise RuntimeError("Model artifact does not match its published SHA-256")
    files = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob("*") if p.is_file() and ".cache" not in p.parts}
    metadata = {"repository": model.repo_id, "revision": info.sha, "license": (info.card_data.to_dict() if info.card_data else {}).get("license", "Check downloaded model card"), "downloaded_at": datetime.now(timezone.utc).isoformat(), "sha256": files}
    marker.write_text(json.dumps(metadata, indent=2))
    print(json.dumps({k:v for k,v in metadata.items() if k != "sha256"}, indent=2))


if __name__ == "__main__":
    main()
