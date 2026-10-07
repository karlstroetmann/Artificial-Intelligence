"""EPUB contents, reading adaptations and the lecture notes' offline policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import posixpath
import re
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile

XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
OPF_NS = "http://www.idpf.org/2007/opf"
NS = {"opf": OPF_NS, "dc": "http://purl.org/dc/elements/1.1/"}
MATH_EM_PT = 11 * 1.4  # Source font size times ebook.mk4's dvisvgm scale.
CSS_URLS = re.compile(
    r'''url\(\s*(?:"([^"]*)"|'([^']*)'|([^\s)]*))\s*\)|@import\s+(?:"([^"]*)"|'([^']*)')''', re.I)


def xhtml(tag: str) -> str:
    return f"{{{XHTML_NS}}}{tag}"


def classes(element: ET.Element) -> set[str]:
    return set(element.get("class", "").split())


def plain_text(element: ET.Element) -> str:
    """Include formula alternatives in descriptions derived from captions."""
    def text(node: ET.Element) -> str:
        content = node.get("alt", "") if node.tag == xhtml("img") else node.text or ""
        return content + "".join(text(child) + (child.tail or "") for child in node)
    return " ".join(text(element).split())


def wrap_child(parent: ET.Element, child: ET.Element, tag: str, class_name: str) -> None:
    wrapper = ET.Element(xhtml(tag), {"class": class_name})
    wrapper.tail, child.tail = child.tail, None
    position = list(parent).index(child)
    parent.remove(child)
    parent.insert(position, wrapper)
    wrapper.append(child)


@dataclass
class Publication:
    files: dict[str, bytes]
    package_path: str
    package: ET.Element
    documents: dict[str, ET.Element]

    @classmethod
    def read(cls, path: Path) -> Publication:
        with zipfile.ZipFile(path) as archive:
            # EPUBCheck permits compression here; the publication contract does not.
            if archive.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
                raise RuntimeError("mimetype must be stored without compression")
            files = {entry.filename: archive.read(entry) for entry in archive.infolist() if not entry.is_dir()}
        container = ET.fromstring(files["META-INF/container.xml"])
        rootfile = container.find(".//{*}rootfile")
        if rootfile is None:
            raise RuntimeError("container.xml does not identify a package document")
        package_path = rootfile.attrib["full-path"]
        book = cls(files, package_path, ET.fromstring(files[package_path]), {})
        for item in book.items:
            if item.get("media-type") in {"application/xhtml+xml", "image/svg+xml"}:
                filename = book.resource_path(item.attrib["href"])
                book.documents[filename] = ET.fromstring(files[filename])
        return book

    @property
    def items(self) -> list[ET.Element]:
        return self.package.findall("opf:manifest/opf:item", NS)

    def property_item(self, property_name: str) -> ET.Element:
        items = [item for item in self.items if property_name in item.get("properties", "").split()]
        if len(items) != 1:
            raise RuntimeError(f"Publication must contain exactly one {property_name} item")
        return items[0]

    def resource_path(self, href: str, document: str | None = None) -> str:
        base = document or self.package_path
        path = unquote(urlsplit(href).path)
        return posixpath.normpath(posixpath.join(posixpath.dirname(base), path)) if path else base

    def metadata(self, name: str) -> str:
        return " ".join("".join(node.itertext()).strip()
                        for node in self.package.findall(f"opf:metadata/dc:{name}", NS)).strip()

    def adapt_for_reading(self) -> None:
        for item in self.items:
            if item.get("media-type") == "application/xhtml+xml":
                filename = self.resource_path(item.attrib["href"])
                document = self.documents[filename]
                describe_figures(document)
                adapt_inline_markup(document)
                adapt_listings(document)
                repair_figure_navigation(document)
                adapt_layout(self, filename, document)
        add_footnote_backlinks(self)
        add_front_matter(self)

    def check_reading_policy(self) -> None:
        """EPUBCheck owns standards; these are additional book requirements."""
        cover = self.property_item("cover-image")
        if not cover.get("media-type", "").startswith("image/"):
            raise RuntimeError("Cover must have an image media type")
        if not self.metadata("creator"):
            raise RuntimeError("Publication requires non-empty dc:creator attribution")
        for filename, document in self.documents.items():
            for element in document.iter():
                tag = element.tag.rsplit("}", 1)[-1]
                attributes = {name.rsplit("}", 1)[-1]: value for name, value in element.attrib.items()}
                if tag == "script" or any(name.lower().startswith("on") for name in attributes):
                    raise RuntimeError(f"{filename}: scripting is not permitted")
                if tag == "img" and not element.get("alt", "").strip():
                    raise RuntimeError(f"{filename}: image requires non-empty alt text")
                for name, reference in attributes.items():
                    if name == "style":
                        check_offline_css(filename, reference)
                    if name not in {"href", "src"}:
                        continue
                    url = urlsplit(reference)
                    if tag == "a" and name == "href" and (url.scheme in {"http", "https", "mailto", "tel"}
                                                           or (not url.scheme and url.netloc)):
                        continue
                    check_offline_resource(filename, reference)
                if tag == "style":
                    check_offline_css(filename, "".join(element.itertext()))
        for item in self.items:
            reference = item.attrib["href"]
            url = urlsplit(reference)
            if url.scheme or url.netloc:
                raise RuntimeError(f"{self.package_path}: external manifest resource {reference!r}")
            if item.get("media-type") == "text/css":
                filename = self.resource_path(reference)
                check_offline_css(filename, self.files[filename].decode("utf-8"))

    def write(self, path: Path) -> None:
        ET.register_namespace("", XHTML_NS)
        ET.register_namespace("epub", EPUB_NS)
        for item in self.items:
            if item.get("media-type") == "application/xhtml+xml":
                filename = self.resource_path(item.attrib["href"])
                self.files[filename] = ET.tostring(self.documents[filename], encoding="utf-8", xml_declaration=True)
        ET.register_namespace("", OPF_NS)
        ET.register_namespace("dc", NS["dc"])
        self.files[self.package_path] = ET.tostring(self.package, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("mimetype", self.files["mimetype"], compress_type=zipfile.ZIP_STORED)
            for filename, content in self.files.items():
                if filename != "mimetype":
                    archive.writestr(filename, content)


def check_offline_resource(filename: str, reference: str) -> None:
    if re.match(r"data:image/(?:png|jpeg|gif)(?:;[^,]*)?,", reference, re.I):
        return  # Dvisvgm embeds raster portions of diagrams in SVG.
    url = urlsplit(reference)
    if url.scheme or url.netloc:
        raise RuntimeError(f"{filename}: external resource reference {reference!r}")


def check_offline_css(filename: str, content: str) -> None:
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    for match in CSS_URLS.finditer(content):
        check_offline_resource(filename, next(value for value in match.groups() if value is not None))


def describe_figures(document: ET.Element) -> None:
    parents = {child: parent for parent in document.iter() for child in parent}
    for image in document.iter(xhtml("img")):
        if image.get("alt", "").strip() not in {"", "PIC", "[Picture]"}:
            continue
        if posixpath.basename(urlsplit(image.get("src", "")).path) == "dhbw-logo.svg":
            image.set("alt", "DHBW logo")
            continue
        ancestor = parents.get(image)
        while ancestor is not None:
            if ancestor.tag == xhtml("figure") or {"figure", "subfigure"} & classes(ancestor):
                caption = next((child for child in ancestor if child.tag == xhtml("figcaption")
                                or "caption" in classes(child)), None)
                if caption is not None and plain_text(caption):
                    image.set("alt", plain_text(caption))
                    break
            ancestor = parents.get(ancestor)


def adapt_inline_markup(document: ET.Element) -> None:
    for element in document.iter():
        href = element.get("href")
        if href and urlsplit(href).scheme:
            element.set("href", quote(href, safe="%:/?#[]@!$&'()*+,;="))
        style = element.get("style", "")
        if re.search(r"(?:^|;)\s*color\s*:", style):
            element.set("class", (element.get("class", "") + " epub-emphasis").strip())
        if style:
            # Reader themes replace print colors; authored bold/italic survives.
            style = re.sub(r"(?:^|;)\s*(?:color|background(?:-color)?)\s*:[^;]*", "", style).strip("; ")
            if style:
                element.set("style", style)
            else:
                element.attrib.pop("style")


def adapt_listings(document: ET.Element) -> None:
    for listing in document.iter(xhtml("pre")):
        for element in listing.iter():
            if element.text:
                element.text = element.text.replace("\u00a0", " ")
            if element.tail:
                element.tail = element.tail.replace("\u00a0", " ")


def repair_figure_navigation(document: ET.Element) -> None:
    for listing in document.findall(f".//{xhtml('nav')}/{xhtml('ol')}"):
        for entry in list(listing):
            if "lofToc" in classes(entry):
                entry.tag = xhtml("li")
            elif entry.tag == xhtml("br"):
                listing.remove(entry)


def adapt_layout(book: Publication, filename: str, document: ET.Element) -> None:
    for image in document.iter(xhtml("img")):
        if not {"math", "math-display"} & classes(image):
            continue
        svg = book.documents[book.resource_path(image.attrib["src"], filename)]
        width = re.fullmatch(r"([\d.]+)pt", svg.get("width", ""))
        height = re.fullmatch(r"([\d.]+)pt", svg.get("height", ""))
        if width and height:
            image.set("style", f"width:{float(width[1]) / MATH_EM_PT:.4f}em;"
                      f"height:{float(height[1]) / MATH_EM_PT:.4f}em")
    for parent in list(document.iter()):
        for child in list(parent):
            if child.tag == xhtml("table"):
                wrap_child(parent, child, "div", "epub-table")
            elif child.tag == xhtml("img") and {"math", "math-display"} & classes(child):
                # Inline math already has its TeX-derived baseline wrapper.
                if "epub-math" not in classes(parent):
                    wrap_child(parent, child, "span", "epub-math")


def add_footnote_backlinks(book: Publication) -> None:
    documents = {name: document for name, document in book.documents.items() if document.tag == xhtml("html")}
    targets = {(filename, element.get("id")): element for filename, document in documents.items()
               for element in document.iter() if element.get("id")}
    for filename, document in documents.items():
        used_ids = {element.get("id") for element in document.iter()}
        for number, reference in enumerate(document.iter(xhtml("a")), start=1):
            if "noteref" not in reference.get(f"{{{EPUB_NS}}}type", "").split():
                continue
            href = urlsplit(reference.get("href", ""))
            if href.scheme or href.netloc:
                continue
            target_file = book.resource_path(reference.get("href", ""), filename)
            note = targets.get((target_file, unquote(href.fragment)))
            if note is None:
                continue  # EPUBCheck reports missing targets.
            reference_id = reference.get("id") or f"epub-noteref-{number}"
            while not reference.get("id") and reference_id in used_ids:
                reference_id += "-ref"
            reference.set("id", reference_id)
            used_ids.add(reference_id)
            return_path = "" if target_file == filename else posixpath.relpath(filename, posixpath.dirname(target_file))
            paragraph = ET.SubElement(note, xhtml("p"), {"class": "epub-note-return"})
            ET.SubElement(paragraph, xhtml("a"), {
                "href": quote(return_path + "#" + reference_id, safe="/#:"),
                "role": "doc-backlink", "aria-label": "Return to the footnote reference",
            }).text = "Return to text"


def add_front_matter(book: Publication) -> None:
    cover_item = book.property_item("cover-image")
    cover = ET.fromstring(f'''<html xmlns="{XHTML_NS}" lang="en"><head><title>Cover</title>
<link rel="stylesheet" href="reader.css" type="text/css"/></head>
<body class="epub-cover"><section xmlns:epub="{EPUB_NS}" epub:type="cover"><img/></section></body></html>''')
    image = cover.find(f".//{xhtml('img')}")
    assert image is not None
    image.set("src", cover_item.attrib["href"])
    image.set("role", "doc-cover")
    image.set("alt", f"Cover: {book.metadata('title')}, by {book.metadata('creator')}")
    book.documents[book.resource_path("cover.xhtml")] = cover
    manifest, spine = book.package.find("opf:manifest", NS), book.package.find("opf:spine", NS)
    if manifest is None or spine is None:
        raise RuntimeError("Publication requires a manifest and reading-order spine")
    ET.SubElement(manifest, f"{{{OPF_NS}}}item", {"id": "ebook-cover", "href": "cover.xhtml",
                                               "media-type": "application/xhtml+xml"})
    spine.insert(0, ET.Element(f"{{{OPF_NS}}}itemref", {"idref": "ebook-cover"}))
    nav_item = book.property_item("nav")
    if not any(item.get("idref") == nav_item.attrib["id"] for item in spine):
        spine.insert(1, ET.Element(f"{{{OPF_NS}}}itemref", {"idref": nav_item.attrib["id"]}))
    navigation = book.documents[book.resource_path(nav_item.attrib["href"])]
    body = navigation.find(xhtml("body"))
    if body is None:
        raise RuntimeError("Navigation document requires a body")
    landmarks = ET.SubElement(body, xhtml("nav"), {f"{{{EPUB_NS}}}type": "landmarks", "hidden": "hidden"})
    ET.SubElement(landmarks, xhtml("h2")).text = "Book landmarks"
    entries = ET.SubElement(landmarks, xhtml("ol"))
    for kind, href, label in [("cover", "cover.xhtml", "Cover"), ("toc", nav_item.attrib["href"], "Contents")]:
        entry = ET.SubElement(entries, xhtml("li"))
        ET.SubElement(entry, xhtml("a"), {f"{{{EPUB_NS}}}type": kind, "href": href}).text = label
