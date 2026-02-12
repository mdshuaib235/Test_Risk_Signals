import hashlib
import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models

# Create your models here.
# models.py


class Bank(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    api_key = models.CharField(max_length=100, unique=True)
    public_key = models.TextField()  # RSA public key (PEM)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ID-{self.id} & name: {self.name}"


class RegisteredApp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE)

    package_name = models.CharField(max_length=255)

    # Hashed version for quick comparison
    certificate_hash_sha256 = models.CharField(max_length=64)

    # Encrypted original certificate fingerprint
    encrypted_certificate = models.BinaryField()

    created_at = models.DateTimeField(auto_now_add=True)


class UserDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    bank = models.ForeignKey(Bank, on_delete=models.CASCADE)
    bank_user_id = models.CharField(max_length=255)

    device_fingerprint_hash = models.CharField(max_length=64)
    sim_iccid_hash = models.CharField(max_length=64)

    hardware_public_key = models.TextField()  # From Android Keystore
    hardware_key_id = models.CharField(max_length=255)

    package_name = models.CharField(max_length=255)
    certificate_hash_sha256 = models.CharField(max_length=64)

    play_integrity_verdict = models.CharField(max_length=100)

    status = models.CharField(max_length=20, default="ACTIVE")

    first_registered_at = models.DateTimeField(auto_now_add=True)
    last_validated_at = models.DateTimeField(null=True, blank=True)


# (Anti-Replay)
class RequestNonce(models.Model):
    nonce = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AuthLog(models.Model):
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE)
    bank_user_id = models.CharField(max_length=255)

    decision = models.CharField(max_length=20)
    reason = models.TextField()

    device_hash = models.CharField(max_length=64)
    sim_hash = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)
