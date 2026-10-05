# Lecture Notes on Artificial Intelligence

These are the resources for my lecture on artificial intelligence.
The directory `Lecture-Notes` contains the LaTeX files, while the directory `Python` contains
*jupyter* notebooks that implement the algorithms discussed in my lecture.

## Export the lecture notes

Run the existing pipeline to build both formats from the same LaTeX source:

```sh
make -C Lecture-Notes
```

The outputs are `Lecture-Notes/artificial-intelligence.pdf` and
`Lecture-Notes/artificial-intelligence.epub`. Use `make -C Lecture-Notes pdf`
or `make -C Lecture-Notes epub` to build one format independently.

The EPUB is a native, reflowable EPUB 3 book: searchable text, a cover,
chapter/section navigation, numbered theorems and exercises, code listings,
tables, linked figures, citations, bibliography, footnotes, and a linked index.
Mathematics, TikZ diagrams, and PDF/EPS figures are rendered locally as SVG;
formula dimensions follow the reading application's font size. The book embeds
its assets and styles and needs neither network access nor JavaScript to read.
Print page references are omitted in the EPUB; figure/equation links still take
you to their targets. The PDF retains its print layout.

### Dependencies

Use a current TeX Live distribution with `latexmk`, `tex4ebook`, `make4ht`,
`tex4ht`, `luaxml`, `dvisvgm`, BibTeX, makeindex, and the document's LaTeX
packages (including `minted` and its `latexminted` executable). Also install
Python 3.10 or later, Ghostscript, ZIP, and EPUBCheck 5.4 or
later with Java. The notebook Docker image does not include the book toolchain.
For dvisvgm builds without built-in PDF support, also install MuPDF's `mutool`;
recent Ghostscript versions cannot supply its PDF conversion backend.

For a minimal TeX Live installation such as TinyTeX:

```sh
tlmgr update --self
tlmgr install tex4ebook make4ht tex4ht luaxml dvisvgm latexmk \
  collection-latexrecommended collection-fontsrecommended \
  a4wide minted stmaryrd xfrac yfonts yfonts-t1 gothic placeins tocbibind lastpage
```

On macOS, install the remaining tools with Homebrew:

```sh
brew install ghostscript mupdf-tools epubcheck
```

On Debian/Ubuntu, the corresponding packages include `ghostscript`,
`mupdf-tools`, `zip`, and `epubcheck`. Verify the packaged EPUBCheck version;
older distributions may require the [official release](https://github.com/w3c/epubcheck/releases).
For macOS Homebrew Ghostscript, the exporter locates the library automatically.
Other nonstandard installations may need `LIBGS` set as described in the
[dvisvgm manual](https://dvisvgm.de/Manpage/).

### Validation and reading quality

Every EPUB export checks all local resources and cross-reference targets, then
runs EPUBCheck with `--failonwarnings`. Converter errors, unresolved references,
and HTML repair also fail the export to prevent silent content corruption.
The output is replaced only after these
gates pass. An unsuccessful build keeps the previous EPUB and diagnostics in
`Lecture-Notes/.build/epub/export.log`; PDF and EPUB auxiliary files are isolated,
including when running `make -j`. `make clean` removes temporary build files.

```sh
make -C Lecture-Notes test-epub   # Fast fixture tests; no TeX installation needed
make -C Lecture-Notes check-epub # Recheck the exported book
```

Reading styles use relative sizes, preserve code indentation, and accommodate
wide tables and equations without shrinking their text. Reader-selected fonts
and themes take precedence. SVG mathematics favors visual compatibility with
reading systems that do not implement MathML. Formula text alternatives are
included, but they are not structured MathML; diagrams use their figure captions
as alternatives. This is not a claim of full screen-reader accessibility.

EPUBCheck establishes standards conformance, not identical behavior in every
reading application. Before release, open the EPUB in the target readers (for
example Apple Books, Thorium, and an e-ink device) and check navigation, enlarged
fonts, themes, wide equations/tables, code, and footnotes. Reader-specific support
for SVG, scrolling, and styles varies. Export-specific configuration and styling
live in `Lecture-Notes/epub/`; the LaTeX remains the content source.
