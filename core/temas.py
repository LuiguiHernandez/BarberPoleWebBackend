"""
Temas visuales predefinidos por tipo de negocio.
Cada negocio puede usar el tema de su industria o personalizar manualmente.
"""

TEMAS = {
    "spa": {
        "label": "Spa / Wellness",
        "emoji": "💆",
        "color_primario":   "#00A86B",
        "color_secundario": "#E8F5EE",
        "color_fondo":      "#F4F1EB",
        "color_texto":      "#1A2E1A",
    },
    "barberia": {
        "label": "Barbería",
        "emoji": "✂️",
        "color_primario":   "#C0392B",
        "color_secundario": "#FADBD8",
        "color_fondo":      "#FDFEFE",
        "color_texto":      "#1A1A2E",
    },
    "medico": {
        "label": "Médico / Clínica",
        "emoji": "🏥",
        "color_primario":   "#1ABC9C",
        "color_secundario": "#D1F2EB",
        "color_fondo":      "#FDFEFE",
        "color_texto":      "#0D2137",
    },
    "odontologia": {
        "label": "Odontología",
        "emoji": "🦷",
        "color_primario":   "#2980B9",
        "color_secundario": "#D6EAF8",
        "color_fondo":      "#F7FBFF",
        "color_texto":      "#1B2631",
    },
    "taller": {
        "label": "Taller mecánico",
        "emoji": "🔧",
        "color_primario":   "#D35400",
        "color_secundario": "#FAE5D3",
        "color_fondo":      "#F8F9F9",
        "color_texto":      "#2C3E50",
    },
    "nail": {
        "label": "Uñas / Nail studio",
        "emoji": "💅",
        "color_primario":   "#8E44AD",
        "color_secundario": "#F5EEF8",
        "color_fondo":      "#FDF2F8",
        "color_texto":      "#2C1654",
    },
    "peluqueria": {
        "label": "Peluquería",
        "emoji": "💇",
        "color_primario":   "#E91E8C",
        "color_secundario": "#FCE4EC",
        "color_fondo":      "#FFF9FB",
        "color_texto":      "#1A0A10",
    },
    "fitness": {
        "label": "Fitness / Gym",
        "emoji": "💪",
        "color_primario":   "#E67E22",
        "color_secundario": "#FDEBD0",
        "color_fondo":      "#FAFAFA",
        "color_texto":      "#1C1C1C",
    },
    "veterinaria": {
        "label": "Veterinaria",
        "emoji": "🐾",
        "color_primario":   "#27AE60",
        "color_secundario": "#D5F5E3",
        "color_fondo":      "#F9FFF9",
        "color_texto":      "#0D2B1A",
    },
    "general": {
        "label": "General",
        "emoji": "🏢",
        "color_primario":   "#00A86B",
        "color_secundario": "#E8F5EE",
        "color_fondo":      "#FFFFFF",
        "color_texto":      "#111827",
    },
}


def get_tema(tipo: str) -> dict:
    """Devuelve el tema predefinido para un tipo de negocio."""
    return TEMAS.get(tipo, TEMAS["general"])


def get_tema_negocio(negocio) -> dict:
    """
    Construye el objeto tema para un negocio.
    Si tiene colores personalizados los usa, si no usa el predefinido.
    """
    predefinido = get_tema(negocio.tipo_negocio or "general")
    return {
        "tipo":             negocio.tipo_negocio or "general",
        "label":            predefinido["label"],
        "emoji":            predefinido["emoji"],
        "color_primario":   negocio.color_primario   or predefinido["color_primario"],
        "color_secundario": negocio.color_secundario or predefinido["color_secundario"],
        "color_fondo":      negocio.color_fondo      or predefinido["color_fondo"],
        "color_texto":      negocio.color_texto      or predefinido["color_texto"],
    }
