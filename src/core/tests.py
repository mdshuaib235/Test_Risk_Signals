from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Bank, RegisteredApp, UserDevice


class SecurityFlowTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.bank = Bank.objects.create(
            name="Test Bank",
            api_key="test-api-key",
            public_key="dummy-public-key",
            is_active=True,
        )

        self.headers = {"HTTP_X_API_KEY": self.bank.api_key}

        self.app_payload = {
            "package_name": "com.test.bank",
            "certificate_hash_sha256": "abc123",
        }

        self.device_payload = {
            "bank_user_id": "user123",
            "device_fingerprint_hash": "devicehash123",
            "sim_iccid_hash": "simhash123",
            "hardware_public_key": "hw-public-key",
            "hardware_key_id": "hw-key-id",
            "package_name": "com.test.bank",
            "certificate_hash_sha256": "abc123",
            "play_integrity_token": "fake-jwt-token",
        }

    # ---------------------------------------------------
    # 1️⃣ BANK REGISTER (No security needed)
    # ---------------------------------------------------
    def test_bank_register(self):
        response = self.client.post(
            "/v1/bank/register/",
            {"name": "Another Bank", "api_key": "new-key", "public_key": "pem-key"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    # ---------------------------------------------------
    # 2️⃣ APP REGISTER
    # ---------------------------------------------------
    @patch("core.views.verify_request")
    def test_app_register(self, mock_verify):
        mock_verify.return_value = (self.bank, None)

        response = self.client.post(
            "/v1/app/register/", self.app_payload, format="json", **self.headers
        )

        self.assertEqual(response.status_code, 201)

    # ---------------------------------------------------
    # 3️⃣ DEVICE REGISTER
    # ---------------------------------------------------
    @patch("core.views.verify_request")
    @patch("core.views.verify_play_integrity")
    def test_device_register_success(self, mock_integrity, mock_verify):

        mock_verify.return_value = (self.bank, None)

        mock_integrity.return_value = (
            {
                "tokenPayloadExternal": {
                    "deviceIntegrity": {
                        "deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY"]
                    }
                }
            },
            None,
        )

        RegisteredApp.objects.create(
            bank=self.bank,
            package_name="com.test.bank",
            certificate_hash_sha256="abc123",
            encrypted_certificate=b"",
        )

        response = self.client.post(
            "/v1/device/register/", self.device_payload, format="json", **self.headers
        )

        self.assertEqual(response.status_code, 200)

    # ---------------------------------------------------
    # 4️⃣ DEVICE VALIDATE
    # ---------------------------------------------------
    @patch("core.views.verify_request")
    def test_device_validate_success(self, mock_verify):

        mock_verify.return_value = (self.bank, None)

        UserDevice.objects.create(
            bank=self.bank,
            bank_user_id="user123",
            device_fingerprint_hash="devicehash123",
            sim_iccid_hash="simhash123",
            hardware_public_key="hw",
            hardware_key_id="hwid",
            package_name="com.test.bank",
            certificate_hash_sha256="abc123",
            play_integrity_verdict="MEETS_DEVICE_INTEGRITY",
            last_validated_at=timezone.now(),
        )

        response = self.client.post(
            "/v1/device/validate/risk/",
            {
                "bank_user_id": "user123",
                "device_fingerprint_hash": "devicehash123",
                "sim_iccid_hash": "simhash123",
                "certificate_hash_sha256": "abc123",
                "hardware_public_key": "hw-public-key",
            },
            format="json",
            **self.headers
        )

        self.assertEqual(response.status_code, 200)

    # ---------------------------------------------------
    # 5️⃣ DEVICE REBIND
    # ---------------------------------------------------
    @patch("core.views.verify_request")
    @patch("core.views.verify_play_integrity")
    def test_device_rebind(self, mock_integrity, mock_verify):

        mock_verify.return_value = (self.bank, None)

        mock_integrity.return_value = (
            {
                "tokenPayloadExternal": {
                    "deviceIntegrity": {
                        "deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY"]
                    }
                }
            },
            None,
        )

        UserDevice.objects.create(
            bank=self.bank,
            bank_user_id="user123",
            device_fingerprint_hash="oldhash",
            sim_iccid_hash="oldsim",
            hardware_public_key="hw",
            hardware_key_id="hwid",
            package_name="com.test.bank",
            certificate_hash_sha256="abc123",
            play_integrity_verdict="MEETS_DEVICE_INTEGRITY",
        )

        response = self.client.post(
            "/v1/device/rebind/", self.device_payload, format="json", **self.headers
        )

        self.assertEqual(response.status_code, 200)

    # ---------------------------------------------------
    # 6️⃣ DEVICE REVOKE
    # ---------------------------------------------------
    @patch("core.views.verify_request")
    def test_device_revoke(self, mock_verify):

        mock_verify.return_value = (self.bank, None)

        device = UserDevice.objects.create(
            bank=self.bank,
            bank_user_id="user123",
            device_fingerprint_hash="devicehash123",
            sim_iccid_hash="simhash123",
            hardware_public_key="hw",
            hardware_key_id="hwid",
            package_name="com.test.bank",
            certificate_hash_sha256="abc123",
            play_integrity_verdict="MEETS_DEVICE_INTEGRITY",
            status="ACTIVE",
        )

        response = self.client.post(
            "/v1/device/revoke/",
            {"bank_user_id": "user123"},
            format="json",
            **self.headers
        )

        device.refresh_from_db()
        self.assertEqual(device.status, "REVOKED")
        self.assertEqual(response.status_code, 200)
