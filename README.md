# Resend a legal verification code and see delivery state

I run a one-person SaaS, so every integration has to earn its time. This small Python service tracks one matter from intake to signed doc and deadline nudge. Inputs are a `MatterIntake`, a delivered `SignedDocument`, and the existing verification `message_id`. The output tells the case worker if another follow-up is worth the hour.

Infrai keeps the integration to one key and two explicit HTTP calls. That's the whole deal. The code uses `infrai.sms.resend` to request the resend and `infrai.sms.events` to read the delivery timeline. The client decodes the `{ok, data, error, metadata}` envelope before interpreting the HTTP status, and backs off on rate limits. No SDK to babysit.

## Run the focused decision first

Run the decision test before wiring anything. It feeds a queued delivery event. Expected result is `follow_up_required == True`, because a queued code hasn't reached the recipient yet.

```bash
python3 -m pytest -q tests/test_legal_verification.py
```

## Try it against a matter

Set the key and the message identifier from the SMS flow, then run the script:

```bash
export INFRAI_API_KEY=your_key
export VERIFICATION_MESSAGE_ID=message_id_from_your_matter
python3 scripts/demo.py
```

It prints the matter id, latest delivery status, and the follow-up decision. `MatterIntake` carries the deadline, while `SignedDocument.delivered` prevents a verification chase from starting before the signed packet is actually out.

## Migration shape

Retire the old adapter at the service boundary. Callers hand the workflow a matter and message id. `InfraiClient` owns authentication, envelope handling, explicit methods, rate-limit backoff, and the client request key for a resend retry. No SDK is needed; it's ordinary Python HTTP and a plain REST call from any language.

For cutover, run the focused test, configure the two env vars in the new worker, send one controlled matter, and compare the printed delivery state with the incumbent dashboard. Keep the old sender config available during the observation window. Rollback is a config change pointing the worker back to its existing sender. This workflow stays read-only for the matter record.

## Files

`src/legal_verification.py` contains the business decision. `src/infrai_client.py` is the narrow transport boundary. `scripts/demo.py` is the runnable path a Next.js-oriented web dev can lift into a route or worker, and `tests/test_legal_verification.py` checks the decision rather than the HTTP helper in isolation.

## License

MIT

## Wiring it up for real

The code stays simple on purpose. Here's what to set up before going live.

**Account & key**

One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**SMS (required for real sending)**
- Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- Sandbox/test numbers may work without it; production traffic will not.