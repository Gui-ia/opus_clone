import hashlib
import hmac


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def verify_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header:
        return False
    expected = sign_payload(payload_bytes, secret)
    return hmac.compare_digest(expected, signature_header)
