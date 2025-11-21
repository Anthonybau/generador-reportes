#!/usr/bin/env python3
import os
import re
import sys
import logging
from logging.handlers import RotatingFileHandler
import pdfplumber
import pytesseract
from PIL import ImageEnhance, ImageFilter, ImageOps
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
CARPETA_PDFS = "./documentos_entrada"
ARCHIVO_SALIDA = "cargaRGM_final.xlsx"
URL_BASE_STORAGE = "https://tustorage.municipalidad.gob.pe/archivos/"

# RUTA TESSERACT (ajusta según tu SO)
pytesseract.pytesseract.tesseract_cmd = r"D:\Programs\Tesseract-OCR\tesseract.exe"

# MAPEOS
TIPO_PUBLICACION_MAP = {
    "GERENCIA MUNICIPAL": 159,
    "ALCALDÍA": 89,
    "CONCEJO MUNICIPAL": 112,
    "ORDENANZA": 13,
}
CATEGORIA_DEFAULT = 54

# Logging
LOG_FILE = "procesamiento_pdfs.log"
logger = logging.getLogger("proc_pdfs")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
)
fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
handler.setFormatter(fmt)
logger.addHandler(handler)
console = logging.StreamHandler(sys.stdout)
console.setFormatter(fmt)
logger.addHandler(console)


def limpiar_texto_basico(texto: str) -> str:
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto).strip()


def preprocesar_imagen_para_handwriting(imagen):
    """Preprocesado robusto: escala, contraste, mediana, binarización."""
    img = imagen.convert("L")
    img = img.filter(ImageFilter.MedianFilter(size=3))
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    # Invertir si fondo oscuro (opcional) - detecta brillo medio
    stat = img.point(lambda p: p).getextrema()
    # binarización con umbral configurado
    fn = lambda x: 255 if x > 160 else 0
    img = img.point(fn, mode="1")
    return img


def extraer_texto_con_ocr(ruta_archivo):
    texto_completo = ""
    uso_ocr = False
    try:
        with pdfplumber.open(ruta_archivo) as pdf:
            for i, pagina in enumerate(pdf.pages):
                try:
                    text = pagina.extract_text()
                except Exception:
                    text = None

                # Si página 1, aplicar estrategia mixta (cabecera+resto)
                if i == 0:
                    # Solo si la página es probable escaneada o texto corto, hacer OCR
                    if not text or len(text) < 100:
                        uso_ocr = True
                    try:
                        img_page = pagina.to_image(resolution=300).original
                        width, height = img_page.size
                        # Crop con int
                        top_h = int(height * 0.25)
                        im_cabecera = img_page.crop((0, 0, width, top_h))
                        im_cuerpo = img_page.crop((0, top_h, width, height))
                        texto_cabecera = ""
                        try:
                            im_proc = preprocesar_imagen_para_handwriting(im_cabecera)
                            texto_cabecera = pytesseract.image_to_string(
                                im_proc, lang="spa", config="--psm 6 --oem 1"
                            )
                        except Exception as e:
                            logger.debug(f"OCR cabecera fallo: {e}")
                        texto_cuerpo = ""
                        try:
                            texto_cuerpo = pytesseract.image_to_string(
                                im_cuerpo, lang="spa"
                            )
                        except Exception as e:
                            logger.debug(f"OCR cuerpo fallo: {e}")
                        # Si extrajo poco, tomar extract_text fallback
                        if (not texto_cabecera and not texto_cuerpo) and text:
                            texto_completo += text + "\n"
                        else:
                            texto_completo += (
                                texto_cabecera + "\n" + texto_cuerpo + "\n"
                            )
                    except Exception as e:
                        logger.warning(f"Error OCR página 0 en {ruta_archivo}: {e}")
                        texto_completo += text or ""
                else:
                    # Resto de páginas: preferir extract_text, sino OCR de la página
                    if text and len(text) > 50:
                        texto_completo += text + "\n"
                    else:
                        try:
                            img = pagina.to_image(resolution=300).original
                            texto_completo += (
                                pytesseract.image_to_string(img, lang="spa") + "\n"
                            )
                        except Exception as e:
                            logger.debug(f"OCR página {i} falló: {e}")
                            texto_completo += text or ""
    except Exception as e:
        logger.error(f"Error abriendo {ruta_archivo}: {e}")
        return "", False

    return texto_completo, uso_ocr


def buscar_titulo_resolucion_exacto(texto):
    cabecera = limpiar_texto_basico(texto[:800])
    patron = (
        r"(?:N[°ºo\.]?)?\s*(\d{1,5})[\s\._-]*(\d{4})[\s\._-]*(MPH|MP|M.PH|MP-H|MPH/GM)?"
    )
    match = re.search(patron, cabecera, re.IGNORECASE)
    if match:
        numero = match.group(1)
        anio = match.group(2)
        sufijo = match.group(3) or "MPH"
        return f"{numero}-{anio}-{sufijo}".upper()
    return "S/N (Manual)"


def formatear_fecha(dia, mes_txt, anio):
    try:
        mes_txt = mes_txt.lower().strip()[:3]
        meses = {
            "ene": "01",
            "jan": "01",
            "feb": "02",
            "mar": "03",
            "abr": "04",
            "apr": "04",
            "may": "05",
            "jun": "06",
            "jul": "07",
            "ago": "08",
            "aug": "08",
            "set": "09",
            "sep": "09",
            "oct": "10",
            "nov": "11",
            "dic": "12",
            "dec": "12",
        }
        mes = meses.get(mes_txt, "01")
        d = str(int(dia)).zfill(2)
        return f"{d}/{mes}/{anio}"
    except Exception:
        return "01/01/1900"


def buscar_fecha_sello(texto):
    # Primero, buscar dd/mm/yyyy
    m = re.search(r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})", texto)
    if m:
        d, mth, y = m.groups()
        return f"{int(d):02d}/{int(mth):02d}/{y}"

    # Buscar formatos escritos (Ayacucho ... 12 de abril de 2024)
    cabecera = texto[:1000]
    patron = (
        r"Ayacucho.*?(\d{1,2})\s*(?:de)?\s*([A-Za-z]{3,})\.?\s*(?:de|del)?\s*(\d{4})"
    )
    match = re.search(patron, cabecera, re.IGNORECASE)
    if match:
        return formatear_fecha(*match.groups())

    # Fallback: buscar cualquier "12 de abril 2024"
    patron_simple = r"(\d{1,2})\s*(?:de)?\s*([A-Za-z]{3,})\.?\s*(?:de|del)?\s*(\d{4})"
    match_simple = re.search(patron_simple, cabecera, re.IGNORECASE)
    if match_simple:
        return formatear_fecha(*match_simple.groups())

    return "Fecha no detectada"


def extraer_parte_resolutiva(texto):
    if not texto:
        return ""
    texto_lineal = re.sub(r"\s+", " ", texto)
    patrones = [
        r"ART[ÍI]CULO\s+(?:PRIMERO|1[º°]?)\s*[\.\-—]?\s+(?P<c>.+?)(?=\s+(?:ART[ÍI]CULO|REG[ÍI]STRESE|COMUN[ÍI]QUESE|FIRMA))",
        r"(?:SE\s+)?RESUELVE\s*[:\.]?\s*(?P<c>.+?)(?=\s+(?:ART[ÍI]CULO|REG[ÍI]STRESE|FIRMA))",
    ]
    contenido = ""
    for p in patrones:
        m = re.search(p, texto_lineal, re.IGNORECASE)
        if m:
            contenido = m.group("c").strip()
            break
    if contenido:
        contenido = re.sub(
            r"^ART[ÍI]CULO\s+PRIMERO[\s\.\-—]*", "", contenido, flags=re.IGNORECASE
        )
        # Limita longitud razonable
        return contenido[:2000].strip()
    return "Revisar contenido"


def determinar_tipo_id(texto):
    texto_upper = (texto or "").upper()
    for clave, id_tipo in TIPO_PUBLICACION_MAP.items():
        if clave in texto_upper:
            return id_tipo
    return 10


def procesar_pdfs():
    carpeta = os.path.abspath(CARPETA_PDFS)
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
        logger.info(f"Carpeta {carpeta} creada. Coloca los PDFs y vuelve a ejecutar.")
        return

    archivos = [f for f in os.listdir(carpeta) if f.lower().endswith(".pdf")]
    lista_datos = []
    logger.info(f"--- Procesando {len(archivos)} archivos ---")

    for archivo in archivos:
        logger.info(f"Analizando: {archivo}")
        ruta = os.path.join(carpeta, archivo)
        texto_crudo, uso_ocr = extraer_texto_con_ocr(ruta)
        if not texto_crudo:
            logger.warning(f"No se extrajo texto de {archivo}")
            continue

        titulo = buscar_titulo_resolucion_exacto(texto_crudo)
        fecha = buscar_fecha_sello(texto_crudo)
        descripcion = extraer_parte_resolutiva(texto_crudo)
        tipo_id = determinar_tipo_id(texto_crudo)
        nombre_norma = limpiar_texto_basico(descripcion)[:200]

        fila = {
            "Título": titulo,
            "Nombre de norma (opcional)": nombre_norma,
            "Descripción": descripcion,
            "Fecha de publicación (dd/mm/yyyy)": fecha,
            "Archivo": f"{URL_BASE_STORAGE}{archivo}",
            "publication_type_id": tipo_id,
            "category_id": CATEGORIA_DEFAULT,
            "Nombre de Archivo": f"RESOLUCION {titulo}",
            "Compendios Normas ids": "",
            "Descripción del documento": f"Documento {titulo}",
            "RUTA TEMP": archivo,
            "OCR usado": uso_ocr,
        }
        lista_datos.append(fila)

    if lista_datos:
        df = pd.DataFrame(lista_datos)
        cols = [
            "Título",
            "Nombre de norma (opcional)",
            "Descripción",
            "Fecha de publicación (dd/mm/yyyy)",
            "Archivo",
            "publication_type_id",
            "category_id",
            "Nombre de Archivo",
            "Compendios Normas ids",
            "Descripción del documento",
            "RUTA TEMP",
            "OCR usado",
        ]
        df = df.reindex(columns=cols)
        try:
            df.to_excel(ARCHIVO_SALIDA, index=False, engine="openpyxl")
            logger.info(f"✅ EXCEL GENERADO: {ARCHIVO_SALIDA}")
        except Exception as e:
            logger.error(f"Error guardando Excel: {e}")
    else:
        logger.info("No se encontraron datos.")


if __name__ == "__main__":
    procesar_pdfs()
