import base64
import hashlib
from datetime import timedelta

from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from django.conf import settings
from django.utils import timezone

from .models import Bank, RequestNonce

ALLOWED_TIME_WINDOW = 30  # seconds


fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)


def encrypt_data(data: str) -> bytes:
    return fernet.encrypt(data.encode())


def decrypt_data(token: bytes) -> str:
    return fernet.decrypt(token).decode()


def verify_signature(public_key_pem, payload, signature_base64):
    public_key = serialization.load_pem_public_key(public_key_pem.encode())

    signature = base64.b64decode(signature_base64)

    try:
        print("verifying payload with signature with from public-key...")
        public_key.verify(
            signature, payload.encode(), padding.PKCS1v15(), hashes.SHA256()
        )
        print("verified successfully payload with signature...")
        return True
    except Exception as err:
        print(f"Exception in verify_signature: error:{err} ")
        return False


def verify_request(request):
    print(
        f"Started verify_request with request.data={request.data} & request.headers={request.headers}..."
    )
    api_key = request.headers.get("X-API-KEY")
    signature = request.headers.get("X-SIGNATURE")
    timestamp = request.headers.get("X-TIMESTAMP")
    nonce = request.headers.get("X-NONCE")

    if not all([api_key, signature, timestamp, nonce]):
        return None, "Missing security headers"

    try:
        bank = Bank.objects.get(api_key=api_key, is_active=True)
    except Bank.DoesNotExist:
        return None, "Invalid API Key"

    # Timestamp validation
    request_time = timezone.datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    if timezone.now() - request_time > timedelta(seconds=ALLOWED_TIME_WINDOW):
        return None, "Request expired"

    # Nonce replay protection
    if RequestNonce.objects.filter(nonce=nonce).exists():
        return None, "Replay attack detected"

    # Verify RSA Signature
    message = request.body + timestamp.encode() + nonce.encode()
    public_key = load_pem_public_key(bank.public_key.encode())

    try:
        public_key.verify(
            base64.b64decode(signature), message, padding.PKCS1v15(), hashes.SHA256()
        )
    except InvalidSignature:
        return None, "Invalid signature"

    # Save nonce
    obj = RequestNonce.objects.create(nonce=nonce)
    print(
        f"Completed verify_request with requestNonceId:{obj.id} and nonce:{nonce} ..."
    )

    return bank, None


import requests
from django.conf import settings

GOOGLE_PLAY_URL = (
    "https://playintegrity.googleapis.com/v1/{package_name}:decodeIntegrityToken"
)


def verify_play_integrity(token, package_name):
    url = GOOGLE_PLAY_URL.format(package_name=package_name)
    #  TODO: add this in settings after deploy 'GOOGLE_SERVICE_ACCOUNT_ACCESS_TOKEN'
    #   1. A Google Cloud project linked to your app
    #   2. Play Integrity API enabled
    #   3. A valid GCP service account credential that your backend can use to get an access token
    if not getattr(settings, "GOOGLE_SERVICE_ACCOUNT_ACCESS_TOKEN"):
        return "GOOGLE_SERVICE_ACCOUNT_ACCESS_TOKEN is required", False
    headers = {
        "Authorization": f"Bearer {settings.GOOGLE_SERVICE_ACCOUNT_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        url, json={"integrityToken": token}, headers=headers, timeout=10
    )

    if response.status_code != 200:
        return "Google verification failed", None

    return response.json(), None
