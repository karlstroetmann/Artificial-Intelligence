"""Check reading adaptations and publication failure behavior."""

import base64
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from check_epub import EPUB_NS, OPF_NS, XHTML_NS, validate
from export_epub import add_footnote_backlinks, build, describe_figures, embedded_png_svg, plain_text, polish_publication, xhtml
from test_check_epub import CONTAINER, PACKAGE, NAV


class ExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.epub = self.root / "book.epub"

    def publication(self) -> None:
        package = PACKAGE.replace("</manifest>",
                                  '<item id="math" href="math.svg" media-type="image/svg+xml"/>'
                                  '<item id="reader" href="reader.css" media-type="text/css"/></manifest>')
        chapter = f'''<html xmlns="{XHTML_NS}"><head><title>Chapter</title></head><body>
<h1 id="section:one">Chapter</h1>
<p><span style="color:blue;font-style:italic">Key concept</span>
<a href="https://example.com/a book">External reading</a></p>
<p>Inline <img class="math" src="../math.svg" alt="x squared"/> stays inline.</p>
<p>A fraction <span class="epub-math" style="vertical-align:-0.35em"><img
class="math" src="../math.svg" alt="a over b"/></span> with its original baseline.</p>
<figure><img src="../images/cover.png" alt="PIC"/><figcaption>A network with
<img class="math" src="../math.svg" alt="x squared"/> nodes.</figcaption></figure>
<table><tr><td>Readable data</td></tr></table>
<pre>\u00a0\u00a0\u00a0\u00a0return\u00a0'quoted text'</pre>
<nav><ol><span class="lofToc"><a href="#section:one">Figure one</a></span><br/></ol></nav>
</body></html>'''
        with zipfile.ZipFile(self.epub, "w") as archive:
            archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            for name, content in {
                "META-INF/container.xml": CONTAINER,
                "EPUB/package.opf": package,
                "EPUB/nav.xhtml": NAV,
                "EPUB/chapters/chapter one.xhtml": chapter,
                "EPUB/images/cover.png": b"cover",
                "EPUB/styles/book.css": "body { line-height: 1.5; }",
                "EPUB/reader.css": "body { line-height: 1.5; }",
                "EPUB/math.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="30.8pt" height="15.4pt"/>',
            }.items():
                archive.writestr(name, content)

    def test_polished_book_preserves_content_links_and_scales_math(self) -> None:
        self.publication()
        polish_publication(self.epub)
        self.assertEqual(validate(self.epub), [])
        with zipfile.ZipFile(self.epub) as archive:
            chapter = ET.fromstring(archive.read("EPUB/chapters/chapter one.xhtml"))
            package = ET.fromstring(archive.read("EPUB/package.opf"))
            nav = ET.fromstring(archive.read("EPUB/nav.xhtml"))
            self.assertEqual(archive.infolist()[0].filename, "mimetype")
            self.assertEqual(archive.infolist()[0].compress_type, zipfile.ZIP_STORED)
        self.assertIn("Readable data", plain_text(chapter))
        self.assertIn("Key concept", plain_text(chapter))
        self.assertEqual(chapter.find(f".//{xhtml('pre')}").text, "    return 'quoted text'")
        self.assertEqual(chapter.find(f".//{xhtml('span')}").get("style"), "font-style:italic")
        self.assertEqual(chapter.find(f".//{xhtml('p')}/{xhtml('a')}").get("href"), "https://example.com/a%20book")
        math = chapter.find(f".//{xhtml('img')}[@class='math']")
        self.assertIn("width:2.0000em", math.get("style"))
        self.assertIn("height:1.0000em", math.get("style"))
        baseline = chapter.find(f".//{xhtml('span')}[@style='vertical-align:-0.35em']")
        self.assertEqual(len(baseline), 1)
        self.assertEqual(baseline[0].tag, xhtml("img"))
        self.assertEqual(chapter.find(f".//{xhtml('figure')}/{xhtml('img')}").get("alt"),
                         "A network with x squared nodes.")
        self.assertIsNotNone(chapter.find(f".//{xhtml('div')}[@class='epub-table']/{xhtml('table')}"))
        self.assertIsNotNone(chapter.find(f".//{xhtml('nav')}/{xhtml('ol')}/{xhtml('li')}/{xhtml('a')}"))
        self.assertEqual(package.find(f"{{{OPF_NS}}}spine")[0].get("idref"), "ebook-cover")
        self.assertEqual(package.find(f"{{{OPF_NS}}}spine")[1].get("idref"), "nav")
        self.assertIsNotNone(nav.find(f".//{xhtml('nav')}[@{{{EPUB_NS}}}type='landmarks']"))

    def test_mislabeled_png_preserves_pixels_and_dimensions(self) -> None:
        png = b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + struct.pack(">II", 1004, 1858) + b"original raster data"
        svg = ET.fromstring(embedded_png_svg(png))
        self.assertEqual(svg.get("viewBox"), "0 0 1004 1858")
        image = svg.find("{http://www.w3.org/2000/svg}image")
        data = image.get("{http://www.w3.org/1999/xlink}href").split(",", 1)[1]
        self.assertEqual(base64.b64decode(data), png)

    def test_footnotes_return_to_unique_references_across_documents(self) -> None:
        chapter = ET.fromstring(f'''<html xmlns="{XHTML_NS}" xmlns:epub="{EPUB_NS}">
<body><p id="epub-noteref-1">Text<a epub:type="noteref" href="notes.xhtml#note">1</a>
<a epub:type="noteref" href="notes.xhtml#note" id="existing">1</a></p></body></html>''')
        notes = ET.fromstring(f'''<html xmlns="{XHTML_NS}" xmlns:epub="{EPUB_NS}">
<body><aside id="note" epub:type="footnote">Note text</aside></body></html>''')
        add_footnote_backlinks({"EPUB/chapter.xhtml": chapter, "EPUB/notes.xhtml": notes})
        references = list(chapter.iter(xhtml("a")))
        self.assertEqual(references[0].get("id"), "epub-noteref-1-ref")
        self.assertEqual(references[1].get("id"), "existing")
        backlinks = list(notes.iter(xhtml("a")))
        self.assertEqual([link.get("href") for link in backlinks],
                         ["chapter.xhtml#epub-noteref-1-ref", "chapter.xhtml#existing"])
        self.assertTrue(all(link.get("role") == "doc-backlink" for link in backlinks))

    def test_diagrams_use_their_own_subfigure_captions(self) -> None:
        document = ET.fromstring(f'''<html xmlns="{XHTML_NS}"><body>
<img src="Figures/dhbw-logo.svg" alt="PIC"/>
<figure><div class="subfigure"><p><img alt="[Picture]"/></p>
<div class="caption">Conventional search</div></div>
<div class="subfigure"><p><img alt="[Picture]"/></p>
<div class="caption">Bidirectional search</div></div>
<p><img alt="PIC"/></p><figcaption>Comparison of search strategies</figcaption>
</figure></body></html>''')
        describe_figures(document)
        self.assertEqual([image.get("alt") for image in document.iter(xhtml("img"))],
                         ["DHBW logo", "Conventional search", "Bidirectional search", "Comparison of search strategies"])

    def test_failed_conversion_retains_previous_export_and_diagnostics(self) -> None:
        source = self.root / "book.tex"
        source.write_text("Original source")
        (self.root / "Figures").mkdir()
        self.epub.write_bytes(b"previous validated publication")
        failure = subprocess.CalledProcessError(1, "tex4ebook")
        with patch("export_epub.shutil.which", return_value="/usr/bin/true"), \
             patch("export_epub.subprocess.run", side_effect=failure):
            with self.assertRaises(subprocess.CalledProcessError):
                build(source)
        self.assertEqual(self.epub.read_bytes(), b"previous validated publication")
        self.assertTrue((self.root / ".build/epub/export.log").exists())
        self.assertEqual(source.read_text(), "Original source")

    def test_missing_tools_fail_before_touching_stage(self) -> None:
        stage = self.root / ".build/epub"
        stage.mkdir(parents=True)
        sentinel = stage / "diagnostic.txt"
        sentinel.write_text("previous build")
        with patch("export_epub.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Missing EPUB tools"):
                build(self.root / "book.tex")
        self.assertEqual(sentinel.read_text(), "previous build")

    def test_html_repair_cannot_replace_previous_publication(self) -> None:
        source = self.root / "book.tex"
        source.write_text("Original source")
        (self.root / "Figures").mkdir()
        self.epub.write_bytes(b"previous validated publication")

        def repaired_conversion(command, **kwargs):
            stage = kwargs["cwd"]
            (stage / "book.log").write_text("Compilation succeeded")
            kwargs["stdout"].write("domfilter: XML DOM parsing of chapter.xhtml failed:\n")
            return subprocess.CompletedProcess(command, 0)

        with patch("export_epub.shutil.which", return_value="/usr/bin/true"), \
             patch("export_epub.subprocess.run", side_effect=repaired_conversion):
            with self.assertRaisesRegex(RuntimeError, "refusing to publish"):
                build(source)
        self.assertEqual(self.epub.read_bytes(), b"previous validated publication")


if __name__ == "__main__":
    unittest.main()
