"""Small publication fixtures for the exporter contract, without external tools."""

from pathlib import Path
import tempfile
import unittest
import zipfile

from check_epub import validate


CONTAINER = '''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
<rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>'''

PACKAGE = '''<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="book-id">urn:test:book</dc:identifier><dc:title>Lecture Notes</dc:title>
<dc:creator>Test Author</dc:creator><dc:language>en</dc:language>
</metadata><manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="chapter" href="chapters/chapter%20one.xhtml" media-type="application/xhtml+xml"/>
<item id="cover" href="images/cover.png" media-type="image/png" properties="cover-image"/>
<item id="css" href="styles/book.css" media-type="text/css"/>
</manifest><spine><itemref idref="chapter"/></spine></package>'''

NAV = '''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Contents</title></head><body><nav epub:type="toc"><ol>
<li><a href="chapters/chapter%20one.xhtml#section%3Aone">First chapter</a></li>
</ol></nav></body></html>'''

CHAPTER = '''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Chapter One</title></head><body>
<h1 id="section:one">Chapter One</h1><p>Readable text with a <a href="#section%3Aone">local link</a>
and an <a href="https://example.com/">external source</a>.</p>
<img src="../images/cover.png" alt="Lecture notes cover"/></body></html>'''


class EPUBValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "book.epub"

    def publication(self, *, replacements: dict[str, str | bytes | None] | None = None,
                    mime_first: bool = True, mime_compression: int = zipfile.ZIP_STORED,
                    mimetype: bytes = b"application/epub+zip") -> list[str]:
        resources: dict[str, str | bytes] = {
            "META-INF/container.xml": CONTAINER,
            "EPUB/package.opf": PACKAGE,
            "EPUB/nav.xhtml": NAV,
            "EPUB/chapters/chapter one.xhtml": CHAPTER,
            "EPUB/images/cover.png": b"example image bytes",
            "EPUB/styles/book.css": 'body { background-image: url("../images/cover.png"); }',
        }
        for name, value in (replacements or {}).items():
            if value is None:
                resources.pop(name, None)
            else:
                resources[name] = value
        with zipfile.ZipFile(self.path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            if mime_first:
                archive.writestr("mimetype", mimetype, compress_type=mime_compression)
            for name, value in resources.items():
                archive.writestr(name, value)
            if not mime_first:
                archive.writestr("mimetype", mimetype, compress_type=mime_compression)
        return validate(self.path)

    def assert_error(self, errors: list[str], expected: str) -> None:
        self.assertTrue(any(expected in error for error in errors), errors)

    def test_complete_epub_with_encoded_paths_fragments_and_external_link(self) -> None:
        self.assertEqual(self.publication(), [])

    def test_mimetype_must_be_first_stored_and_exact(self) -> None:
        self.assert_error(self.publication(mime_first=False), "first ZIP entry")
        self.assert_error(self.publication(mime_compression=zipfile.ZIP_DEFLATED), "without compression")
        self.assert_error(self.publication(mimetype=b"application/epub+zip\n"), "exactly")

    def test_missing_manifest_resource(self) -> None:
        self.assert_error(self.publication(replacements={"EPUB/images/cover.png": None}), "manifest resource is missing")

    def test_broken_local_file_and_fragment_links(self) -> None:
        for href, expected in (("missing.xhtml", "broken href reference"),
                               ("#unknown", "broken fragment reference")):
            with self.subTest(href=href):
                chapter = CHAPTER.replace('href="#section%3Aone"', f'href="{href}"')
                self.assert_error(self.publication(replacements={"EPUB/chapters/chapter one.xhtml": chapter}), expected)

    def test_missing_and_remote_images_fail(self) -> None:
        for source, expected in (("missing.png", "broken src reference"),
                                 ("https://example.com/image.png", "external resource reference")):
            with self.subTest(source=source):
                chapter = CHAPTER.replace("../images/cover.png", source)
                self.assert_error(self.publication(replacements={"EPUB/chapters/chapter one.xhtml": chapter}), expected)

    def test_authority_does_not_allow_script_or_local_filesystem_links(self) -> None:
        for href in ("javascript://example.com/%0Aalert(1)", "file://localhost/etc/passwd"):
            with self.subTest(href=href):
                chapter = CHAPTER.replace("https://example.com/", href)
                self.assert_error(self.publication(replacements={"EPUB/chapters/chapter one.xhtml": chapter}),
                                  "external resource reference")

    def test_embedded_raster_image_data_is_offline(self) -> None:
        chapter = CHAPTER.replace("../images/cover.png", "data:image/png;base64,iVBORw0KGgo=")
        self.assertEqual(self.publication(replacements={"EPUB/chapters/chapter one.xhtml": chapter}), [])

    def test_image_requires_nonempty_alt_text(self) -> None:
        for alternative in ('', 'alt=""', 'alt="  "'):
            with self.subTest(alternative=alternative):
                chapter = CHAPTER.replace('alt="Lecture notes cover"', alternative)
                self.assert_error(self.publication(replacements={"EPUB/chapters/chapter one.xhtml": chapter}), "non-empty alt text")

    def test_cover_and_navigation_metadata_required(self) -> None:
        self.assert_error(self.publication(replacements={"EPUB/package.opf": PACKAGE.replace(' properties="cover-image"', '')}), "one cover-image")
        self.assert_error(self.publication(replacements={"EPUB/package.opf": PACKAGE.replace(' properties="nav"', '')}), "one navigation document")
        self.assert_error(self.publication(replacements={"EPUB/nav.xhtml": NAV.replace('epub:type="toc"', 'epub:type="landmarks"')}), "non-empty epub:type='toc'")

    def test_empty_spine_and_unknown_spine_item_fail(self) -> None:
        self.assert_error(self.publication(replacements={"EPUB/package.opf": PACKAGE.replace('<itemref idref="chapter"/>', '')}), "spine must not be empty")
        self.assert_error(self.publication(replacements={"EPUB/package.opf": PACKAGE.replace('idref="chapter"', 'idref="missing"')}), "unknown manifest id")

    def test_metadata_required_and_identifier_must_resolve(self) -> None:
        for field, value in (("title", "Lecture Notes"), ("creator", "Test Author"),
                             ("language", "en"), ("identifier", "urn:test:book")):
            with self.subTest(field=field):
                self.assert_error(self.publication(replacements={"EPUB/package.opf": PACKAGE.replace(f">{value}</dc:{field}>", f"></dc:{field}>")}), f"dc:{field}")
        self.assert_error(self.publication(replacements={"EPUB/package.opf": PACKAGE.replace('unique-identifier="book-id"', 'unique-identifier="missing"')}), "unique-identifier")

    def test_script_elements_handlers_and_javascript_urls_fail(self) -> None:
        for addition in ('<script>bad()</script>', '<p onclick="bad()">Text</p>',
                         '<a href="javascript:bad()">Bad link</a>'):
            with self.subTest(addition=addition):
                chapter = CHAPTER.replace("</body>", addition + "</body>")
                self.assertTrue(self.publication(replacements={"EPUB/chapters/chapter one.xhtml": chapter}))

    def test_archive_traversal_link_fails(self) -> None:
        chapter = CHAPTER.replace("../images/cover.png", "../../../cover.png")
        self.assert_error(self.publication(replacements={"EPUB/chapters/chapter one.xhtml": chapter}), "escapes the archive")

    def test_stylesheets_and_inline_styles_require_offline_resources(self) -> None:
        for style in ('body { background: url(https://example.com/image.png); }',
                      '@import "https://example.com/book.css";',
                      'body { background: url(//example.com/image.png); }'):
            with self.subTest(style=style):
                self.assert_error(self.publication(replacements={"EPUB/styles/book.css": style}), "external resource reference")
        self.assert_error(self.publication(replacements={"EPUB/styles/book.css": 'body { background: url(missing.png); }'}), "broken CSS url reference")
        chapter = CHAPTER.replace("</head>", '<style>body { background: url(https://example.com/image.png); }</style></head>')
        self.assert_error(self.publication(replacements={"EPUB/chapters/chapter one.xhtml": chapter}), "external resource reference")
        chapter = CHAPTER.replace('<h1 id=', '<h1 style="background:url(https://example.com/image.png)" id=')
        self.assert_error(self.publication(replacements={"EPUB/chapters/chapter one.xhtml": chapter}), "external resource reference")

    def test_malformed_url_fails_clearly(self) -> None:
        chapter = CHAPTER.replace('href="#section%3Aone"', 'href="http://[invalid"')
        self.assert_error(self.publication(replacements={"EPUB/chapters/chapter one.xhtml": chapter}), "invalid URL")

    def test_invalid_xml_and_missing_package_fail_clearly(self) -> None:
        self.assert_error(self.publication(replacements={"EPUB/nav.xhtml": "<html>"}), "Invalid XML")
        self.assert_error(self.publication(replacements={"EPUB/package.opf": None}), "Missing resource")

    def test_missing_and_invalid_archive_fail_clearly(self) -> None:
        self.assert_error(validate(self.path), "Cannot read EPUB")
        self.path.write_text("not a ZIP", encoding="utf-8")
        self.assert_error(validate(self.path), "Cannot read EPUB")


if __name__ == "__main__":
    unittest.main()
