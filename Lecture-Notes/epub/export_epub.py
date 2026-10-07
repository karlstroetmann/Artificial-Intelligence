#!/usr/bin/env python3
"""Convert the lecture notes, validate the book, then publish it atomically."""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from typing import TextIO
import xml.etree.ElementTree as ET
import zipfile

from publication import Publication


def tool_environment() -> dict[str, str]:
    tools = ("tex4ebook", "bibtex", "makeindex", "dvisvgm", "mutool", "rsvg-convert", "gs", "epubcheck")
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        raise RuntimeError("Missing EPUB tools: " + ", ".join(missing) + ". See README.md for setup.")
    environment = os.environ.copy()
    # Homebrew's Ghostscript library is outside dvisvgm's default search path.
    library = Path(shutil.which("gs")).resolve().parent.parent / "lib/libgs.dylib"
    if library.is_file():
        environment.setdefault("LIBGS", str(library))
    return environment


def prepare_stage(source: Path) -> Path:
    stage = source.parent / ".build/epub"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    extensions = {".tex", ".bib", ".tfm", ".mf", ".sty", ".fd", ".enc", ".ttf"}
    for file in source.parent.iterdir():
        if file.is_file() and file.suffix in extensions:
            shutil.copy2(file, stage / file.name)
            if file.suffix == ".tex":
                # Reflow retains reference links, but has no print page numbers.
                content = re.sub(r"\s+on\s+page\s+\\pageref\{[^}]+\}", "", file.read_text(encoding="utf-8"))
                (stage / file.name).write_text(content, encoding="utf-8")
    shutil.copytree(source.parent / "Figures", stage / "Figures")
    for name in ("reader.css", "cover.svg", "ebook.cfg", "ebook.mk4"):
        shutil.copy2(Path(__file__).parent / name, stage / name)
    return stage


def embedded_png_svg(data: bytes) -> bytes:
    """Preserve PNG pixels in legacy assets named .pdf (such as newman.pdf)."""
    width, height = struct.unpack(">II", data[16:24])
    image = base64.b64encode(data).decode("ascii")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<image width="{width}" height="{height}" xlink:href="data:image/png;base64,{image}"/>
</svg>'''.encode("utf-8")


def convert_figures(stage: Path, log: TextIO, environment: dict[str, str]) -> None:
    for figure in sorted((stage / "Figures").rglob("*")):
        extension = figure.suffix.lower()
        if extension not in {".pdf", ".eps"}:
            continue
        if extension == ".pdf":
            with figure.open("rb") as stream:
                is_png = stream.read(8) == b"\x89PNG\r\n\x1a\n"
            if is_png:
                vector = embedded_png_svg(figure.read_bytes())
                for suffix in ("-1.svg", "-.svg"):
                    figure.with_name(figure.stem + suffix).write_bytes(vector)
                continue
            vector = figure.with_name(figure.stem + "-1.svg")
            # Preserve embedded raster artwork, including the MNIST digit grid.
            subprocess.run(["mutool", "draw", "-F", "svg", "-o", str(vector), str(figure), "1"],
                           stdout=log, stderr=subprocess.STDOUT, env=environment, check=True)
            # MuPDF writes PDF point dimensions as unitless SVG pixels.
            svg = ET.parse(vector)
            for dimension in ("width", "height"):
                svg.getroot().set(dimension, svg.getroot().attrib[dimension] + "pt")
            ET.register_namespace("", "http://www.w3.org/2000/svg")
            ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
            svg.write(vector, encoding="utf-8", xml_declaration=True)
            shutil.copy2(vector, figure.with_name(figure.stem + "-.svg"))
        else:
            subprocess.run(["dvisvgm", "--no-fonts", "--exact", "--eps",
                            f"--output={figure.with_suffix('.svg')}", str(figure)],
                           stdout=log, stderr=subprocess.STDOUT, env=environment, check=True)


def convert_source(source: Path, stage: Path, environment: dict[str, str]) -> Path:
    log = stage / "export.log"
    print(f"Building native EPUB in {stage}; log: {log}", flush=True)
    with log.open("w", encoding="utf-8") as output:
        # Keep the editable artwork; embed a raster cover for reader compatibility.
        subprocess.run(["rsvg-convert", "--output", str(stage / "cover.png"), str(stage / "cover.svg")],
                       stdout=output, stderr=subprocess.STDOUT, env=environment, check=True)
        convert_figures(stage, output, environment)
        subprocess.run(["tex4ebook", "-f", "epub3+dvisvgm_hashes", "-s", "-c", "ebook.cfg",
                        "-e", "ebook.mk4", source.name], cwd=stage, stdout=output,
                       stderr=subprocess.STDOUT, env=environment, check=True)
    transcript = (stage / source.with_suffix(".log").name).read_text(encoding="utf-8")
    if re.search(r"^!|LaTeX Warning: (?:Citation|Reference).*undefined|There were undefined references",
                 transcript, re.MULTILINE):
        raise RuntimeError("LaTeX reported errors or unresolved references in the final EPUB pass.")
    if re.search(r"XML DOM parsing.*failed:", log.read_text(encoding="utf-8")):
        raise RuntimeError("TeX4ht required HTML repair; refusing to publish potentially altered content.")
    return stage / source.with_suffix(".epub").name


def validate(book: Publication, path: Path) -> None:
    book.check_reading_policy()
    subprocess.run(["epubcheck", "--failonwarnings", str(path)], check=True)


def build(source: Path) -> None:
    environment = tool_environment()
    source = source.resolve(strict=True)
    stage = prepare_stage(source)
    epub = convert_source(source, stage, environment)
    book = Publication.read(epub)
    book.adapt_for_reading()
    book.write(epub)
    validate(book, epub)
    # Failed conversion or validation retains the previous downloadable book.
    destination = source.with_suffix(".epub")
    temporary = destination.with_suffix(".epub.tmp")
    shutil.copy2(epub, temporary)
    temporary.replace(destination)
    print(f"Exported {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="LaTeX source, or an existing EPUB with --check")
    parser.add_argument("--check", action="store_true", help="Recheck an EPUB without rebuilding it")
    args = parser.parse_args()
    try:
        if args.check:
            validate(Publication.read(args.path), args.path)
        else:
            build(args.path)
    except (OSError, RuntimeError, subprocess.CalledProcessError, ET.ParseError,
            zipfile.BadZipFile, KeyError, ValueError) as error:
        print(f"EPUB {'validation' if args.check else 'export'} failed: {error}", file=sys.stderr)
        if not args.check:
            print("See .build/epub/export.log for diagnostics.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
