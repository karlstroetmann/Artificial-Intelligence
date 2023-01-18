PROJNAME=artificial-intelligence
.PHONY: $(PROJNAME).pdf all clean

all: $(PROJNAME).pdf

# MAIN LATEXMK RULE

$(PROJNAME).pdf: $(PROJNAME).tex | $(build_dir)
	latexmk -bibtex -pdf -pdflatex="pdflatex  --shell-escape %O %S -interactive=nonstopmode" -use-make $<

clean:
	latexmk -c -bibtex
	rm -r "_minted-$(PROJNAME)"
