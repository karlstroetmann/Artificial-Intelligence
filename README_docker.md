# Docker Container Stroetmann Vorlesung

## Container starten

Der folgende Befehl startet den Container im Hintergrund.

```bash
docker-compose up -d
```

Der folgende Befehl startet den Container in der aktuellen Konsole und baut ihn vorher neu.

Vorsicht hierbei, der Vorgang benötigt einige Zeit, sollte sofern nur bei einem Update genutzt werden.
```bash
docker-compose up --build
```

Sollte der Container bereits einmal gebaut worden sein, muss der folgende Befehl ausgeführt werden:

```bash
docker-compose up -d --build
```

## Container stoppen

Mit dem folgenden Befehl wird der Container gestoppt:

```bash
docker-compose down
```

## Zugriff auf Jupyter

[Jupyter Notebook](localhost:8888) öffnet den Zugriff auf Jupyter. Es wird kein Passwort oder Token benötigt.

## Eingebundene Bibliotheken

```text
- python=3.7
- jupyter
- nbconvert=5.6.1
- jupyter_contrib_nbextensions
- graphviz
- python-graphviz
- ply
- ipycanvas
- matplotlib
- seaborn
- tensorflow
- scikit-learn
- nltk
- pip:
    - jedi==0.17.2  
    - python-chess
```

## Quelle der Jupyterdaten

Alle Rechte an den Daten innerhalb des Ordners 'stroetmann-data' gehören [Prof. Dr. Karl Stroetmann](https://github.com/karlstroetmann/)
