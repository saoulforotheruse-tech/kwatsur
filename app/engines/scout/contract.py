"""Contrat d'exécution signé : le seul objet qui autorise un outil de Kwatsur à agir.

Spécification : engines/scout-intent/docs/execution-contract.md (dépôt Meterless, Apache-2.0).
signature = HMAC_SHA256(secret, json_canonique(contrat_sans_signature)), durée de vie 5 minutes.
L'exécuteur (`ContractVerifier`) refuse un contrat non signé, altéré, expiré, hors périmètre
ou à risque élevé sans approbation, et journalise contract.verified / refused / expired.
"""

import hashlib
import hmac
import json
import logging
import os
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from app.core.exceptions import KwatsurError

logger = logging.getLogger("kwatsur.scout")

CONTRACT_TTL = timedelta(minutes=5)
CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


class ContractRefusedError(KwatsurError):
    status_code = 403
    public_message = "Action refusée : elle n'est pas autorisée par le contrat d'exécution."


def new_ulid(now_ms: int | None = None) -> str:
    """ULID : 48 bits d'horodatage (ms) puis 80 bits aléatoires, en base 32 de Crockford."""
    timestamp = now_ms if now_ms is not None else int(time.time() * 1000)
    value = (timestamp << 80) | int.from_bytes(os.urandom(10), "big")
    return "".join(CROCKFORD_ALPHABET[(value >> shift) & 31] for shift in range(125, -1, -5))


def canonical_json(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sign(payload: dict, secret: bytes) -> str:
    return hmac.new(secret, canonical_json(payload), hashlib.sha256).hexdigest()


def isoformat(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def issue_contract(fields: dict, secret: bytes, now: datetime, parent_id: str | None = None) -> dict:
    contract = {
        "contractId": new_ulid(int(now.timestamp() * 1000)),
        **({"parentId": parent_id} if parent_id else {}),
        **fields,
        "issuedAt": isoformat(now),
        "expiresAt": isoformat(now + CONTRACT_TTL),
        "signedBy": "scout",
    }
    contract["signature"] = sign(contract, secret)
    logger.info(
        "contract.issued contractId=%s intent=%s risk=%s profile=%s",
        contract["contractId"], fields["intent"]["primary"], fields["risk"]["level"],
        fields["modelProfile"]["model"],
    )
    return contract


class ContractVerifier:
    """Frontière d'exécution : chaque outil vérifie le contrat avant d'agir."""

    def __init__(
        self,
        secret: bytes,
        engine: str = "kwatsur-agent",
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.secret = secret
        self.engine = engine
        self.now = now

    def require(self, contract: dict | None, capability: str) -> None:
        if contract is None:
            self._refuse("unknown", "no-contract")
        contract_id = contract.get("contractId", "unknown")
        unsigned = {key: value for key, value in contract.items() if key != "signature"}
        signature = contract.get("signature", "")
        if contract.get("signedBy") != "scout" or not hmac.compare_digest(sign(unsigned, self.secret), signature):
            self._refuse(contract_id, "bad-signature")
        if self.now() >= datetime.fromisoformat(contract["expiresAt"].replace("Z", "+00:00")):
            logger.warning("contract.expired contractId=%s engine=%s", contract_id, self.engine)
            raise ContractRefusedError("Action refusée : le contrat d'exécution a expiré.")
        if capability not in contract["scope"]["capabilities"]:
            self._refuse(contract_id, "scope-mismatch")
        if contract["risk"]["level"] == "high" and not contract["risk"]["approvals"]:
            self._refuse(contract_id, "approval-missing")
        logger.info(
            "contract.verified contractId=%s engine=%s capability=%s", contract_id, self.engine, capability
        )

    def _refuse(self, contract_id: str, reason: str) -> None:
        logger.warning("contract.refused contractId=%s engine=%s reason=%s", contract_id, self.engine, reason)
        raise ContractRefusedError()
