import os
import re
import pdfplumber
import pytesseract
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
CARPETA_PDFS = "./documentos_entrada"
ARCHIVO_SALIDA = "cargaRGM_final.xlsx"
URL_BASE_STORAGE = "https://tustorage.municipalidad.gob.pe/archivos/"

# --- CONFIGURACIÓN DE TESSERACT (OCR) ---
# IMPORTANTE: Si estás en Windows, verifica que esta ruta sea la correcta donde instalaste Tesseract
# Si estás en Linux/Mac, generalmente no necesitas esta línea si instalaste tesseract-ocr
pytesseract.pytesseract.tesseract_cmd = r"D:\Programs\Tesseract-OCR\tesseract.exe"

# --- MAPEOS ---
TIPO_PUBLICACION_MAP = {
    "GERENCIA MUNICIPAL": 159,
    "ALCALDÍA": 89,
    "CONCEJO MUNICIPAL": 112,
    "ORDENANZA": 13,
}
CATEGORIA_DEFAULT = 54


def limpiar_texto(texto):
    """Elimina saltos de línea innecesarios y espacios múltiples"""
    if not texto:
        return ""
    # Reemplaza saltos de línea por espacios y elimina espacios dobles
    texto_limpio = re.sub(r"\s+", " ", texto).strip()
    return texto_limpio


def extraer_texto_con_ocr(ruta_archivo):
    """
    Estrategia híbrida:
    1. Intenta leer texto digital.
    2. Si encuentra muy poco texto (<50 caracteres), asume que es escaneado y usa OCR.
    """
    texto_completo = ""
    uso_ocr = False

    try:
        with pdfplumber.open(ruta_archivo) as pdf:
            for pagina in pdf.pages:
                # 1. Intento digital
                texto_pagina = pagina.extract_text()

                # Validación: Si hay poco texto, probablemente sea un escaneo sucio o imagen
                if not texto_pagina or len(texto_pagina) < 50:
                    uso_ocr = True
                    # 2. Conversión a Imagen y OCR (Requiere pytesseract y Ghostscript/Poppler instalados implícitamente por pdfplumber/PIL)
                    # Nota: pdfplumber to_image requiere que la librería 'Wand' o similar funcione,
                    # pero una forma más compatible es usar las propiedades de imagen si falla.
                    try:
                        im = pagina.to_image(resolution=300).original
                        texto_ocr = pytesseract.image_to_string(im, lang="spa")
                        texto_completo += texto_ocr + "\n"
                    except Exception as e_ocr:
                        print(f"Error en OCR de página: {e_ocr}")
                else:
                    texto_completo += texto_pagina + "\n"

    except Exception as e:
        print(f"Error grave leyendo archivo {ruta_archivo}: {e}")
        return "", False

    return texto_completo, uso_ocr


def extraer_parte_resolutiva(texto):
    """
    Extrae el contenido, limpia encabezados como '; ARTICULO PRIMERO.-'
    y elimina residuos finales.
    """
    if not texto:
        return ""

    # 1. Normalización: todo a una sola línea
    texto_lineal = re.sub(r"\s+", " ", texto)

    # 2. Regex de Búsqueda Principal
    # Busca el contenido entre el Artículo Primero y el Segundo (o final)
    # La clave aquí es que buscamos el BLOQUE, no nos preocupamos tanto por limpiar el inicio AÚN.
    patron = r"ART[ÍI]CULO\s+(?:PRIMERO|1[º°]?)\s*[\.\-—]?\s+(?P<contenido>.+?)(?=\s+(?:[A-ZÑa-z]|\W)?\s*ART[ÍI]CULO\s+SE(?:GUNDO|2)|REG[ÍI]STRESE|COMUN[ÍI]QUESE)"

    match = re.search(patron, texto_lineal, re.IGNORECASE)
    contenido = ""

    if match:
        contenido = match.group("contenido")
    else:
        # Fallback: Si falla, intentamos desde SE RESUELVE
        patron_fallback = r"(?:SE\s+)?RESUELVE\s*[:\.]?\s*(?P<contenido>.+?)(?=\s+(?:[A-ZÑ]|\W)?\s*ART[ÍI]CULO\s+SE(?:GUNDO|2)|REG[ÍI]STRESE)"
        match_fb = re.search(patron_fallback, texto_lineal, re.IGNORECASE)
        if match_fb:
            contenido = match_fb.group("contenido")

    if contenido:
        # --- 3. LIMPIEZA DE INICIO (EL FILTRO QUE NECESITAS) ---
        # Esto elimina "; ARTICULO PRIMERO.-" si se coló dentro de la captura.
        # ^[\W_]* : Busca al inicio cualquier símbolo raro (; . - espacio)
        # ART...  : Busca la palabra Artículo Primero
        # [\s\.\-—]* : Busca los separadores finales (.-)
        contenido = re.sub(
            r"^[\W_]*ART[ÍI]CULO\s+(?:PRIMERO|1[º°]?)[\s\.\-—]*",
            "",
            contenido,
            flags=re.IGNORECASE,
        )

        # --- 4. LIMPIEZA DE FINAL ---
        # Elimina letras sueltas al final ('A', 'Ñ')
        contenido = re.sub(r"\s+[A-ZÑa-z]\.?$", "", contenido)

        return contenido.strip()

    return "No se pudo detectar el contenido específico"


def buscar_titulo_resolucion(texto):
    # Busca patrón tipo: 641-2025-MPH/GM
    patron = r"(\d{3,4}-\d{4}-MPH/[A-Za-z]+)"
    match = re.search(patron, texto)
    if match:
        return match.group(1)
    return "S/N"


def buscar_fecha(texto):
    # Intenta buscar fechas
    patron_fecha = r"(\d{1,2}) de ([a-zA-Z]+) d?e?l? ?(\d{4})"
    match = re.search(patron_fecha, texto.lower())
    if match:
        dia, mes_txt, anio = match.groups()
        meses = {
            "enero": "01",
            "febrero": "02",
            "marzo": "03",
            "abril": "04",
            "mayo": "05",
            "junio": "06",
            "julio": "07",
            "agosto": "08",
            "septiembre": "09",
            "octubre": "10",
            "noviembre": "11",
            "diciembre": "12",
        }
        mes = meses.get(mes_txt, "01")
        return f"{dia.zfill(2)}/{mes}/{anio}"
    return datetime.now().strftime("%d/%m/%Y")


def determinar_tipo_id(texto):
    texto_upper = texto.upper()
    for clave, id_tipo in TIPO_PUBLICACION_MAP.items():
        if clave in texto_upper:
            return id_tipo
    return 10


def procesar_pdfs():
    if not os.path.exists(CARPETA_PDFS):
        os.makedirs(CARPETA_PDFS)
        print(f"Carpeta {CARPETA_PDFS} creada.")
        return

    archivos = [f for f in os.listdir(CARPETA_PDFS) if f.lower().endswith(".pdf")]
    lista_datos = []

    print(f"--- Iniciando procesamiento con OCR para {len(archivos)} archivos ---")

    for archivo in archivos:
        print(f"Leyendo: {archivo}...")
        ruta = os.path.join(CARPETA_PDFS, archivo)

        # 1. Extracción (Texto + OCR si es necesario)
        texto_crudo, uso_ocr = extraer_texto_con_ocr(ruta)

        if not texto_crudo:
            print(f"⚠️ Advertencia: No se pudo leer {archivo}")
            continue

        # 2. Procesamiento de Texto
        titulo = buscar_titulo_resolucion(texto_crudo)
        fecha = buscar_fecha(texto_crudo)
        tipo_id = determinar_tipo_id(texto_crudo)

        # AQUÍ ESTÁ EL CAMBIO CLAVE: Extracción del "Se Resuelve"
        descripcion_resolutiva = extraer_parte_resolutiva(texto_crudo)

        # 3. Armado de fila
        fila = {
            "Título": titulo,
            "Nombre de norma (opcional)": descripcion_resolutiva,
            "Descripción": descripcion_resolutiva,
            "Fecha de publicación (dd/mm/yyyy)": fecha,
            "Archivo": f"{URL_BASE_STORAGE}{archivo}",
            "publication_type_id": tipo_id,
            "category_id": CATEGORIA_DEFAULT,
            "Nombre de Archivo": f"RESOLUCION {titulo}",
            "Compendios Normas ids": "",
            "Descripción del documento": f"Archivo PDF (OCR:{'Sí' if uso_ocr else 'No'}) - {titulo}",
            "RUTA TEMP": archivo,
        }
        lista_datos.append(fila)

    if lista_datos:
        df = pd.DataFrame(lista_datos)
        # Columnas ordenadas según tu CSV
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
        ]
        df = df.reindex(columns=cols)
        df.to_excel(ARCHIVO_SALIDA, index=False)
        print(f"\n✅ Éxito. Excel generado: {ARCHIVO_SALIDA}")
    else:
        print("No se generaron datos.")


if __name__ == "__main__":
    procesar_pdfs()
