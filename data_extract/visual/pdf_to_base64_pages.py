from pathlib import Path
import argparse
import base64
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent

# script is in: root/data_extract/visual
# PDFs are in:  root/pdf_src
ROOT_DIR = SCRIPT_DIR.parents[1]
PDF_SRC_DIR = ROOT_DIR / "pdf_src"

# Outputs go here:
# root/data_extract/visual/images
IMAGES_OUTPUT_DIR = SCRIPT_DIR / "images"


def render_page_to_jpg_bytes(page: fitz.Page, dpi: int = 200, quality: int = 95) -> bytes:
    """
    Render a PDF page to JPG bytes.
    """

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    pixmap = page.get_pixmap(
        matrix=matrix,
        colorspace=fitz.csRGB,
        alpha=False,
    )

    image = Image.frombytes(
        mode="RGB",
        size=(pixmap.width, pixmap.height),
        data=pixmap.samples,
    )

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def pdf_pages_to_base64_and_jpg(
    pdf_path: Path,
    output_root: Path = IMAGES_OUTPUT_DIR,
    dpi: int = 200,
    jpg_quality: int = 95,
    include_data_uri: bool = False,
) -> Path:
    """
    For one PDF:
    - creates a folder named after the PDF inside /images
    - saves base64-encoded JPGs inside /b64
    - saves normal JPG screenshots inside /jpg

    Example:
        root/data_extract/visual/images/my_pdf/b64/page_001.b64
        root/data_extract/visual/images/my_pdf/jpg/page_001.jpg
    """

    pdf_path = Path(pdf_path).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Input file must be a PDF: {pdf_path}")

    pdf_output_folder = output_root / pdf_path.stem
    b64_folder = pdf_output_folder / "b64"
    jpg_folder = pdf_output_folder / "jpg"

    b64_folder.mkdir(parents=True, exist_ok=True)
    jpg_folder.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as doc:
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)

            jpg_bytes = render_page_to_jpg_bytes(
                page=page,
                dpi=dpi,
                quality=jpg_quality,
            )

            page_name = f"page_{page_index + 1:03d}"

            # Save JPG screenshot for human checking
            jpg_output_path = jpg_folder / f"{page_name}.jpg"
            jpg_output_path.write_bytes(jpg_bytes)

            # Save base64 encoding of that same JPG
            b64_string = base64.b64encode(jpg_bytes).decode("utf-8")

            if include_data_uri:
                b64_string = f"data:image/jpeg;base64,{b64_string}"

            b64_output_path = b64_folder / f"{page_name}.b64"
            b64_output_path.write_text(b64_string, encoding="utf-8")

    return pdf_output_folder


def process_single_pdf(
    pdf_filename: str,
    dpi: int = 200,
    jpg_quality: int = 95,
    include_data_uri: bool = False,
) -> Path:
    """
    Process one PDF from root/pdf_src by filename.
    """

    pdf_path = PDF_SRC_DIR / pdf_filename

    return pdf_pages_to_base64_and_jpg(
        pdf_path=pdf_path,
        output_root=IMAGES_OUTPUT_DIR,
        dpi=dpi,
        jpg_quality=jpg_quality,
        include_data_uri=include_data_uri,
    )


def process_all_pdfs(
    dpi: int = 200,
    jpg_quality: int = 95,
    include_data_uri: bool = False,
) -> list[Path]:
    """
    Process every PDF inside root/pdf_src.
    Each PDF gets its own folder inside root/data_extract/visual/images.
    """

    if not PDF_SRC_DIR.exists():
        raise FileNotFoundError(f"PDF source folder not found: {PDF_SRC_DIR}")

    pdf_files = sorted(PDF_SRC_DIR.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in: {PDF_SRC_DIR}")

    output_folders = []

    for pdf_path in pdf_files:
        output_folder = pdf_pages_to_base64_and_jpg(
            pdf_path=pdf_path,
            output_root=IMAGES_OUTPUT_DIR,
            dpi=dpi,
            jpg_quality=jpg_quality,
            include_data_uri=include_data_uri,
        )
        output_folders.append(output_folder)

    return output_folders


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF pages into JPG screenshots and base64-encoded JPG files."
    )

    parser.add_argument(
        "--pdf",
        type=str,
        help="PDF filename inside root/pdf_src, for example: my_file.pdf",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all PDFs inside root/pdf_src",
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Render DPI. Default: 200",
    )

    parser.add_argument(
        "--jpg-quality",
        type=int,
        default=95,
        help="JPG quality from 1 to 95. Default: 95",
    )

    parser.add_argument(
        "--data-uri",
        action="store_true",
        help="Save base64 strings with data:image/jpeg;base64 prefix",
    )

    args = parser.parse_args()

    # Default behavior:
    # running `python pdf_to_base64_pages.py`
    # will process all PDFs in root/pdf_src
    if args.all or not args.pdf:
        output_folders = process_all_pdfs(
            dpi=args.dpi,
            jpg_quality=args.jpg_quality,
            include_data_uri=args.data_uri,
        )

        for folder in output_folders:
            print(f"Saved PDF pages to: {folder}")

    else:
        output_folder = process_single_pdf(
            pdf_filename=args.pdf,
            dpi=args.dpi,
            jpg_quality=args.jpg_quality,
            include_data_uri=args.data_uri,
        )

        print(f"Saved PDF pages to: {output_folder}")


if __name__ == "__main__":
    main()