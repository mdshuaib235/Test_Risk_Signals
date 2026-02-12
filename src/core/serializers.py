from rest_framework import serializers

from .models import Bank


class BankRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = ["name", "public_key"]
