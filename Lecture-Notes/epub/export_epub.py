#!/usr/bin/env python3
"""Build and validate a native EPUB without sharing PDF auxiliary files."""

from __future__ import annotations

import argparse
import base64
import os
import posixpath
import re
import shutil
import subprocess
import struct
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile

from check_epub import EPUB_NS, OPF_NS, XHTML_NS, validate


def xhtml(tag: str) -> str:
    return f"{{{XHTML_NS}}}{tag}"


def plain_text(element: ET.Element) -> str:
    """Include formula alternatives when deriving a figure's description."""
    def text(node: ET.Element) -> str:
        content = node.get("alt", "") if node.tag == xhtml("img") else node.text or ""
        return content + "".join(text(child) + (child.tail or "") for child in node)
    return " ".join(text(element).split())


def embedded_png_svg(data: bytes) -> bytes:
    """Preserve raster bytes in legacy assets named .pdf (e.g. newman.pdf)."""
    width, height = struct.unpack(">II", data[16:24])
    svg = ET.Element("svg", {"xmlns": "http://www.w3.org/2000/svg",
                              "xmlns:xlink": "http://www.w3.org/1999/xlink",
                              "width": str(width), "height": str(height),
                              "viewBox": f"0 0 {width} {height}"})
    ET.SubElement(svg, "image", {"width": str(width), "height": str(height),
                                 "xlink:href": "data:image/png;base64," + base64.b64encode(data).decode("ascii")})
    return ET.tostring(svg, encoding="utf-8", xml_declaration=True)


def add_footnote_backlinks(documents: dict[str, ET.Element]) -> None:
    """Let readers without note popups return to each reference in the text."""
    targets = {(filename, element.get("id")): element
               for filename, document in documents.items()
               for element in document.iter() if element.get("id")}
    for filename, document in documents.items():
        used_ids = {element.get("id") for element in document.iter()}
        for number, reference in enumerate(document.iter(xhtml("a")), start=1):
            if "noteref" not in reference.get(f"{{{EPUB_NS}}}type", "").split():
                continue
            href = urlsplit(reference.get("href", ""))
            if href.scheme or href.netloc:
                continue
            target_file = posixpath.normpath(posixpath.join(posixpath.dirname(filename),
                                                            unquote(href.path))) if href.path else filename
            note = targets.get((target_file, unquote(href.fragment)))
            if note is None:
                continue  # The content validator reports missing targets.
            reference_id = reference.get("id") or f"epub-noteref-{number}"
            while not reference.get("id") and reference_id in used_ids:
                reference_id += "-ref"
            reference.set("id", reference_id)
            used_ids.add(reference_id)
            return_path = "" if target_file == filename else posixpath.relpath(
                filename, posixpath.dirname(target_file))
            paragraph = ET.SubElement(note, xhtml("p"), {"class": "epub-note-return"})
            ET.SubElement(paragraph, xhtml("a"), {
                "href": quote(return_path + "#" + reference_id, safe="/#:"),
                "role": "doc-backlink", "aria-label": "Return to the footnote reference",
            }).text = "Return to text"


def describe_figures(document: ET.Element) -> None:
    """Replace converter placeholders with the nearest authored caption."""
    parents = {child: parent for parent in document.iter() for child in parent}
    for image in document.iter(xhtml("img")):
        if image.get("alt", "").strip() not in {"", "PIC", "[Picture]"}:
            continue
        if posixpath.basename(urlsplit(image.get("src", "")).path) == "dhbw-logo.svg":
            image.set("alt", "DHBW logo")
            continue
        ancestor = parents.get(image)
        while ancestor is not None:
            if ancestor.tag == xhtml("figure") or {"figure", "subfigure"}.intersection(
                ancestor.get("class", "").split()
            ):
                caption = next((child for child in ancestor
                                if child.tag == xhtml("figcaption")
                                or "caption" in child.get("class", "").split()), None)
                if caption is not None and plain_text(caption):
                    image.set("alt", plain_text(caption))
                    break
            ancestor = parents.get(ancestor)


def polish_publication(path: Path) -> None:
    """Adapt print presentation without changing authored text or link targets."""
    with zipfile.ZipFile(path) as archive:
        files = {item.filename: archive.read(item) for item in archive.infolist()}
    container = ET.fromstring(files["META-INF/container.xml"])
    package_path = next(container.iterfind(".//{*}rootfile")).attrib["full-path"]
    package = ET.fromstring(files[package_path])
    directory = posixpath.dirname(package_path)
    manifest = package.find(f"{{{OPF_NS}}}manifest")
    spine = package.find(f"{{{OPF_NS}}}spine")
    assert manifest is not None and spine is not None
    documents: dict[str, ET.Element] = {}

    for item in manifest:
        if item.get("media-type") != "application/xhtml+xml":
            continue
        filename = posixpath.join(directory, unquote(item.attrib["href"]))
        document = ET.fromstring(files[filename])
        documents[filename] = document
        for element in document.iter():
            href = element.get("href")
            if href and urlsplit(href).scheme:
                element.set("href", quote(href, safe="%:/?#[]@!$&'()*+,;="))
            style = element.get("style")
            if style:
                # Fixed print colors can disappear in reader themes. Bold/italic
                # and the actual source text survive; colors are presentation.
                if re.search(r"(?:^|;)\s*color\s*:", style):
                    element.set("class", (element.get("class", "") + " epub-emphasis").strip())
                style = re.sub(r"(?:^|;)\s*(?:color|background(?:-color)?)\s*:[^;]*", "", style)
                if style.strip("; "):
                    element.set("style", style.strip("; "))
                else:
                    element.attrib.pop("style")

        describe_figures(document)

        # TeX4ht uses nonbreaking spaces in listings. Real spaces preserve
        # indentation under pre-wrap and allow readable wrapping and copying.
        for listing in document.iter(xhtml("pre")):
            for element in listing.iter():
                if element.text:
                    element.text = element.text.replace("\u00a0", " ")
                if element.tail:
                    element.tail = element.tail.replace("\u00a0", " ")

        # TeX4ht emits the list of figures as spans and separators in an ol.
        # Preserve every entry and target while giving it valid list semantics.
        for listing in document.findall(f".//{xhtml('nav')}/{xhtml('ol')}"):
            for entry in list(listing):
                if "lofToc" in entry.get("class", "").split():
                    entry.tag = xhtml("li")
                elif entry.tag == xhtml("br"):
                    listing.remove(entry)

        for parent in list(document.iter()):
            for position, element in enumerate(list(parent)):
                if element.tag == xhtml("table"):
                    wrapper = ET.Element(xhtml("div"), {"class": "epub-table"})
                    wrapper.tail, element.tail = element.tail, None
                    parent.remove(element)
                    parent.insert(position, wrapper)
                    wrapper.append(element)

        for image in document.iter(xhtml("img")):
            if not {"math", "math-display"}.intersection(image.get("class", "").split()):
                continue
            source = posixpath.normpath(posixpath.join(posixpath.dirname(filename),
                                                      unquote(urlsplit(image.attrib["src"]).path)))
            svg = ET.fromstring(files[source])
            width = re.fullmatch(r"([\d.]+)pt", svg.get("width", ""))
            height = re.fullmatch(r"([\d.]+)pt", svg.get("height", ""))
            if width and height:
                # dvisvgm scales the 11pt source by 1.4. em units then follow
                # the reader's text-size setting, including inline formulas.
                image.set("style", f"width:{float(width[1]) / 15.4:.4f}em;"
                          f"height:{float(height[1]) / 15.4:.4f}em")

        # Even authors' inline arrays can be wider than a phone at large type.
        # Constrain the container, keep glyphs at text size and allow scrolling.
        for parent in list(document.iter()):
            if "epub-math" in parent.get("class", "").split():
                continue  # Inline math already carries its TeX-derived baseline.
            for position, image in enumerate(list(parent)):
                if image.tag != xhtml("img") or not {"math", "math-display"}.intersection(
                    image.get("class", "").split()
                ):
                    continue
                wrapper = ET.Element(xhtml("span"), {"class": "epub-math"})
                wrapper.tail, image.tail = image.tail, None
                parent.remove(image)
                parent.insert(position, wrapper)
                wrapper.append(image)

    add_footnote_backlinks(documents)
    cover_item = next(item for item in manifest
                      if "cover-image" in item.get("properties", "").split())
    cover_href = cover_item.attrib["href"]
    cover = ET.Element(xhtml("html"), {"lang": "en"})
    head = ET.SubElement(cover, xhtml("head"))
    ET.SubElement(head, xhtml("title")).text = "Cover"
    ET.SubElement(head, xhtml("link"), {"rel": "stylesheet", "href": "reader.css", "type": "text/css"})
    body = ET.SubElement(cover, xhtml("body"), {"class": "epub-cover"})
    section = ET.SubElement(body, xhtml("section"), {f"{{{EPUB_NS}}}type": "cover"})
    title = package.find("{*}metadata/{*}title")
    ET.SubElement(section, xhtml("img"), {"src": cover_href, "alt": "Cover: " + (title.text or "")})
    documents[posixpath.join(directory, "cover.xhtml")] = cover
    ET.SubElement(manifest, f"{{{OPF_NS}}}item", {"id": "ebook-cover", "href": "cover.xhtml",
                                                "media-type": "application/xhtml+xml"})
    spine.insert(0, ET.Element(f"{{{OPF_NS}}}itemref", {"idref": "ebook-cover"}))

    nav_item = next(item for item in manifest if "nav" in item.get("properties", "").split())
    if not any(item.get("idref") == nav_item.attrib["id"] for item in spine):
        spine.insert(1, ET.Element(f"{{{OPF_NS}}}itemref", {"idref": nav_item.attrib["id"]}))
    navigation = documents[posixpath.join(directory, nav_item.attrib["href"])]
    nav_body = navigation.find(xhtml("body"))
    assert nav_body is not None
    landmarks = ET.SubElement(nav_body, xhtml("nav"), {f"{{{EPUB_NS}}}type": "landmarks",
                                                       "hidden": "hidden"})
    ET.SubElement(landmarks, xhtml("h2")).text = "Book landmarks"
    entries = ET.SubElement(landmarks, xhtml("ol"))
    for kind, href, label in [("cover", "cover.xhtml", "Cover"),
                               ("toc", nav_item.attrib["href"], "Contents")]:
        entry = ET.SubElement(entries, xhtml("li"))
        ET.SubElement(entry, xhtml("a"), {f"{{{EPUB_NS}}}type": kind, "href": href}).text = label

    ET.register_namespace("", XHTML_NS)
    ET.register_namespace("epub", EPUB_NS)
    for filename, document in documents.items():
        files[filename] = ET.tostring(document, encoding="utf-8", xml_declaration=True)
    ET.register_namespace("", OPF_NS)
    ET.register_namespace("dc", "http://purl.org/dc/elements/1.1/")
    files[package_path] = ET.tostring(package, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", files.pop("mimetype"), compress_type=zipfile.ZIP_STORED)
        for filename, content in files.items():
            archive.writestr(filename, content)


def build(source: Path) -> None:
    tools = ("tex4ebook", "bibtex", "makeindex", "dvisvgm", "mutool", "gs", "epubcheck")
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        raise RuntimeError("Missing EPUB tools: " + ", ".join(missing) + ". See README.md for setup.")
    source = source.resolve(strict=True)
    settings = Path(__file__).resolve().parent
    environment = os.environ.copy()
    # TeX Live's macOS dvisvgm loads Ghostscript dynamically. Homebrew keeps
    # it next to the gs executable, outside the loader's default search path.
    gs_library = Path(shutil.which("gs")).resolve().parent.parent / "lib" / "libgs.dylib"
    if "LIBGS" not in environment and gs_library.is_file():
        environment["LIBGS"] = str(gs_library)
    stage = source.parent / ".build" / "epub"
    # A fresh stage prevents removed chapters/assets surviving in the ZIP.
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for extension in ("*.tex", "*.bib", "*.tfm", "*.mf", "*.sty", "*.fd", "*.enc", "*.ttf"):
        for file in source.parent.glob(extension):
            shutil.copy2(file, stage / file.name)
            if file.suffix == ".tex":
                # Figure/equation links already navigate to the referenced
                # location. Print page numbers have no meaning in reflow.
                content = file.read_text()
                content = re.sub(r"\s+on\s+page\s+\\pageref\{[^}]+\}", "", content)
                (stage / file.name).write_text(content)
    shutil.copytree(source.parent / "Figures", stage / "Figures")
    for name in ("reader.css", "cover.svg", "ebook.cfg", "ebook.mk4"):
        shutil.copy2(settings / name, stage / name)
    log = stage / "export.log"
    print(f"Building native EPUB in {stage}; log: {log}", flush=True)
    with log.open("w") as output:
        # The batched math renderer skips TeX4ht's external graphics converter.
        # Convert figures first, with the exact names requested by TeX4ht.
        for figure in sorted((stage / "Figures").rglob("*")):
            if figure.suffix.lower() not in {".pdf", ".eps"}:
                continue
            if figure.suffix.lower() == ".pdf":
                data = figure.read_bytes()
                if data.startswith(b"\x89PNG\r\n\x1a\n"):
                    vector = embedded_png_svg(data)
                    figure.with_name(figure.stem + "-1.svg").write_bytes(vector)
                    figure.with_name(figure.stem + "-.svg").write_bytes(vector)
                    continue
                vector = figure.with_name(figure.stem + "-1.svg")
                # MuPDF preserves embedded raster artwork that dvisvgm's PDF
                # converter can silently omit, such as the MNIST digit grid.
                command = ["mutool", "draw", "-F", "svg", "-o", str(vector), str(figure), "1"]
                subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, env=environment, check=True)
                # MuPDF writes PDF point dimensions as unitless SVG pixels.
                # Keep the physical sizing used by the previous converter.
                svg = ET.parse(vector)
                for dimension in ("width", "height"):
                    svg.getroot().set(dimension, svg.getroot().attrib[dimension] + "pt")
                ET.register_namespace("", "http://www.w3.org/2000/svg")
                ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
                svg.write(vector, encoding="utf-8", xml_declaration=True)
                shutil.copy2(vector, figure.with_name(figure.stem + "-.svg"))
            else:
                subprocess.run(["dvisvgm", "--eps", "--no-fonts", "--exact",
                                f"--output={figure.with_suffix('.svg')}", str(figure)],
                               stdout=output, stderr=subprocess.STDOUT, env=environment, check=True)
        subprocess.run(["tex4ebook", "-f", "epub3+dvisvgm_hashes", "-s", "-c", "ebook.cfg",
                        "-e", "ebook.mk4", source.name], cwd=stage, stdout=output,
                       stderr=subprocess.STDOUT, env=environment, check=True)
    transcript = (stage / source.with_suffix(".log").name).read_text()
    if re.search(r"^!|LaTeX Warning: (?:Citation|Reference).*undefined|There were undefined references",
                 transcript, re.MULTILINE):
        raise RuntimeError("LaTeX reported errors or unresolved references in the final EPUB pass.")
    if re.search(r"XML DOM parsing.*failed:", log.read_text()):
        # LuaXML's HTML recovery can silently alter quoted strings in code.
        # Require valid converter XML rather than publish repaired content.
        raise RuntimeError("TeX4ht required HTML repair; refusing to publish potentially altered content.")
    epub = stage / source.with_suffix(".epub").name
    polish_publication(epub)
    errors = validate(epub)
    if errors:
        raise RuntimeError("EPUB content validation failed:\n" + "\n".join(errors))
    subprocess.run(["epubcheck", "--failonwarnings", str(epub)], check=True)
    # Publish only after every gate passes; a failed rebuild retains the last
    # valid book and the complete staging diagnostics.
    destination = source.with_suffix(".epub")
    temporary = destination.with_suffix(".epub.tmp")
    shutil.copy2(epub, temporary)
    temporary.replace(destination)
    print(f"Exported {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    try:
        build(args.source)
    except (OSError, RuntimeError, subprocess.CalledProcessError, ET.ParseError, zipfile.BadZipFile) as error:
        print(f"EPUB export failed: {error}\nSee .build/epub/export.log for diagnostics.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
