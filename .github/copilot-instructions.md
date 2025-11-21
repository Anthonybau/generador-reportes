**Project Overview**

- **Purpose:** Script para extraer la parte resolutiva de PDFs (resoluciones), normalizar metadatos y generar un Excel (`cargaRGM_final.xlsx`). El entrypoint principal es `main.py`.
- **Input folder:** `documentos_entrada/` — colocar ahí los PDFs a procesar.
- **Output:** archivo Excel definido por la constante `ARCHIVO_SALIDA` en `main.py`.

**Key Files**

- `main.py`: lógica única del proyecto — lectura de PDFs, extracción (texto digital + OCR), parsing con regex, armado del DataFrame y exportación a Excel.
- `pyproject.toml`: dependencias (ver sección "Dependencias y entorno").
- `documentos_entrada/`: carpeta de entrada usada por `main.py`.

**Dependencias y entorno**

- Requiere Python >= 3.12 (mirar `pyproject.toml`).
- Dependencias principales: `pdfplumber`, `pytesseract`, `pillow`, `pandas`, `openpyxl`.
- Requisitos adicionales fuera de pip:
  - Tesseract OCR instalado en el sistema. En Windows configure la ruta en `main.py`: `pytesseract.pytesseract.tesseract_cmd`.
  - Herramientas para renderizar PDFs como imagen (Poppler o Ghostscript) si `pdfplumber` necesita generar imágenes para OCR.

**Cómo ejecutar (rápido)**

- Instalar dependencias (PowerShell):

```powershell
python -m pip install --upgrade pip
python -m pip install pandas openpyxl pdfplumber pillow pytesseract
```

- Ejecutar el script:

```powershell
python .\main.py
```

Colocar PDFs en `documentos_entrada/` y luego ejecutar; el Excel se genera en el mismo directorio.

**Patrones y convenciones del código**

- Nombres y comentarios en español; constantes globales en mayúsculas (`CARPETA_PDFS`, `ARCHIVO_SALIDA`, `URL_BASE_STORAGE`).
- Estrategia de extracción: primero intenta texto digital con `pdfplumber`, y si la página tiene menos de 50 caracteres se activa OCR (función `extraer_texto_con_ocr`). El umbral de 50 caracteres es un comportamiento específico del proyecto.
- La extracción principal de la parte resolutiva está en `extraer_parte_resolutiva(texto)` y usa un regex adaptado para ruido de OCR (p. ej. busca `ARTÍCULO PRIMERO` y corta en `ARTÍCULO SEGUNDO` o tokens similares).
- Mapeos fijos: `TIPO_PUBLICACION_MAP` y `CATEGORIA_DEFAULT` contienen IDs numéricos que el proyecto usa para `publication_type_id` y `category_id`.
- Orden de columnas de salida: la lista `cols` en `procesar_pdfs()` define el orden final del Excel. Mantenerla si se agregan columnas.

**Qué revisar si algo falla**

- Si no hay texto o el OCR produce basura: verificar `pytesseract.pytesseract.tesseract_cmd` y que Tesseract esté instalado y accesible.
- Si `pagina.to_image()` falla o no genera imagen: instalar Poppler/Ghostscript o ajustar la estrategia (usar `pdfplumber` con configuración de imágenes alternativa).
- Si la extracción del artículo no es correcta: probar y ajustar `patron` en `extraer_parte_resolutiva`. Ejemplo de entrada problemática: OCR que inserta caracteres como `Ñ` o barras — el patrón ya contempla varios de esos ruidos.

**Ejemplos útiles para un AI coding agent**

- Cambiar la ruta de Tesseract (Windows): editar la línea en `main.py` cerca del inicio:

```python
pytesseract.pytesseract.tesseract_cmd = r"D:\Programs\Tesseract-OCR\tesseract.exe"
```

- Ajustar el umbral OCR: buscar `if not texto_pagina or len(texto_pagina) < 50:` y cambiar `50` por otro número si los PDFs digitales son cortos.

- Ver y editar los IDs de tipo/publicación: `TIPO_PUBLICACION_MAP` en `main.py`.

**Limitaciones y notas**

- No hay tests ni CI en el repo — cualquier cambio en `main.py` debería verificarse con PDFs de ejemplo manualmente.
- `README.md` está vacío; actualizarlo si se añaden instrucciones de despliegue o ejemplos de PDF de prueba.

**Si necesitas más (preguntas concretas)**

- ¿Quieres que añada un `requirements.txt` o un pequeño script de tests para validar la extracción con 2-3 PDFs de ejemplo?
- ¿Prefieres que convierta este script en una CLI con argumentos (input folder, output path, umbral OCR)?

---

Archivo generado/actualizado por agente: si hay contenido previo en `.github/copilot-instructions.md`, fusiona manualmente las secciones importantes (no existen instrucciones previas detectadas en este repo).
