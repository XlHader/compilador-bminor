# Proyecto Python Base

Base inicial para trabajar con Python usando buenas practicas modernas:

- Estilo PEP 8 automatizado con Ruff (lint + format).
- Dependencias en `requirements.txt` y `requirements-dev.txt` para trabajar con `venv`.
- Salida de consola usando `rich`.
- Logging con `loguru` hacia archivo en `logs/`.
- Estructura `src/` para evitar problemas de imports.

## Requisitos

- Python 3.11+

## Inicio rapido

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m proyect.main
```

## Calidad de codigo

```bash
ruff check .
ruff check --fix .
ruff format .
pytest
```
