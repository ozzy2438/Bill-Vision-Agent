"""Select 20–30 distinct FATURA v2 templates using official ZIP members, with labels isolated."""
import argparse
import hashlib
import io
import json
import random
import re
import zipfile
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from billvision.config import ROOT

RECORD = "https://zenodo.org/records/10371464"
URL = "https://zenodo.org/api/records/10371464/files/FATURA2.zip/content"
SIZE = 690717658
MD5 = "4c9404462f22c5241eb1a290a02eb2a2"
ATTRIBUTION = "Mahmoud Limam, Marwa Dhiaf, Yousri Kessentini — FATURA Dataset, v2 record 10371464, CC BY 4.0"


class RemoteZip(io.RawIOBase):
    """Read official HTTP byte ranges; ZIP validates each selected member's CRC."""
    def __init__(self):
        self.position = 0
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504], allowed_methods=["GET"])))
        self.cache = b""
        self.cache_start = 0
        self.downloaded = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else SIZE + offset
        if self.position < 0:
            raise ValueError("Negative ZIP seek")
        return self.position

    def read(self, size=-1):
        size = SIZE - self.position if size < 0 else min(size, SIZE - self.position)
        if size <= 0:
            return b""
        start, end = self.position, self.position + size
        if not (self.cache_start <= start and end <= self.cache_start + len(self.cache)):
            fetch_end = min(SIZE, start + max(size, 131072))
            r = self.session.get(URL, headers={"Range": f"bytes={start}-{fetch_end-1}"}, timeout=(15, 120), stream=True)
            with r:
                r.raise_for_status()
                if r.status_code != 206 or r.headers.get("Content-Range") != f"bytes {start}-{fetch_end-1}/{SIZE}":
                    raise RuntimeError("Official server did not return the requested byte range. Use --archive with a complete local ZIP.")
                self.cache = r.content
                if len(self.cache) != fetch_end - start:
                    raise RuntimeError("Truncated archive range")
            self.cache_start = start
            self.downloaded += len(self.cache)
        result = self.cache[start-self.cache_start:end-self.cache_start]
        self.position = end
        return result

    def close(self):
        self.session.close()
        super().close()


def save_unchanged(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError(f"Refusing to overwrite a different existing file: {path}")
    if not path.exists():
        path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Complete local FATURA2.zip; official MD5 is verified")
    parser.add_argument("--download-all", type=Path, help="Download and verify the complete 690,717,658-byte official ZIP at this path")
    parser.add_argument("--count", type=int, default=25, choices=range(20,31), metavar="20..30")
    parser.add_argument("--background", choices=["white", "colored"], default="white")
    args = parser.parse_args()
    existing_manifest = ROOT / "data/fatura/selection.json"
    if existing_manifest.exists() and not args.archive and not args.download_all:
        existing = json.loads(existing_manifest.read_text())
        rows = existing.get("selection", [])
        if len(rows) != args.count or any(r["background"] != args.background for r in rows):
            raise RuntimeError("An existing selection has different parameters; preserve it before preparing a different selection")
        for row in rows:
            for path, expected in [(ROOT / "data/fatura/documents" / row["document"], row["sha256"]), (ROOT / "reference_annotations/fatura_v2" / (row["id"] + ".json"), row["annotation_sha256"])]:
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    raise RuntimeError("Existing selection is missing files or has changed; inspect it before replacing")
        print(f"Verified existing {len(rows)}-case FATURA selection and isolated labels; no download needed.")
        return
    if args.download_all:
        print(f"Full archive: {SIZE:,} bytes (658.72 MiB). Source: {URL}", flush=True)
        args.download_all.parent.mkdir(parents=True, exist_ok=True)
        if not args.download_all.exists():
            temporary = args.download_all.with_suffix(".zip.part")
            with requests.get(URL, stream=True, timeout=(15,120)) as response:
                response.raise_for_status()
                with temporary.open("wb") as target:
                    for chunk in response.iter_content(1024*1024):
                        target.write(chunk)
            with temporary.open("rb") as f:
                if hashlib.file_digest(f, "md5").hexdigest() != MD5:
                    raise RuntimeError("Downloaded archive fails the official MD5 checksum")
            temporary.rename(args.download_all)
        args.archive = args.download_all
    if args.archive:
        with args.archive.open("rb") as f:
            if hashlib.file_digest(f,"md5").hexdigest() != MD5:
                raise RuntimeError("Local archive fails the official FATURA v2 MD5 checksum")
        source = args.archive.open("rb")
        integrity = "Full official MD5 verified; member CRC checked by zipfile"
    else:
        source = RemoteZip()
        integrity = "HTTPS selective ZIP access; selected member CRC verified. Full-archive MD5 was not evaluated."
        print(f"Official archive is {SIZE:,} bytes; downloading only ZIP directory and {args.count} selected image/label pairs.", flush=True)
    with source, zipfile.ZipFile(source) as archive:
        prefix = "invoices_dataset_final/" + ("images/" if args.background == "white" else "colored_images/")
        groups = {}
        for name in archive.namelist():
            match = re.fullmatch(re.escape(prefix) + r"Template(\d+)_Instance(\d+)\.jpg", name)
            if match:
                groups.setdefault(int(match[1]), []).append(name)
        if len(groups) < args.count:
            raise RuntimeError("Expected FATURA v2 layout not found; no guess-based mapping was made")
        randomizer = random.Random(42)
        templates = sorted(randomizer.sample(sorted(groups), args.count))
        selection = []
        for template in templates:
            member = randomizer.choice(sorted(groups[template]))
            identity = Path(member).stem
            label = "invoices_dataset_final/Annotations/Original_Format/" + identity + ".json"
            image_bytes, label_bytes = archive.read(member), archive.read(label)
            json.loads(label_bytes)  # Validate labels only in this preparation command.
            save_unchanged(ROOT / "data/fatura/documents" / (identity + ".jpg"), image_bytes)
            save_unchanged(ROOT / "reference_annotations/fatura_v2" / (identity + ".json"), label_bytes)
            selection.append({"id": identity, "template": template, "background": args.background, "document": identity + ".jpg", "sha256": hashlib.sha256(image_bytes).hexdigest(), "annotation_sha256": hashlib.sha256(label_bytes).hexdigest()})
            print(f"Selected {identity}", flush=True)
    manifest = {"source": RECORD, "archive_url": URL, "archive_size": SIZE, "published_md5": MD5,
                "attribution": ATTRIBUTION, "license": "CC BY 4.0", "integrity": integrity,
                "synthetic_data": True, "company_records_derived_from_labels": False,
                "unique_invoice_cases": len(selection), "distinct_templates": len(templates), "selection": selection}
    (ROOT / "data/fatura/selection.json").write_text(json.dumps(manifest, indent=2))
    print(f"Prepared {len(selection)} distinct invoice cases / templates; labels isolated in reference_annotations/fatura_v2.")
    if isinstance(source, RemoteZip):
        print(f"Selective bytes downloaded: {source.downloaded:,}; full archive was not required.")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        raise SystemExit(f"Official FATURA access failed ({type(exc).__name__}). Download {URL} from {RECORD}, then run --archive /path/to/FATURA2.zip. No substitute dataset was used.")
