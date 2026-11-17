from datetime import date
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infrai_client import InfraiClient
from src.legal_verification import MatterIntake, SignedDocument, resend_stuck_verification


message_id = os.environ.get("VERIFICATION_MESSAGE_ID")
if not message_id:
    raise SystemExit("VERIFICATION_MESSAGE_ID is required")

result = resend_stuck_verification(
    InfraiClient(),
    MatterIntake("matter-104", "Jordan Lee", "+15550101010", date(2026, 11, 14)),
    SignedDocument("engagement-104", "Jordan Lee", True),
    message_id,
)
print({"matter_id": result.matter.matter_id, "delivery": result.delivery, "follow_up_required": result.follow_up_required})
