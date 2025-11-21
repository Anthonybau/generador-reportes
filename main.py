import os
import re
import pdfplumber
import pytesseract
from PIL import ImageEnhance
import pandas as pd

# --- CONFIGURACIÓN ---
CARPETA_PDFS = "./documentos_entrada"
ARCHIVO_SALIDA = "cargaRGM_final.xlsx"
URL_BASE_STORAGE = "https://tustorage.municipalidad.gob.pe/archivos/"

# RUTA TESSERACT
pytesseract.pytesseract.tesseract_cmd = r"D:\Programs\Tesseract-OCR\tesseract.exe"

# MAPEOS
TIPO_PUBLICACION_MAP = {
    "GERENCIA MUNICIPAL": 159,
    "ALCALDÍA": 89,
    "CONCEJO MUNICIPAL": 112,
    "ORDENANZA": 13,
}
CATEGORIA_DEFAULT = 54


def limpiar_texto_basico(texto):
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto).strip()


def preprocesar_imagen_para_handwriting(imagen):
    """
    Trucos de imagen para hacer legible el texto a mano:
    1. Convierte a escala de grises.
    2. Aumenta el contraste violentamente.
    3. Convierte a Blanco y Negro puro (Threshold) para engrosar trazos finos.
    """
    # 1. Escala de grises
    img = imagen.convert("L")

    # 2. Aumentar contraste (ayuda si el lapicero es azul o negro suave)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)  # Doble de contraste

    # 3. Binarización (Todo lo que no sea blanco puro se vuelve negro absoluto)
    # El valor 180 es el "umbral". Ajustable entre 100 y 200.
    # Si el texto a mano es muy claro, sube a 200. Si hay mucho ruido (puntos), baja a 150.
    fn = lambda x: 255 if x > 160 else 0  # noqa: E731
    img = img.point(fn, mode="1")

    return img


def extraer_texto_con_ocr(ruta_archivo):
    """
    Estrategia Mejorada:
    - Corta solo la CABECERA (25% superior) para buscar el título con filtros agresivos.
    - Lee el resto normal.
    """
    texto_completo = ""
    uso_ocr = False

    try:
        with pdfplumber.open(ruta_archivo) as pdf:
            for i, pagina in enumerate(pdf.pages):
                # --- PÁGINA 1: TRATAMIENTO ESPECIAL PARA MANUSCRITOS ---
                if i == 0:
                    uso_ocr = True
                    try:
                        # 1. Obtener imagen original de alta calidad
                        im_original = pagina.to_image(resolution=300).original

                        # 2. Recortar solo la cabecera (Top 25%) para evitar leer basura del pie de página
                        width, height = im_original.size
                        im_cabecera = im_original.crop((0, 0, width, height * 0.25))

                        # 3. Aplicar filtros para resaltar escritura a mano
                        im_procesada = preprocesar_imagen_para_handwriting(im_cabecera)

                        # 4. OCR a la cabecera procesada
                        # --psm 6: Asume bloque de texto. --oem 1: Neural Net (mejor para algo de manuscrito)
                        texto_cabecera = pytesseract.image_to_string(
                            im_procesada, lang="spa", config="--psm 6"
                        )

                        # 5. OCR al resto de la página (cuerpo) sin filtros agresivos (para leer bien el texto impreso)
                        im_cuerpo = im_original.crop((0, height * 0.25, width, height))
                        texto_cuerpo = pytesseract.image_to_string(
                            im_cuerpo, lang="spa"
                        )

                        texto_completo += texto_cabecera + "\n" + texto_cuerpo + "\n"

                    except Exception as e_ocr:
                        print(f"Error OCR pág 1: {e_ocr}")
                        texto_completo += pagina.extract_text() or ""
                else:
                    # Resto de páginas
                    texto_pagina = pagina.extract_text()
                    if texto_pagina and len(texto_pagina) > 50:
                        texto_completo += texto_pagina + "\n"
                    else:
                        try:
                            im = pagina.to_image(resolution=300).original
                            texto_completo += (
                                pytesseract.image_to_string(im, lang="spa") + "\n"
                            )
                        except Exception as e_img:
                            print(f"Error OCR pág {i}: {e_img}")
                            texto_completo += pagina.extract_text() or ""

    except Exception as e:
        print(f"Error leyendo archivo {ruta_archivo}: {e}")
        return "", False

    return texto_completo, uso_ocr


def buscar_titulo_resolucion_exacto(texto):
    """
    Busca formato NUMERO - AÑO - MPH en el primer bloque de texto (Cabecera).
    """
    # Limitamos la búsqueda a los primeros 500 caracteres para evitar falsos positivos abajo.
    cabecera = limpiar_texto_basico(texto[:800])

    # Regex optimizado:
    # (\d{1,5}) : Número (manuscrito o impreso)
    # [\s\._-]* : Separadores flexibles (el OCR a veces lee el guion manuscrito como punto o guion bajo)
    # (\d{4})   : Año
    # [\s\._-]*MPH : MPH final
    patron = r"(?:N[°ºo\.]?)?\s*(\d{1,5})[\s\._-]*(\d{4})[\s\._-]*MPH"

    match = re.search(patron, cabecera, re.IGNORECASE)
    if match:
        numero = match.group(1)
        anio = match.group(2)
        return f"{numero}-{anio}-MPH/GM"

    return "S/N (Manual)"


def buscar_fecha_sello(texto):
    # Solo buscamos en el encabezado
    cabecera = texto[:1000]

    patron = (
        r"Ayacucho.*?\s+(\d{1,2})\s*(?:de)?\s*([A-Za-z]{3,})\s*(?:de|del)?\s*(\d{4})"
    )
    match = re.search(patron, cabecera, re.IGNORECASE)

    if match:
        d, m, a = match.groups()
        return formatear_fecha(d, m, a)

    # Fallback simple
    patron_simple = r"(\d{1,2})\s*(?:de)?\s*([A-Za-z]{3,})\s*(?:de|del)?\s*(\d{4})"
    match_simple = re.search(patron_simple, cabecera, re.IGNORECASE)
    if match_simple:
        d, m, a = match_simple.groups()
        return formatear_fecha(d, m, a)

    return "Fecha no detectada"


def formatear_fecha(dia, mes_txt, anio):
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
    return f"{dia.zfill(2)}/{mes}/{anio}"


def extraer_parte_resolutiva(texto):
    if not texto:
        return ""
    texto_lineal = re.sub(r"\s+", " ", texto)

    patron = r"ART[ÍI]CULO\s+(?:PRIMERO|1[º°]?)\s*[\.\-—]?\s+(?P<contenido>.+?)(?=\s+(?:[A-ZÑa-z]|\W)?\s*ART[ÍI]CULO\s+SE(?:GUNDO|2)|REG[ÍI]STRESE|COMUN[ÍI]QUESE)"
    match = re.search(patron, texto_lineal, re.IGNORECASE)
    contenido = ""

    if match:
        contenido = match.group("contenido")
    else:
        patron_fb = r"(?:SE\s+)?RESUELVE\s*[:\.]?\s*(?P<contenido>.+?)(?=\s+(?:[A-ZÑ]|\W)?\s*ART[ÍI]CULO\s+SE(?:GUNDO|2)|REG[ÍI]STRESE)"
        m_fb = re.search(patron_fb, texto_lineal, re.IGNORECASE)
        if m_fb:
            contenido = m_fb.group("contenido")

    if contenido:
        contenido = re.sub(
            r"^[\W_]*ART[ÍI]CULO\s+(?:PRIMERO|1[º°]?)[\s\.\-—]*",
            "",
            contenido,
            flags=re.IGNORECASE,
        )
        contenido = re.sub(r"\s+[A-ZÑa-z]\.?$", "", contenido)
        return contenido.strip()

    return "Revisar contenido"


def determinar_tipo_id(texto):
    texto_upper = texto.upper()
    for clave, id_tipo in TIPO_PUBLICACION_MAP.items():
        if clave in texto_upper:
            return id_tipo
    return 10


def procesar_pdfs():
    if not os.path.exists(CARPETA_PDFS):
        os.makedirs(CARPETA_PDFS)
        print(f"Carpeta {CARPETA_PDFS} lista.")
        return

    archivos = [f for f in os.listdir(CARPETA_PDFS) if f.lower().endswith(".pdf")]
    lista_datos = []

    print(f"--- Procesando {len(archivos)} archivos ---")

    for archivo in archivos:
        print(f"-> Analizando: {archivo}")
        ruta = os.path.join(CARPETA_PDFS, archivo)

        texto_crudo, uso_ocr = extraer_texto_con_ocr(ruta)
        if not texto_crudo:
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
        ]
        df = df.reindex(columns=cols)
        df.to_excel(ARCHIVO_SALIDA, index=False)
        print(f"\n✅ EXCEL GENERADO: {ARCHIVO_SALIDA}")
    else:
        print("No se encontraron datos.")


if __name__ == "__main__":
    procesar_pdfs()
