# 📄 Automatización de Procesamiento de PDFs

## UTIC – Municipalidad Provincial de Huamanga

**Proyecto:** Generación automática de reportes desde PDFs
**Responsable:** Ledvir Anthony Bautista Pérez (Practicante)
**Tecnologías:** Python · pdfplumber · Tesseract OCR · pandas · Pillow

---

## 🧠 ¿Qué hace este proyecto?

Este sistema automatiza la lectura y extracción de información desde **PDFs de resoluciones y documentos oficiales**, incluso cuando están **escaneados o con mala calidad**.

El proceso genera un Excel consolidado (`cargaRGM_final.xlsx`) listo para ser cargado en los sistemas internos de la municipalidad.

### 🔄 Flujo principal

1. Coloca PDFs en `./documentos_entrada/`
2. Se extrae texto:

   * Con **pdfplumber** si es PDF digital
   * Con **Tesseract OCR** si es escaneado
3. Se detecta:

   * Número de resolución
   * Fecha
   * Parte resolutiva
   * Tipo de publicación
4. Se genera un **Excel final limpio y estandarizado**

---

## 📁 Estructura del repositorio

```sh
.
├─ documentos_entrada/        # PDFs a procesar
├─ procesar_pdfs.py           # Script principal
├─ cargaRGM_final.xlsx         # Resultado generado
├─ requirements.txt
├─ Dockerfile (opcional)
└─ README.md
```

---

## 🗂️ Archivo principal

### `procesar_pdfs.py`

Contiene:

* Preprocesamiento de imágenes para OCR
* Extracción de texto (pdfplumber + Tesseract)
* Heurísticas para detectar título, fecha y parte resolutiva
* Generación automática del Excel final

---

## 🛠️ Requisitos

### 📌 Software del sistema

| Sistema              | Instalación de Tesseract                           |
| -------------------- | -------------------------------------------------- |
| **Windows**          | Instalar Tesseract y establecer ruta en el script  |
| **Ubuntu / Debian**  | `sudo apt install tesseract-ocr tesseract-ocr-spa` |
| **macOS (Homebrew)** | `brew install tesseract tesseract-lang`            |

> Es necesario instalar el idioma **spa (español)**.

---

## 🧰 Instalación de dependencias (con uv o pip)

Si usas **uv** (recomendado):

```bash
uv sync
```

Si usas pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Configuración del script

En `procesar_pdfs.py` puedes ajustar:

```python
CARPETA_PDFS = "./documentos_entrada"
ARCHIVO_SALIDA = "cargaRGM_final.xlsx"
URL_BASE_STORAGE = "https://tustorage.municipalidad.gob.pe/archivos/"

# Windows
pytesseract.pytesseract.tesseract_cmd = r"D:\Programs\Tesseract-OCR\tesseract.exe"
```

---

## ▶️ Cómo usar

1. Coloca tus PDFs en `documentos_entrada/`
2. Ejecuta:

```bash
python procesar_pdfs.py
```

3. El resultado se guardará como:

```text
cargaRGM_final.xlsx
```

---

## 📊 Columnas del Excel generado

* **Título**
* **Nombre de norma**
* **Descripción (parte resolutiva)**
* **Fecha de publicación**
* **Archivo (URL generada)**
* **publication_type_id**
* **category_id**
* **Nombre de Archivo**
* **Compendios Normas ids**
* **Descripción del documento**
* **RUTA TEMP**
* **OCR usado**

---

## 🔍 Cómo funciona internamente (resumen técnico)

### 🧼 Preprocesamiento de imágenes

* Conversión a escala de grises
* Contraste y binarización
* Limpieza de ruido
* Recorte estratégico en página 1 (25% superior)

### 🔎 Detección con heurísticas

* Títulos tipo: `Nº ###-2024-MPH`
* Fechas:

  * `dd/mm/yyyy`
  * `12 de abril de 2024`
* Parte resolutiva basada en patrones:

  * “SE RESUELVE”
  * “ARTÍCULO PRIMERO”

---

## 🐳 Docker (opcional)

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr tesseract-ocr-spa \
    poppler-utils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "procesar_pdfs.py"]
```

---

## 🧪 Tests recomendados

* Detección de fechas
* Patrón de título
* Extracción de parte resolutiva
* OCR vs pdfplumber

---

## 🛠️ Problemas comunes

| Problema                 | Solución                                  |
| ------------------------ | ----------------------------------------- |
| *TesseractNotFoundError* | Configurar la ruta de Tesseract (Windows) |
| Texto muy pobre          | Subir resolución a 300 DPI                |
| pdfplumber falla         | Instalar poppler                          |
| Excel no se genera       | Revisar permisos / openpyxl               |

---

## 📌 Licencia

Este material se entrega como recurso académico/técnico. Puedes adaptarlo libremente (MIT recomendado).

---

## 📨 Contacto

**Autor:** Ledvir Anthony Bautista Pérez
**Proyecto:** Prácticas UTIC — Municipalidad Provincial de Huamanga
