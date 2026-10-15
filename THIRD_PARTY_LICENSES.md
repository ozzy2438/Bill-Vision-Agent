# Separate software, model and data licenses

## Software

Application source is MIT (`LICENSE`). `uv.lock` fixes the complete Python dependency graph and artifact hashes. `docs/software-license-inventory.json` records installed distribution versions and their declared licenses. The distributions' own notices remain authoritative.

Main components: Docling MIT; FastAPI MIT; Pydantic MIT; Streamlit Apache-2.0; psycopg LGPL-3.0; PostgreSQL PostgreSQL License; Ollama MIT; Tesseract Apache-2.0; PyTorch BSD-3-Clause; Pillow HPND; ReportLab BSD; pypdf BSD-3-Clause. Docling's installed EasyOCR dependency is not selected or used for OCR, and its models are not downloaded.

## Downloaded models

- **Qwen2.5-7B-Instruct**, local Ollama `qwen2.5:7b` quantized package: Apache-2.0. Model card https://huggingface.co/Qwen/Qwen2.5-7B-Instruct ; package https://ollama.com/library/qwen2.5:7b . The inspected official package's model layer is 4,683,073,952 bytes, SHA-256 `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`. Ollama verifies pulled layers. Runtime package metadata is recorded in `docs/model-manifest.json` after a successful installation.
- **Docling layout Heron** (`ds4sd/docling-layout-heron`): Apache-2.0, as declared in its downloaded model card. Pinned commit `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8`. This is layout analysis, not an additional OCR engine. Source: https://huggingface.co/ds4sd/docling-layout-heron . The download command verifies published LFS SHA-256 values and records local hashes and the revision in `models/docling/download-complete.json`.
- **Tesseract English `eng.traineddata`**: Apache-2.0; installed system model, source https://github.com/tesseract-ocr/tessdata . Its version/location/hash are recorded with the model manifest. This is the single selected OCR engine.

No paid API, model fine-tuning or alternate model comparison is included. Source-code licenses do not replace model-weight licenses.

## Data

FATURA v2 is CC BY 4.0 with author attribution in `DATA_SOURCES.md`. Independent generated demo PDFs/company data are CC0 1.0. Dataset licenses are separate from application and model licenses.
