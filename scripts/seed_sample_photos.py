"""Télécharge les photos d'exemple (Wikimedia Commons, CC BY-SA) et les rattache aux annonces de démo.

Usage (dans le conteneur API, qui a accès à Internet) :
    python -m scripts.seed_sample_photos

- liste et crédits : db/seed/sample_photos.json ;
- chaque fichier est vérifié comme vraie image (JPEG, PNG ou WebP) avant d'être enregistré ;
- idempotent : une photo déjà présente (même page source) n'est pas retéléchargée.
Ces photos ne montrent pas les annonces fictives : elles sont étiquetées « Photo d'exemple ».
"""

import json
import sys
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.image_description.base import DisabledImageDescriber
from app.integrations.image_generation.base import DisabledImageProvider
from app.models.image import PropertyImage
from app.models.property import Property
from app.repositories.image_repository import ImageRepository
from app.services.image_service import ImageService
from app.services.image_storage import LocalImageStore

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "db" / "seed" / "sample_photos.json"
# Wikimedia demande un User-Agent qui identifie l'application.
USER_AGENT = "KwatsurDemo/1.0 (hackathon housing demo; https://github.com/saoulforotheruse-tech/kwatsur)"


def download(url: str) -> bytes:
    response = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True)
    response.raise_for_status()
    return response.content


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    store = LocalImageStore(Path(settings.media_directory), settings.image_upload_max_bytes)
    added = skipped = failed = 0
    with SessionLocal() as session:
        # Aucune génération ni vision ici : seul l'enregistrement des photos est utilisé.
        images = ImageService(DisabledImageProvider(), store, ImageRepository(session), daily_limit=0,
                              describer=DisabledImageDescriber())
        for photo in manifest["photos"]:
            listing = session.scalar(select(Property).where(Property.source_property_id == photo["listing"]))
            if listing is None:
                print(f"  ignorée (annonce {photo['listing']} absente) : {photo['title']}")
                skipped += 1
                continue
            already = session.scalar(
                select(PropertyImage.id).where(
                    PropertyImage.property_id == listing.id, PropertyImage.source_url == photo["source_url"]
                )
            )
            if already:
                skipped += 1
                continue
            try:
                image = images.add_sample_photo(
                    listing.id, download(photo["download_url"]), photo["room"],
                    photo["author"], photo["license"], photo["source_url"],
                )
            except Exception as error:  # noqa: BLE001 — on continue avec les autres photos
                print(f"  ÉCHEC {photo['title']} : {error}")
                failed += 1
                continue
            print(f"  ajoutée : {photo['title']} → {listing.title} ({photo['room']}), image {image.id}")
            added += 1
    print(f"{added} ajoutée(s), {skipped} déjà présente(s) ou ignorée(s), {failed} échec(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
