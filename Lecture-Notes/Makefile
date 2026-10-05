PROJNAME=artificial-intelligence
PYTHON ?= python3
.PHONY: $(PROJNAME).pdf $(PROJNAME).epub all pdf epub check-epub test-epub clean

all: pdf epub

pdf: $(PROJNAME).pdf

epub: $(PROJNAME).epub

# MAIN LATEXMK RULE

$(PROJNAME).pdf: $(PROJNAME).tex
	latexmk -bibtex -pdf -pdflatex="pdflatex --shell-escape %O %S -interaction=nonstopmode -halt-on-error" -use-make $<

$(PROJNAME).epub: $(PROJNAME).tex
	$(PYTHON) epub/export_epub.py $<

check-epub:
	$(PYTHON) epub/check_epub.py $(PROJNAME).epub
	epubcheck --failonwarnings $(PROJNAME).epub

test-epub:
	$(PYTHON) -m unittest discover -s epub -p 'test_*.py'

clean:
	latexmk -c -bibtex
	$(PYTHON) -c 'import shutil; from pathlib import Path; [shutil.rmtree(path, ignore_errors=True) for path in (Path("_minted-$(PROJNAME)"), Path("_minted"), Path(".build/epub"))]'
