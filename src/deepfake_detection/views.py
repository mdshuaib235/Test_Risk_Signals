from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework import status
from deepfake_detection.services.sensity_client import SensityClient, TASK_MAP , ClientClassMap
from deepfake_detection.utils import get_media_type
from deepfake_detection.serializers import DeepfakeScanSerializer, DeepfakeStatusSerializer
from deepfake_detection.models import ServiceProvider, DeepfakeTask
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


# @method_decorator(csrf_exempt, name='dispatch')
class UploadMediaAPIViews(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = DeepfakeScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider_name = request.data.get("provider", "SENSITY")

        provider = ServiceProvider.objects.filter(
            name=provider_name, 
            is_active=True
        ).first()

        if not provider:
            return Response(
                {"error": "Provider not found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        media_file = (
            request.FILES.get("media") or 
            request.FILES.get("file")
        )

        media_url = (
            request.data.get("media_url") or 
            request.data.get("url")
        )

        if not media_file and not media_url:
            return Response(
                {"error": "Provide media file or URL"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if media_file and media_url:
            return Response(
                {"error": "Provide only one: file OR URL"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        media_type = get_media_type(file=media_file, url=media_url)

        if not media_type:
            return Response(
                {"error": "Unsupported media type"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        clean_payload = request.data.copy()
        print('ddddddddddddddddddddddddddd')
        file_obj = media_file
        if file_obj:
            clean_payload["media"] = {
                "filename": file_obj.name,
                "size": file_obj.size,
                "content_type": file_obj.content_type,
            }

        deepfake_task = DeepfakeTask.objects.create(
            provider=provider,
            media_type=media_type,
            media_file=media_file,
            media_url=media_url,
            request_payload=dict(clean_payload),
            status="submitted"
        )

        clientClass = ClientClassMap[provider_name]
        client = clientClass(token=provider.token)

        report_ids = client.create_tasks(
            media_file=media_file,
            media_url=media_url,
            media_type=media_type
        )

        deepfake_task.report_ids = report_ids
        deepfake_task.save()

        return Response({
            "task_uuid": deepfake_task.id,
            "report_ids": report_ids
        }, status=status.HTTP_202_ACCEPTED)



@method_decorator(csrf_exempt, name='dispatch')
class DeepfakeStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, task_uuid):

        try:
            task = DeepfakeTask.objects.get(id=task_uuid)
        except DeepfakeTask.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        client = SensityClient(token=task.provider.token)

        # Fetch results for all tasks
        results = client.get_results(task.report_ids or {})

        # Decide final status
        overall = "completed"
        for r in results.values():
            if isinstance(r, dict) and r.get("status") != "completed":
                overall = "in_progress"
                break

        task.response_full = results
        task.status = overall
        task.save()

        return Response({
            "status": task.status,
            "results": results
        })