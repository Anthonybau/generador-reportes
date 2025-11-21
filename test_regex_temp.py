import re


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


def buscar_fecha_sello(texto):
    # Solo buscamos en el encabezado
    cabecera = texto[:1000]

    patron = (
        r"Ayacucho.*?\s+(\d{1,2})\s*(?:de)?\s*([A-Za-z]{3,})\.?\s*(?:de|del)?\s*(\d{4})"
    )
    match = re.search(patron, cabecera, re.IGNORECASE)

    if match:
        d, m, a = match.groups()
        return formatear_fecha(d, m, a)

    # Fallback simple
    patron_simple = r"(\d{1,2})\s*(?:de)?\s*([A-Za-z]{3,})\.?\s*(?:de|del)?\s*(\d{4})"
    match_simple = re.search(patron_simple, cabecera, re.IGNORECASE)
    if match_simple:
        d, m, a = match_simple.groups()
        return formatear_fecha(d, m, a)

    return "Fecha no detectada"


# Test cases
test_cases = [
    "Ayacucho 05 SET. 2025",
    "Ayacucho 05 SET 2025",
    "05 SET. 2025",
    "05 de Septiembre de 2025",
]

for t in test_cases:
    print(f"'{t}' -> {buscar_fecha_sello(t)}")
