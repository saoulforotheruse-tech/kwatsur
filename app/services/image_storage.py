"""Stockage des fichiers image sur le disque (dossier MEDIA_DIRECTORY, volume Docker).

Règles de sécurité :
- le nom de fichier est toujours généré par Kwatsur (UUID + extension du type réel) ;
- le contenu est vérifié par sa signature, jamais par le nom ou le type annoncé ;
- la lecture n'accepte qu'un nom au format généré : aucune traversée de répertoire possible.
Le stockage ignore d'où vient l'image (propriétaire ou fournisseur IA).
"""

import re
import uuid
from pathlib import Path

from app.core.exceptions import KwatsurError
from app.core.image_formats import SUPPORTED_IMAGE_TYPES, detect_image_type

STORED_NAME_PATTERN = re.compile(r"[0-9a-f]{32}\.(jpg|png|webp)")


class InvalidImageFileError(KwatsurError):
    status_code = 415
    public_message = "Le fichier envoyé n'est pas une image JPEG, PNG ou WebP valide."


class ImageTooLargeError(KwatsurError):
    status_code = 413
    public_message = "L'image dépasse la taille maximale autorisée."


class ImageStorageError(KwatsurError):
    status_code = 500
    public_message = "L'image n'a pas pu être enregistrée."


class LocalImageStore:
    def __init__(self, directory: Path, max_bytes: int) -> None:
        self.directory = directory
        self.max_bytes = max_bytes

    def save(self, image_bytes: bytes) -> tuple[str, str]:
        """Vérifie puis écrit l'image ; renvoie (nom de fichier généré, type MIME réel)."""
        if not image_bytes:
            raise InvalidImageFileError("Le fichier envoyé est vide.")
        if len(image_bytes) > self.max_bytes:
            raise ImageTooLargeError(
                f"L'image dépasse la taille maximale ({self.max_bytes // 1_000_000} Mo)."
            )
        content_type = detect_image_type(image_bytes)
        if content_type is None:
            raise InvalidImageFileError()

        file_name = f"{uuid.uuid4().hex}.{SUPPORTED_IMAGE_TYPES[content_type]}"
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            (self.directory / file_name).write_bytes(image_bytes)
        except OSError as error:
            raise ImageStorageError() from error
        return file_name, content_type

    def path_for(self, file_name: str) -> Path | None:
        """Chemin d'un fichier enregistré, ou None si le nom n'est pas un nom généré."""
        if not STORED_NAME_PATTERN.fullmatch(file_name):
            return None
        path = self.directory / file_name
        return path if path.is_file() else None

    def delete(self, file_name: str) -> None:
        path = self.path_for(file_name)
        if path is not None:
            path.unlink(missing_ok=True)
