"""Routes des images : génération d'illustrations IA et lecture des fichiers enregistrés."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.dependencies import ImageServiceDependency, SearchServiceDependency, enforce_chat_rate_limit
from app.schemas.image import GenerateImageRequest, ImageRead

router = APIRouter(prefix="/api/images", tags=["images"])


class ImageGenerationStatus(BaseModel):
    available: bool
    remaining_today: int


@router.get("/status", response_model=ImageGenerationStatus, summary="Génération d'images disponible ?")
def generation_status(image_service: ImageServiceDependency) -> ImageGenerationStatus:
    return ImageGenerationStatus(
        available=image_service.generation_available,
        remaining_today=image_service.remaining_generations_today(),
    )


@router.post(
    "/generate",
    response_model=ImageRead,
    dependencies=[Depends(enforce_chat_rate_limit)],
    summary="Générer une image illustrative (jamais présentée comme une photo réelle)",
)
def generate_image(
    request: GenerateImageRequest,
    image_service: ImageServiceDependency,
    search_service: SearchServiceDependency,
) -> ImageRead:
    listing = None
    if request.property_id is not None:
        listing = search_service.get_property(request.property_id)
        if listing is None:
            raise HTTPException(status_code=404, detail="Logement introuvable.")
    return image_service.generate_illustration(request.description, request.room, listing)


@router.get("/{image_id}", summary="Fichier d'une image enregistrée")
def read_image(image_id: int, image_service: ImageServiceDependency) -> FileResponse:
    stored = image_service.file_for(image_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Image introuvable.")
    path, content_type = stored
    return FileResponse(path, media_type=content_type, headers={"Cache-Control": "private, max-age=86400"})
