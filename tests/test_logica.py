import pytest
from procesador_pdfs import (
    limpiar_texto_basico,
    buscar_titulo_resolucion_exacto,
    formatear_fecha,
    buscar_fecha_sello,
    determinar_tipo_id,
    extraer_parte_resolutiva,
)


# --- 1. Test de Limpieza Básica ---
def test_limpiar_texto_basico():
    assert limpiar_texto_basico(None) == ""
    assert limpiar_texto_basico("  Hola   Mundo  ") == "Hola Mundo"
    assert limpiar_texto_basico("Texto\ncon\nsaltos") == "Texto con saltos"


# --- 2. Test de Títulos (Regex Crítico) ---
@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("RESOLUCIÓN DE ALCALDÍA Nº 568-2025-MPH/GM", "568-2025-MPH/GM"),  # Caso ideal
        ("N° 1090 - 2025 - MPH", "1090-2025-MPH"),  # Espacios y guiones
        ("471 2025 MPH", "471-2025-MPH"),  # Sin guiones (simulando OCR malo)
        ("N. 1 - 2025 - MPH", "1-2025-MPH"),  # Dígito único
        (
            "Texto basura antes 123-2025-MPH texto despues",
            "123-2025-MPH",
        ),  # Extracción en sucio
        ("No hay numero aqui", "S/N (Manual)"),  # Caso fallido
    ],
)
def test_buscar_titulo_resolucion(input_text, expected):
    resultado = buscar_titulo_resolucion_exacto(input_text)
    assert resultado == expected


# --- 3. Test de Formateo de Fechas (Lógica interna) ---
def test_formatear_fecha():
    assert formatear_fecha("5", "enero", "2025") == "05/01/2025"
    assert formatear_fecha("12", "set", "2024") == "12/09/2024"  # Abreviatura
    assert formatear_fecha("1", "Aug", "2023") == "01/08/2023"  # Inglés/Mayúscula
    assert (
        formatear_fecha("30", "MesInvalido", "2025") == "30/01/2025"
    )  # Fallback a Enero


# --- 4. Test de Búsqueda de Fecha en Sello (Regex Sello) ---
@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("Ayacucho, 05 de Setiembre de 2025", "05/09/2025"),
        ("Ayacucho 05 SET 2025", "05/09/2025"),  # Sin 'de'
        ("Lima, 10 de Octubre 2024", "10/10/2024"),  # Sin Ayacucho (Fallback)
        ("Texto random sin fecha", "Fecha no detectada"),
    ],
)
def test_buscar_fecha_sello(input_text, expected):
    assert buscar_fecha_sello(input_text) == expected


# --- 5. Test de IDs de Publicación ---
def test_determinar_tipo_id():
    assert determinar_tipo_id("RESOLUCIÓN DE ALCALDÍA") == 89
    assert determinar_tipo_id("Resolucion Gerencia Municipal N 123") == 159
    assert determinar_tipo_id("DOCUMENTO DESCONOCIDO") == 10  # Default


# --- 6. Test de Extracción de Contenido (Parte Resolutiva) ---
def test_extraer_parte_resolutiva():
    texto_ejemplo = """
    VISTOS: El informe técnico...
    SE RESUELVE:
    ARTICULO PRIMERO.- APROBAR el plan de trabajo del 2025.
    ARTICULO SEGUNDO.- NOTIFICAR a las partes.
    REGISTRESE Y COMUNIQUESE.
    """
    # Debería capturar solo lo que hay entre PRIMERO y SEGUNDO
    esperado = "APROBAR el plan de trabajo del 2025."

    resultado = extraer_parte_resolutiva(texto_ejemplo)
    assert resultado == esperado


def test_extraer_parte_resolutiva_sucia():
    # Simula error OCR al inicio
    texto_sucio = "; ARTICULO PRIMERO.- DESIGNAR al funcionario..."
    esperado = "DESIGNAR al funcionario..."
    assert extraer_parte_resolutiva(texto_sucio) == esperado
