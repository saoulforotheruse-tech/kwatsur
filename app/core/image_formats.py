"""Reconnaissance des formats d'image à partir de leurs premiers octets.

On ne fait confiance ni au nom de fichier ni au Content-Type annoncé : seule la signature
du contenu compte. Pas de dépendance externe (Pillow) pour trois formats bien connus.
"""

# Type MIME → extension de fichier utilisée par Kwatsur.
SUPPORTED_IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def detect_image_type(data: bytes) -> str | None:
    """Renvoie le type MIME réel (« image/jpeg »…) ou None si ce n'est pas une image acceptée."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
