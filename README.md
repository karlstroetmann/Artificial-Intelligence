# Lecture Notes on Artificial Intelligence

These are the resources for my lecture on artificial intelligence.
The directory `Lecture-Notes` contains the LaTeX files, while the directory `Python` contains
*jupyter* notebooks that implement the algorithms discussed in my lecture.

Download the lecture notes: [PDF](Lecture-Notes/artificial-intelligence.pdf?raw=true)
or [EPUB](Lecture-Notes/artificial-intelligence.epub?raw=true).
Both finished books are included in the repository; no build tools are needed to read them.

## Export PDF and EPUB

### macOS setup

Set up [Homebrew](https://docs.brew.sh/Installation), including its shell instructions,
then install full [MacTeX](https://formulae.brew.sh/cask/mactex-no-gui) and the export tools:

```sh
xcode-select --install                 # if Command Line Tools are missing
brew install --cask mactex-no-gui       # skip if current full MacTeX is installed
brew install python ghostscript mupdf-tools epubcheck
export PATH="/Library/TeX/texbin:$(brew --prefix)/bin:$PATH"
```

Use Python 3.10+ and EPUBCheck 5.4+; Homebrew's
[EPUBCheck package](https://formulae.brew.sh/formula/epubcheck) includes Java.
On other systems, use full TeX Live plus Python, Ghostscript, MuPDF (`mutool`), ZIP
and EPUBCheck with Java. All tools must be on `PATH`; no Python packages are required.

### Build

From the repository root:

```sh
make -C Lecture-Notes
```

This builds `Lecture-Notes/artificial-intelligence.pdf` and
`Lecture-Notes/artificial-intelligence.epub` from the same LaTeX source.
Append `pdf` or `epub` to build one format, `check-epub` to validate an existing EPUB,
or `clean` to remove temporary files.

If a command is missing, check the installations and `PATH` above.
EPUB build diagnostics are in `Lecture-Notes/.build/epub/export.log`;
a failed export preserves the previous EPUB. Nonstandard Ghostscript installations
may need [`LIBGS`](https://dvisvgm.de/Manpage/).

The EPUB is reflowable and works offline, with searchable text, navigation, code,
linked figures/equations, bibliography, footnotes and index. Mathematics and diagrams
use SVG with text alternatives; the PDF retains its print layout. EPUBCheck must pass
without warnings before publication. SVG is not structured MathML, and reader support
varies; check the book in the intended reading applications before release.
