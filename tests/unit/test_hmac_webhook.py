from opus_clone.services.hmac_webhook import sign_payload, verify_signature


def test_sign_and_verify():
    payload = b'{"job_id": "test123", "status": "completed"}'
    secret = "my-webhook-secret"

    signature = sign_payload(payload, secret)
    assert signature.startswith("sha256=")
    assert verify_signature(payload, signature, secret)


def test_verify_wrong_secret():
    payload = b'{"test": true}'
    secret = "correct-secret"
    wrong_secret = "wrong-secret"

    signature = sign_payload(payload, secret)
    assert not verify_signature(payload, signature, wrong_secret)


def test_verify_empty_signature():
    payload = b'{"test": true}'
    assert not verify_signature(payload, "", "secret")


def test_verify_tampered_payload():
    payload = b'{"job_id": "test123"}'
    secret = "secret"

    signature = sign_payload(payload, secret)
    tampered = b'{"job_id": "evil"}'
    assert not verify_signature(tampered, signature, secret)
