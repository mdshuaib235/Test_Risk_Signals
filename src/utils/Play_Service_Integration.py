from datetime import datetime

import jwt
from jwt import PyJWTClient

#  fetch google pub key
integrity_token = "x"
YOUR_PRIVATE_KEY = "test"
jwk_client = PyJWKClient(
    "https://www.googleapis.com/androidcheck/v1/attestation/publicKey"
)

#  verify sign
signing_key = jwk_client.get_signing_key_from_jwt(integrity_token)
decoded = jwt.decode(
    integrity_token,
    signing_key.key,
    algorithms=["ES256"],
    options={"verify_aud": False},
)

#  read integrity check
app_verdict = decoded["appIntegrity"]["appRecognitionVerdict"]
device_verdict = decoded["deviceIntegrity"]["deviceRecognitionVerdict"]

#  apply policy and check ___
if app_verdict != "PLAY_RECOGNIZED":
    # reject()
    pass

if "MEETS_STRONG_INTEGRITY" not in device_verdict:
    # reject()
    pass


# issue our attestation server token (trusted session token)
trust_token = jwt.encode(
    payload={
        "iss": "your-company",
        "bank_id": "bank_id",
        "app_instance_id": "app_instance_id",
        "exp": datetime.now() + 120,
    },
    key=YOUR_PRIVATE_KEY,
    algorithm="RS256",
)
