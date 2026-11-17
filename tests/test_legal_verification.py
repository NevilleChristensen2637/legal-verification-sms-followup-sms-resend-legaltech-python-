from datetime import date

from src.legal_verification import MatterIntake, SignedDocument, resend_stuck_verification


class FakeSms:
    def resend(self, message_id, request_id):
        assert request_id == "matter-1:msg-1:resend"
        return {"message_id": message_id}

    def events(self, message_id):
        return type("Events", (), {"events": [{"status": "queued"}]})()


class FakeInfrai:
    def __init__(self):
        self.sms = FakeSms()


class FakeClient:
    def __init__(self):
        self.infrai = FakeInfrai()


def test_queued_delivery_requires_deadline_follow_up():
    result = resend_stuck_verification(
        FakeClient(),
        MatterIntake("matter-1", "Ava", "+15550101010", date(2026, 11, 14)),
        SignedDocument("doc-1", "Ava", True),
        "msg-1",
    )
    assert result.delivery["status"] == "queued"
    assert result.follow_up_required is True

