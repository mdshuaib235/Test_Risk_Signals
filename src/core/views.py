import hashlib
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
import re

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.basic_crypto import encrypt_data, verify_request, verify_signature, verify_play_integrity
from .models import AuthLog, Bank, RegisteredApp, UserDevice
from .serializers import BankRegistrationSerializer


class TestAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class BankRegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    # TODO: add auth,permission classes for verification
    def post(self, request):
        print(
            f"Started BankRegisterView data={request.data} & headers:{request.headers}..."
        )
        name = request.data.get("name")
        api_key = request.data.get("api_key")
        public_key = request.data.get("public_key")

        bank = Bank.objects.create(name=name, api_key=api_key, public_key=public_key)

        return Response({"bank_id": str(bank.id)})





class AppRegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        print(f"[AppRegister] data={request.data}")

        bank, error = verify_request(request)
        if error:
            return Response({"error": error}, status=403)

        package_name = request.data.get("package_name")
        certificate_hash = request.data.get("certificate_hash_sha256")

        if not package_name or not certificate_hash:
            return Response(
                {"error": "package_name and certificate_hash_sha256 required"},
                status=400
            )

        # Validate SHA256 format (64 hex chars)
        if not re.fullmatch(r"[a-fA-F0-9]{64}", certificate_hash):
            return Response(
                {"error": "Invalid certificate hash format"},
                status=400
            )

        # Prevent duplicate app registration
        if RegisteredApp.objects.filter(
            bank=bank,
            package_name=package_name,
            certificate_hash_sha256=certificate_hash
        ).exists():
            return Response(
                {"error": "App already registered"},
                status=400
            )

        with transaction.atomic():
            RegisteredApp.objects.create(
                bank=bank,
                package_name=package_name,
                certificate_hash_sha256=certificate_hash,
                encrypted_certificate=b""  # Optional future encryption
            )

        return Response({"message": "App registered successfully"})
    


class DeviceRegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        print(f"[DeviceRegister] data={request.data}")

        bank, error = verify_request(request)
        if error:
            return Response({"error": error}, status=403)

        data = request.data

        required_fields = [
            "bank_user_id",
            "device_fingerprint_hash",
            "sim_iccid_hash",
            "hardware_public_key",
            "hardware_key_id",
            "package_name",
            "certificate_hash_sha256",
            "play_integrity_token",
        ]

        for field in required_fields:
            if not data.get(field):
                return Response(
                    {"error": f"Missing or empty field: {field}"},
                    status=400
                )

        # 🔎 Verify app registration
        app_exists = RegisteredApp.objects.filter(
            bank=bank,
            package_name=data["package_name"],
            certificate_hash_sha256=data["certificate_hash_sha256"],
        ).exists()

        if not app_exists:
            return Response(
                {"decision": "BLOCK", "reason": "Invalid or unregistered app"},
                status=403
            )

        # 🔐 Verify Play Integrity with Google
        token = data["play_integrity_token"]

        # TODO: add GOOGLE_SERVICE_ACCOUNT_ACCESS_TOKEN in settings.py
        payload, error = verify_play_integrity(
            token,
            data["package_name"]
        )

        if error:
            return Response(
                {"decision": "BLOCK", "reason": error},
                status=403
            )

        try:
            token_payload = payload["tokenPayloadExternal"]
            device_integrity = token_payload["deviceIntegrity"]
            app_integrity = token_payload["appIntegrity"]

            device_verdict = device_integrity.get(
                "deviceRecognitionVerdict", []
            )

            package_name_from_google = app_integrity.get(
                "packageName"
            )

        except KeyError:
            return Response(
                {"decision": "BLOCK", "reason": "Malformed integrity response"},
                status=403
            )

        # Verify package match
        if package_name_from_google != data["package_name"]:
            return Response(
                {"decision": "BLOCK", "reason": "Package mismatch"},
                status=403
            )

        # Verify device integrity
        if "MEETS_DEVICE_INTEGRITY" not in device_verdict:
            return Response(
                {"decision": "BLOCK", "reason": "Device integrity failed"},
                status=403
            )

        # Prevent duplicate active device
        if UserDevice.objects.filter(
            bank=bank,
            bank_user_id=data["bank_user_id"],
            status="ACTIVE"
        ).exists():
            return Response(
                {"decision": "BLOCK", "reason": "Device already registered"},
                status=400
            )

        # Atomic device creation (binding)
        # TODO: before saving SIM info, perform SNA agains SIM number
        with transaction.atomic():
            UserDevice.objects.create(
                bank=bank,
                bank_user_id=data["bank_user_id"],
                device_fingerprint_hash=data["device_fingerprint_hash"],
                sim_iccid_hash=data["sim_iccid_hash"],
                hardware_public_key=data["hardware_public_key"],
                hardware_key_id=data["hardware_key_id"],
                package_name=data["package_name"],
                certificate_hash_sha256=data["certificate_hash_sha256"],
                play_integrity_verdict=",".join(device_verdict),
                last_validated_at=timezone.now(),
                status="ACTIVE"
            )

        return Response({"decision": "ALLOW"})


class DeviceValidateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        bank, error = verify_request(request)
        if error:
            return Response({"error": error}, status=403)

        data = request.data

        # Basic existence check
        try:
            device = UserDevice.objects.get(
                bank=bank, bank_user_id=data["bank_user_id"], status="ACTIVE"
            )
        except UserDevice.DoesNotExist:
            return Response({
                "decision": "BLOCK",
                "reason": "Device not registered",
                "risk_score": 100,
                "risk_flags": ["DEVICE_NOT_REGISTERED"]
            })

        # Risk signals
        risk_score = 0
        risk_flags = []

        # Check device fingerprint
        if device.device_fingerprint_hash != data["device_fingerprint_hash"]:
            risk_score += 50
            risk_flags.append("DEVICE_MISMATCH")

        # IF SIM has changed can perform SNA (better to give seperate options to banks for on-demand SNA (just verifying number is active in this device))
        if device.sim_iccid_hash != data["sim_iccid_hash"]:
            risk_score += 40
            risk_flags.append("SIM_CHANGED")

        # App integrity
        if device.certificate_hash_sha256 != data["certificate_hash_sha256"]:
            risk_score += 30
            risk_flags.append("APP_INTEGRITY_FAIL")

        # Hardware key
        if device.hardware_public_key != data["hardware_public_key"]:
            risk_score += 20
            risk_flags.append("HARDWARE_KEY_MISMATCH")

        # Additional signals (play integrity, OS version drift)
        if "play_integrity_token" in data:
            if not verify_play_integrity( data['play_integrity_token'], device.package_name):
                risk_score += 20
                risk_flags.append("PLAY_INTEGRITY_FAIL")

        # Decide recommendation
        recommendation = "ALLOW"
        if risk_score >= 70:
            recommendation = "BLOCK"
        elif risk_score >= 30:
            recommendation = "CHALLENGE"

        # Log decision
        AuthLog.objects.create(
            bank=bank,
            bank_user_id=data["bank_user_id"],
            decision=recommendation,
            risk_score=risk_score,
            risk_flags=",".join(risk_flags),
            device_hash=data["device_fingerprint_hash"],
            sim_hash=data["sim_iccid_hash"],
        )

        # Update last validated
        device.last_validated_at = timezone.now()
        device.save()

        response = {
            "decision": recommendation,
            "risk_score": risk_score,
            "risk_flags": risk_flags,
            "reasons": {
                "sim_change_detected": "SIM_CHANGED" in risk_flags,
                "device_drift_detected": "DEVICE_MISMATCH" in risk_flags,
                "app_integrity_failed": "APP_INTEGRITY_FAIL" in risk_flags,
            }
        }

        # if sna_token:
        #     response["sna_token"] = sna_token

        return Response(response)
    



class DeviceRebindView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        print(f"[DeviceRebind] Incoming data={request.data}")

        # 🔐 1. Verify Bank Signature & Headers
        bank, error = verify_request(request)
        if error:
            return Response({"error": error}, status=403)

        data = request.data

        required_fields = [
            "bank_user_id",
            "device_fingerprint_hash",
            "sim_iccid_hash",
            "hardware_public_key",
            "hardware_key_id",
            "package_name",
            "certificate_hash_sha256",
            "play_integrity_token",
        ]

        # 2. Validate Required Fields
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {"error": f"Missing or empty field: {field}"},
                    status=400
                )

        # 3. Validate App Is Registered
        app_exists = RegisteredApp.objects.filter(
            bank=bank,
            package_name=data["package_name"],
            certificate_hash_sha256=data["certificate_hash_sha256"],
        ).exists()

        if not app_exists:
            return Response(
                {"decision": "BLOCK", "reason": "Unregistered or tampered app"},
                status=403
            )

        # 4. Verify Play Integrity With Google
        token = data["play_integrity_token"]

        payload, error = verify_play_integrity(
            token,
            data["package_name"]
        )

        if error:
            return Response(
                {"decision": "BLOCK", "reason": error},
                status=403
            )

        try:
            token_payload = payload["tokenPayloadExternal"]
            device_integrity = token_payload["deviceIntegrity"]
            app_integrity = token_payload["appIntegrity"]

            device_verdict = device_integrity.get(
                "deviceRecognitionVerdict", []
            )

            package_name_from_google = app_integrity.get(
                "packageName"
            )

        except KeyError:
            return Response(
                {"decision": "BLOCK", "reason": "Malformed integrity response"},
                status=403
            )

        # 5. Verify Google Package Name Matches
        if package_name_from_google != data["package_name"]:
            return Response(
                {"decision": "BLOCK", "reason": "Package mismatch"},
                status=403
            )

        # 6. Check Device Integrity Verdict
        if "MEETS_DEVICE_INTEGRITY" not in device_verdict:
            return Response(
                {"decision": "BLOCK", "reason": "Device integrity failed"},
                status=403
            )

        # 7. Atomic Rebind Operation
        with transaction.atomic():

            # Revoke previous active devices
            UserDevice.objects.filter(
                bank=bank,
                bank_user_id=data["bank_user_id"],
                status="ACTIVE"
            ).update(status="REVOKED")

            # Create new trusted device
            UserDevice.objects.create(
                bank=bank,
                bank_user_id=data["bank_user_id"],
                device_fingerprint_hash=data["device_fingerprint_hash"],
                sim_iccid_hash=data["sim_iccid_hash"],
                hardware_public_key=data["hardware_public_key"],
                hardware_key_id=data["hardware_key_id"],
                package_name=data["package_name"],
                certificate_hash_sha256=data["certificate_hash_sha256"],
                play_integrity_verdict=",".join(device_verdict),
                last_validated_at=timezone.now(),
                status="ACTIVE"
            )

        return Response({"decision": "ALLOW"})
    


class DeviceRevokeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        print(
            f"Started DeviceRevokeView data={request.data} & headers:{request.headers}..."
        )
        bank, error = verify_request(request)
        if error:
            return Response({"error": error}, status=403)

        bank_user_id = request.data.get("bank_user_id")

        # TODO: use select_for_update, select/prefetch_related, atomic-transactions, indexing etc
        revoked_device = UserDevice.objects.filter(bank=bank, bank_user_id=bank_user_id)
        if revoked_device:
            revoked_device.update(status="REVOKED")

        return Response({"message": "Device revoked"})
