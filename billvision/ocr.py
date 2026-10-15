import io
import warnings
from functools import lru_cache
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from billvision.config import settings


def inspect_file(data: bytes):
    if not data or len(data) > settings.max_file_mb * 1024 * 1024:
        raise ValueError(f"File must be between 1 byte and {settings.max_file_mb} MB")
    if data.startswith(b"%PDF-"):
        try:
            pdf = PdfReader(io.BytesIO(data), strict=True)
            if pdf.is_encrypted:
                raise ValueError("Encrypted PDFs are unsupported")
            pages = len(pdf.pages)
        except Exception as exc:
            raise ValueError("Invalid or encrypted PDF") from exc
        if not 1 <= pages <= settings.max_pages:
            raise ValueError(f"PDF must contain 1–{settings.max_pages} pages")
        return "application/pdf", ".pdf"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as img:
                if img.format not in {"PNG", "JPEG"}:
                    raise ValueError("Only PDF, PNG and JPEG are supported")
                if img.width * img.height > settings.max_image_pixels:
                    raise ValueError("Image pixel limit exceeded")
                if getattr(img, "n_frames", 1) != 1:
                    raise ValueError("Multi-frame images are unsupported")
                kind = img.format
                img.verify()
        return ("image/png", ".png") if kind == "PNG" else ("image/jpeg", ".jpg")
    except Exception as exc:
        raise ValueError("Invalid image, unsupported type or image limit exceeded") from exc


@lru_cache(maxsize=1)
def converter():
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption

    if not settings.docling_artifacts_path.is_dir():
        raise RuntimeError("Docling models missing; run uv run python -m scripts.download_models")
    options = PdfPipelineOptions(
        artifacts_path=settings.docling_artifacts_path,
        do_ocr=True,
        do_table_structure=False,
        ocr_options=TesseractCliOcrOptions(lang=["eng"], force_full_page_ocr=True),
    )
    return DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=options),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=options),
    })


def read_document(path: Path):
    result = converter().convert(path, max_num_pages=settings.max_pages, raises_on_error=True)
    if result.status.value != "success":
        raise RuntimeError(f"Docling conversion did not complete: {result.status.value}")
    evidence = []
    for item, _level in result.document.iterate_items():
        text = getattr(item, "text", None)
        if not text or not text.strip():
            continue
        for prov in getattr(item, "prov", []):
            evidence.append({
                "id": f"p{prov.page_no}-e{len(evidence) + 1}",
                "page": prov.page_no,
                "text": text,
                "bbox": prov.bbox.model_dump(mode="json") if prov.bbox else None,
            })
    if not evidence:
        raise RuntimeError("OCR produced no usable text; manual review is required")
    return evidence, result.document.model_dump(mode="json")
