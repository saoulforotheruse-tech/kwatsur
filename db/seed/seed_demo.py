"""Insère des annonces FICTIVES pour démontrer la recherche (aucune annonce réelle).

Aucune coordonnée ni lien n'est inventé : ces champs restent vides.
Certaines informations sont volontairement inconnues pour montrer leur traitement.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.property import Property, PropertySource

DEMO_SOURCE_NAME = "Données fictives Kwatsur"
DEMO_DESCRIPTION_PREFIX = "[DÉMO — annonce fictive] "

# (référence, titre, ville, quartier, type, loyer, chambres, sdb, meublé, eau, électricité,
#  jours depuis la dernière observation, description)
DEMO_LISTINGS = (
    ("dla-bonamoussadi-01", "Appartement 2 chambres à Bonamoussadi", "Douala", "Bonamoussadi",
     "appartement", 120000, 2, 1, False, True, True, 3,
     "Appartement au premier étage, à deux minutes d'un arrêt de taxis et de moto-taxis. Compteur ENEO individuel."),
    ("dla-bonamoussadi-02", "Appartement lumineux proche carrefour Bonamoussadi", "Douala", "Bonamoussadi",
     "appartement", 145000, 2, 2, False, True, None, 10,
     "Grand salon, cuisine équipée, quartier animé proche des transports et du marché."),
    ("dla-bonamoussadi-03", "Appartement 3 chambres avec parking", "Douala", "Bonamoussadi",
     "appartement", 180000, 3, 2, False, True, True, 5,
     "Résidence calme avec parking et gardien de nuit."),
    ("dla-makepe-01", "Appartement 2 chambres à Makepe", "Douala", "Makepe",
     "appartement", 110000, 2, 1, False, None, True, 20,
     "Proche de la route principale et des transports en commun."),
    ("dla-kotto-01", "Appartement 2 chambres à Kotto", "Douala", "Kotto",
     "appartement", 100000, 2, 1, False, True, True, 45,
     "Immeuble récent, forage dans la cour."),
    ("dla-logpom-01", "Appartement 2 chambres à Logpom", "Douala", "Logpom",
     "appartement", 95000, 2, 1, None, True, True, 8,
     "Quartier résidentiel, rue bitumée."),
    ("dla-akwa-01", "Appartement 2 chambres à Akwa", "Douala", "Akwa",
     "appartement", 40000, 2, None, None, None, None, None,
     "Loyer très bas, paiement de six mois d'avance demandé."),
    ("dla-bonapriso-01", "Studio meublé à Bonapriso", "Douala", "Bonapriso",
     "studio", 150000, 0, 1, True, True, None, 2,
     "Studio meublé, climatisé, dans une rue calme."),
    ("dla-bonaberi-01", "Chambre moderne à Bonabéri", "Douala", "Bonabéri",
     "chambre", 35000, 1, 1, False, True, True, 12,
     "Chambre avec douche interne, proche du pont du Wouri."),
    ("dla-denver-01", "Maison 3 chambres à Denver", "Douala", "Denver",
     "maison", 250000, 3, 2, False, True, True, 30,
     "Maison avec cour et parking, quartier calme."),
    ("dla-pk14-01", "Appartement 2 chambres à PK14", "Douala", "PK14",
     "appartement", 70000, 2, 1, False, None, None, 90,
     None),
    ("yde-melen-01", "Studio à Melen", "Yaoundé", "Melen",
     "studio", 60000, 0, 1, False, True, True, 6,
     "Studio proche de l'université et des transports."),
    ("yde-ngoa-ekelle-01", "Studio meublé à Ngoa-Ekellé", "Yaoundé", "Ngoa-Ekellé",
     "studio", 85000, 0, 1, True, True, True, 15,
     "Studio meublé pour étudiant, connexion internet possible."),
    ("yde-bastos-01", "Appartement 3 chambres à Bastos", "Yaoundé", "Bastos",
     "appartement", 350000, 3, 3, True, True, True, 4,
     "Appartement haut standing, gardiennage permanent."),
    ("yde-mvan-01", "Appartement 2 chambres à Mvan", "Yaoundé", "Mvan",
     "appartement", 90000, 2, 1, False, True, None, 25,
     "Proche de l'axe lourd et de la gare routière."),
    ("yde-biyem-assi-01", "Appartement 2 chambres à Biyem-Assi", "Yaoundé", "Biyem-Assi",
     "appartement", 120000, 2, 2, False, True, True, 9,
     "Quartier calme, eau courante et forage de secours."),
    ("yde-odza-01", "Maison 4 chambres à Odza", "Yaoundé", "Odza",
     "maison", 200000, 4, 2, False, None, True, 60,
     "Maison avec jardin, route en terre sur les derniers mètres."),
    ("yde-emana-01", "Chambre à Emana", "Yaoundé", "Emana",
     "chambre", 30000, 1, None, False, True, True, 18,
     "Chambre simple, douche commune."),
    ("yde-essos-01", "Appartement 1 chambre à Essos", "Yaoundé", "Essos",
     "appartement", 75000, 1, 1, None, True, True, 11,
     "Proche du marché et des transports."),
    ("yde-nkolbisson-01", "Studio à Nkolbisson", "Yaoundé", None,
     "studio", 45000, 0, None, None, None, None, None,
     None),
)


def demo_properties(source_id: int, now: datetime) -> list[Property]:
    properties = []
    for (
        reference, title, city, neighborhood, property_type, rent, bedrooms, bathrooms,
        furnished, water, electricity, seen_days_ago, description,
    ) in DEMO_LISTINGS:
        properties.append(
            Property(
                source_id=source_id,
                source_property_id=f"demo-{reference}",
                title=title,
                description=(DEMO_DESCRIPTION_PREFIX + description) if description else None,
                city=city,
                neighborhood=neighborhood,
                property_type=property_type,
                monthly_rent=rent,
                currency="XAF",
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                furnished=furnished,
                water_available=water,
                electricity_available=electricity,
                listing_status="unconfirmed",
                verification_status="unverified",
                last_seen_at=now - timedelta(days=seen_days_ago) if seen_days_ago is not None else None,
            )
        )
    return properties


def seed_demo_properties() -> int:
    """Ajoute les annonces fictives absentes ; relancer le script ne crée pas de doublons."""
    with SessionLocal.begin() as session:
        source = session.scalar(
            select(PropertySource).where(PropertySource.name == DEMO_SOURCE_NAME)
        )
        if source is None:
            source = PropertySource(name=DEMO_SOURCE_NAME, source_type="demo", is_demo=True)
            session.add(source)
            session.flush()

        existing_references = set(
            session.scalars(
                select(Property.source_property_id).where(Property.source_id == source.id)
            )
        )
        new_properties = [
            item
            for item in demo_properties(source.id, datetime.now(timezone.utc))
            if item.source_property_id not in existing_references
        ]
        session.add_all(new_properties)
        return len(new_properties)


if __name__ == "__main__":
    added = seed_demo_properties()
    print(f"{added} annonce(s) fictive(s) ajoutée(s).")
