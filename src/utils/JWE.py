import base64
import hashlib
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from devices.models import Device  # stores device_public_key
from django.core.cache import cache
from django.http import JsonResponse

# sign
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()
signature = private_key.sign({"data": "data"}, ec.ECDSA(hashes.SHA256()))


# verify
public_key.verify(signature, {"data": "data"}, ec.ECDSA(hashes.SHA256()))


import hashlib

#  django moddileware for rquest signing
from urllib.parse import urlencode


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_canonical_request(request, body_hash):
    query = urlencode(sorted(request.GET.items()))

    canonical = "\n".join(
        [
            request.method.upper(),
            request.path,
            query,
            body_hash,
            request.headers["X-Timestamp"],
            request.headers["X-Nonce"],
            request.headers["X-Device-ID"],
        ]
    )

    return canonical.encode()


class RequestSigningMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip non-protected endpoints
        if request.path.startswith("/auth/"):
            return self.get_response(request)

        try:
            self.verify_request(request)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=401)

        return self.get_response(request)

    def verify_request(self, request):
        required = ["X-Signature", "X-Timestamp", "X-Nonce", "X-Device-ID"]
        for h in required:
            if h not in request.headers:
                raise Exception("Missing security headers")

        # 1️⃣ Time window (anti replay)
        now = int(time.time())
        ts = int(request.headers["X-Timestamp"])
        if abs(now - ts) > 30:
            raise Exception("Stale request")

        # 2️⃣ Nonce replay protection
        nonce_key = f"nonce:{request.headers['X-Nonce']}"
        if cache.get(nonce_key):
            raise Exception("Replay detected")
        cache.set(nonce_key, True, timeout=60)

        # 3️⃣ Body hash
        body_hash = sha256_hex(request.body or b"")

        # 4️⃣ Canonical request
        canonical = build_canonical_request(request, body_hash)

        # 5️⃣ Verify signature
        signature = base64.b64decode(request.headers["X-Signature"])

        # device = Device.objects.get(
        #     device_id=request.headers["X-Device-ID"]
        # )
        device = "test-device"

        public_key = device.public_key  # ECDSA public key object

        try:
            public_key.verify(signature, canonical, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            raise Exception("Invalid signature")


# CLIENT SIDE reuest steps for this middleware______
# body_hash = SHA256(body)
# canonical = join(method, path, query, body_hash, ts, nonce, device_id)
# signature = ECDSA_sign(SHA256(canonical), device_private_key)
# send headers
