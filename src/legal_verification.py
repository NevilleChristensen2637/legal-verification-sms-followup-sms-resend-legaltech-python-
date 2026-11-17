"""Domain workflow for a legal matter with a stuck verification message."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from .infrai_client import InfraiClient


@dataclass(frozen=True)
class MatterIntake:
    matter_id: str
    client_name: str
    phone: str
    deadline: date


@dataclass(frozen=True)
class SignedDocument:
    document_id: str
    signer: str
    delivered: bool


@dataclass(frozen=True)
class VerificationFollowUp:
    matter: MatterIntake
    document: SignedDocument
    message_id: str
    resend_result: Mapping[str, Any]
    delivery: Any
    follow_up_required: bool


def _latest_status(events: Any) -> str:
    if not isinstance(events, list) or not events:
        return "unknown"
    latest = events[-1]
    if isinstance(latest, Mapping):
        value = latest.get("status")
        return str(value).lower() if value is not None else "unknown"
    return "unknown"


def resend_stuck_verification(
    client: InfraiClient,
    matter: MatterIntake,
    document: SignedDocument,
    message_id: str,
) -> VerificationFollowUp:
    if not document.delivered:
        raise ValueError("signed document must be delivered before verification follow-up")
    request_id = f"{matter.matter_id}:{message_id}:resend"
    resend_result = client.infrai.sms.resend(message_id, request_id)
    delivery = client.infrai.sms.events(message_id)
    status = _latest_status(delivery.events)
    return VerificationFollowUp(
        matter=matter,
        document=document,
        message_id=message_id,
        resend_result=resend_result,
        delivery={"status": status, "events": delivery.events},
        follow_up_required=status not in {"delivered", "sent"},
    )

