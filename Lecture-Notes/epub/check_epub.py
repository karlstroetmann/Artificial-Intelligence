#!/usr/bin/env python3
"""Check the offline EPUB 3 contract used by the lecture-notes exporter.

This deliberately small structural check complements EPUBCheck; it does not
replace standards validation or testing in an actual reading application.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import posixpath
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile


CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
XML_NS = "http://www.w3.org/XML/1998/namespace"
XML_MEDIA_TYPES = {"application/xhtml+xml", "image/svg+xml"}
CSS_REFERENCES = re.compile(
    r'''url\(\s*(?:"([^"]*)"|'([^']*)'|([^\s)]*))\s*\)|@import\s+(?:"([^"]*)"|'([^']*)')''',
    re.IGNORECASE,
)


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _resolve(base: str, reference: str) -> tuple[str, str]:
    """Resolve a publication-relative URL without allowing archive traversal."""
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc:
        raise ValueError(f"external resource reference {reference!r}")
    path = unquote(parsed.path)
    if path.startswith("/") or "\\" in path:
        raise ValueError(f"invalid archive path {reference!r}")
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(base), path)) if path else base
    if resolved in {".", ".."} or resolved.startswith("../"):
        raise ValueError(f"resource escapes the archive: {reference!r}")
    return resolved, unquote(parsed.fragment)


def validate(path: str | Path) -> list[str]:
    """Return all structural errors found in an EPUB; an empty list means success."""
    errors: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            _validate_archive(archive, errors)
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        errors.append(f"Cannot read EPUB: {error}")
    return errors


def _validate_archive(archive: zipfile.ZipFile, errors: list[str]) -> None:
    entries = archive.infolist()
    names = {entry.filename for entry in entries if not entry.is_dir()}
    if len(names) != sum(not entry.is_dir() for entry in entries):
        errors.append("Archive contains duplicate file entries")
    if not entries or entries[0].filename != "mimetype":
        errors.append("mimetype must be the first ZIP entry")
    if "mimetype" not in names:
        errors.append("Archive is missing mimetype")
    else:
        if archive.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            errors.append("mimetype must be stored without compression")
        if archive.read("mimetype") != b"application/epub+zip":
            errors.append("mimetype must contain exactly application/epub+zip")

    documents: dict[str, ET.Element | None] = {}

    def read_xml(filename: str) -> ET.Element | None:
        if filename not in documents:
            if filename not in names:
                errors.append(f"Missing resource: {filename}")
                documents[filename] = None
            else:
                try:
                    documents[filename] = ET.fromstring(archive.read(filename))
                except ET.ParseError as error:
                    errors.append(f"Invalid XML in {filename}: {error}")
                    documents[filename] = None
        return documents[filename]

    container = read_xml("META-INF/container.xml")
    if container is None:
        return
    rootfile = container.find(f"{{{CONTAINER_NS}}}rootfiles/{{{CONTAINER_NS}}}rootfile")
    if rootfile is None or not rootfile.get("full-path"):
        errors.append("container.xml must identify a package document")
        return
    try:
        package_path, _ = _resolve("container.xml", rootfile.get("full-path", ""))
    except ValueError as error:
        errors.append(f"container.xml: {error}")
        return
    package = read_xml(package_path)
    if package is None:
        return
    if package.tag != f"{{{OPF_NS}}}package" or package.get("version") != "3.0":
        errors.append(f"{package_path}: package must use OPF namespace and EPUB version 3.0")

    metadata = package.find(f"{{{OPF_NS}}}metadata")
    for field in ("title", "creator", "language", "identifier"):
        values = metadata.findall(f"{{{DC_NS}}}{field}") if metadata is not None else []
        if not any("".join(value.itertext()).strip() for value in values):
            errors.append(f"{package_path}: missing non-empty dc:{field} metadata")
    unique_id = package.get("unique-identifier")
    identifiers = metadata.findall(f"{{{DC_NS}}}identifier") if metadata is not None else []
    if not unique_id or not any(value.get("id") == unique_id and "".join(value.itertext()).strip()
                               for value in identifiers):
        errors.append(f"{package_path}: unique-identifier must identify dc:identifier metadata")

    manifest: dict[str, tuple[str, str, set[str]]] = {}
    declared: set[str] = set()
    for item in package.findall(f"{{{OPF_NS}}}manifest/{{{OPF_NS}}}item"):
        item_id, href = item.get("id", ""), item.get("href", "")
        if not item_id or not href:
            errors.append(f"{package_path}: manifest item requires id and href")
            continue
        if item_id in manifest:
            errors.append(f"{package_path}: duplicate manifest id {item_id!r}")
        try:
            filename, fragment = _resolve(package_path, href)
        except ValueError as error:
            errors.append(f"{package_path}: {error}")
            continue
        if fragment:
            errors.append(f"{package_path}: manifest href must not contain a fragment: {href}")
        media_type = item.get("media-type", "")
        if not media_type:
            errors.append(f"{package_path}: manifest item {item_id!r} lacks media-type")
        manifest[item_id] = (filename, media_type, set(item.get("properties", "").split()))
        declared.add(filename)
        if filename not in names:
            errors.append(f"{package_path}: manifest resource is missing: {filename}")
        elif media_type in XML_MEDIA_TYPES:
            read_xml(filename)

    spine = package.findall(f"{{{OPF_NS}}}spine/{{{OPF_NS}}}itemref")
    if not spine:
        errors.append(f"{package_path}: reading-order spine must not be empty")
    for item in spine:
        item_id = item.get("idref", "")
        if item_id not in manifest:
            errors.append(f"{package_path}: spine references unknown manifest id {item_id!r}")

    covers = [filename for filename, media_type, props in manifest.values() if "cover-image" in props]
    if len(covers) != 1:
        errors.append(f"{package_path}: manifest must contain exactly one cover-image")
    for filename, media_type, props in manifest.values():
        if "cover-image" in props and not media_type.startswith("image/"):
            errors.append(f"{package_path}: cover-image must have an image media type: {filename}")

    navigation = [filename for filename, media_type, props in manifest.values() if "nav" in props]
    if len(navigation) != 1:
        errors.append(f"{package_path}: manifest must contain exactly one navigation document")
    for filename in navigation:
        document = read_xml(filename)
        if document is not None:
            toc = [element for element in document.iter(f"{{{XHTML_NS}}}nav")
                   if "toc" in element.get(f"{{{EPUB_NS}}}type", "").split()]
            if not any(link.get("href") and "".join(link.itertext()).strip()
                       for element in toc for link in element.iter(f"{{{XHTML_NS}}}a")):
                errors.append(f"{filename}: navigation must contain a non-empty epub:type='toc'")

    def check_reference(filename: str, reference: str, attribute: str) -> None:
        # Dvisvgm embeds raster parts of PDF diagrams as offline image data.
        if re.match(r"data:image/(?:png|jpeg|gif)(?:;[^,]*)?,", reference, re.IGNORECASE):
            return
        try:
            target, fragment = _resolve(filename, reference)
        except ValueError as error:
            errors.append(f"{filename}: {error}")
            return
        if target not in names:
            errors.append(f"{filename}: broken {attribute} reference {reference!r} (missing {target})")
            return
        if target not in declared:
            errors.append(f"{filename}: linked resource is not declared in manifest: {target}")
        if fragment:
            target_document = read_xml(target)
            if target_document is not None and not any(
                node.get("id") == fragment or node.get(f"{{{XML_NS}}}id") == fragment
                for node in target_document.iter()
            ):
                errors.append(f"{filename}: broken fragment reference {reference!r}")

    def check_css(filename: str, content: str) -> None:
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        for match in CSS_REFERENCES.finditer(content):
            reference = next(value for value in match.groups() if value is not None)
            check_reference(filename, reference, "CSS url")

    for filename, media_type, _ in manifest.values():
        if media_type == "text/css" and filename in names:
            try:
                check_css(filename, archive.read(filename).decode("utf-8"))
            except UnicodeDecodeError as error:
                errors.append(f"{filename}: CSS must use UTF-8: {error}")
        if media_type not in XML_MEDIA_TYPES:
            continue
        document = read_xml(filename)
        if document is None:
            continue
        if media_type == "application/xhtml+xml" and document.tag != f"{{{XHTML_NS}}}html":
            errors.append(f"{filename}: XHTML document must use the XHTML namespace")
        for element in document.iter():
            tag = _local_name(element.tag)
            if tag == "script":
                errors.append(f"{filename}: scripts are not permitted in the offline export")
            if tag == "img" and not element.get("alt", "").strip():
                errors.append(f"{filename}: image must have non-empty alt text: {element.get('src', '')}")
            if tag == "style":
                check_css(filename, "".join(element.itertext()))
            for attribute, reference in element.attrib.items():
                attribute = _local_name(attribute)
                if attribute.lower().startswith("on"):
                    errors.append(f"{filename}: script event handler {attribute!r} is not permitted")
                if attribute == "style":
                    check_css(filename, reference)
                if attribute not in {"href", "src"}:
                    continue
                try:
                    parsed = urlsplit(reference)
                except ValueError as error:
                    errors.append(f"{filename}: invalid URL {reference!r}: {error}")
                    continue
                if tag == "a" and attribute == "href" and (
                    parsed.scheme in {"http", "https", "mailto", "tel"}
                    or (not parsed.scheme and parsed.netloc)
                ):
                    continue
                check_reference(filename, reference, attribute)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("epub", type=Path, help="EPUB file to validate")
    args = parser.parse_args(argv)
    errors = validate(args.epub)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"EPUB structural checks passed: {args.epub}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
