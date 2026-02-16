from rest_framework import serializers


class DeepfakeScanSerializer(serializers.Serializer):
    media = serializers.FileField(required=False)
    media_url = serializers.URLField(required=False)
    provider = serializers.CharField(required=False)
    media_type = serializers.CharField(required=True)
    

class DeepfakeStatusSerializer(serializers.Serializer):
    task_uuid = serializers.UUIDField()