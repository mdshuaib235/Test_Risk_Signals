from django.shortcuts import render, redirect
import uuid
import json
from rest_framework.views import APIView
from rest_framework import status
from deepfake_detection.services.sensity_client import TASK_MAP , ClientClassMap, build_public_media_url
from deepfake_detection.serializers import DeepfakeScanSerializer, DeepfakeStatusSerializer
from deepfake_detection.models import ServiceProvider, DeepfakeTask
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.urls import reverse
import requests


@method_decorator(csrf_exempt, name='dispatch')
class UploadMediaAPIViews(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        print('started post in upload api', request.data)
        serializer = DeepfakeScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        print('is_valid serializer')

        provider_name = request.data.get("provider", "SENSITY")

        provider = ServiceProvider.objects.filter(
            name=provider_name, 
            is_active=True
        ).first()
        print('stilllllllll')
        if not provider:
            return Response(
                {"error": "Provider not found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        print('worked')

        media_file = (
            request.FILES.get("media") or 
            request.FILES.get("file")
        )

        media_url = (
            request.data.get("media_url") or 
            request.data.get("url")
        )

        if not media_file and not media_url:
            print("provide media file or url")
            return Response(
                {"error": "Provide media file or URL"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if media_file and media_url:
            print('error: only file')
            return Response(
                {"error": "Provide only one: file OR URL"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        media_type = request.data.get('media_type')

        if not media_type:
            print('error: unsupported type')
            return Response(
                {"error": "Unsupported media type"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        print('will cleaned_data get')
        clean_payload = {
            "provider": provider_name,
            "media_type": media_type,
        }

        base_url , localhost = build_public_media_url(), "http://localhost"
        if media_url:
            if base_url and localhost in media_url:
                clean_payload["media_url"] = media_url.replace(localhost, base_url)
            

        if media_file:
            
            media_file_name = media_file.name
            if base_url and localhost in media_file_name:
                clean_payload["media"] = {
                    "filename": media_file_name.replace(localhost, base_url),
                    "size": media_file.size,
                    "content_type": media_file.content_type,
                }

        file_obj = media_file

        if file_obj:
            file_obj_name = file_obj.name
            if base_url and localhost in file_obj_name:
                clean_payload["media"] = {
                    "filename": file_obj_name,
                    "size": file_obj.size,
                    "content_type": file_obj.content_type,
                }

        print(f'data from views upload media api: data:{clean_payload}')

        deepfake_task = DeepfakeTask.objects.create(
            provider=provider,
            media_type=media_type,
            media_file=media_file,
            media_url=media_url,
            request_payload=dict(clean_payload),
            status="submitted"
        )
        
        # clientClass = ClientClassMap[provider_name]
        # client = clientClass(token=provider.token)
        from deepfake_detection.services.sensity_client import SensityClient
        client = SensityClient(provider.token)
        print('will client.create_tasks() from views...')
        report_ids = client.create_tasks(
            media_file=media_file,
            media_url=media_url,
            media_type=media_type
        )
        print(f'completed client.create_tasks() from views and here is report_ids:{report_ids}...')

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
    #  use consistent serializer request,response classes

    def get(self, request, task_uuid):
        try:
            task_uuid = uuid.UUID(task_uuid)
        except Exception as err:
            print('INVALID UUID format')

        print(f"started deepfake status(result) ...")
        try:
            task = DeepfakeTask.objects.get(id=task_uuid)
        except DeepfakeTask.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        


        if task.status in ["completed", "completed_with_errors"] and task.response_full:
            return Response({
                "status": task.status,
                "media_type": str(task.media_type),
                "payload": task.request_payload,
                "provider": task.provider.name,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "results": task.response_full,
                "media_url": task.media_url if task.media_url else (
                    task.media_file.url if task.media_file else None
                )
            })
        from deepfake_detection.services.sensity_client import SensityClient
        client = SensityClient(token=task.provider.token)

        results = client.get_results(task.report_ids or {})
        print('get_result success completed...')

        has_in_progress = False
        has_error = False

        for task_name, result in results.items():

            # If provider returned structured error
            if isinstance(result, dict) and "error" in result:
                has_error = True
                continue

            # Normal status check
            if isinstance(result, dict) and result.get("status") != "completed":
                has_in_progress = True

        if has_in_progress:
            overall = "in_progress"
        elif has_error:
            overall = "completed_with_errors"
        else:
            overall = "completed"

        task.response_full = results
        task.status = overall
        task.save(update_fields=["response_full", "status"])
        print('sucess of task result status api')
        return Response({
            "status": task.status,
            "media_type": str(task.media_type),
            "payload": task.request_payload,
            "provider": task.provider.name,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "results": task.response_full,
            "media_url": task.media_url if task.media_url else (
                task.media_file.url if task.media_file else None
            )
        })




class DemoUploadView(View):
    template_name = "demo/upload.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        media_file = request.FILES.get("media_file")
        media_url = request.POST.get("media_url")
        media_type = request.POST.get("media_type")

        data = {"media_type": media_type}
        files = {}

        if media_file:
            files["media"] = media_file   
        elif media_url:
            data["media_url"] = media_url
        else:
            return render(request, self.template_name, {
                "error": "Please upload file or provide URL"
            })

        
        print(build_public_media_url()+"/v1/deepfake/scan/")

        response = requests.post(
            url=build_public_media_url()+"/v1/deepfake/scan/",
            data=data,
            files=files
        )
        try:
            task_uuid = response.json().get("task_uuid")
        except Exception as err:
            print(f"{response.text}----error in json decoding----error:{err}")
        print('task_uuid----------------', task_uuid)



        return redirect(
            reverse("deepfake_result_page", args=[task_uuid])
        )
    

class DemoResultPageView(View):
    template_name = "demo/result.html"

    def get(self, request, task_uuid,  *args, **kwargs):
        from deepfake_detection.models import DeepfakeTask 

        try:
            task = DeepfakeTask.objects.get(id=task_uuid)
        except DeepfakeTask.DoesNotExist:
            return render(request, "result.html", {
                "error": "Invalid Task ID"
            })

        api_url = request.build_absolute_uri(
            reverse("deepfake_result_apiview", args=[task.id])
        )

        try:
            api_response = requests.get(api_url, timeout=10)
        except requests.RequestException:
            return render(request, self.template_name, {
                "error": "Internal API connection failed."
            })

        if api_response.status_code != 200:
            return render(request, self.template_name, {
                "error": f"API returned {api_response.status_code}"
            })

        data = api_response.json()
        formatted_json = json.dumps(data, indent=4, default=str)
        context = {
            "data": data,   
            "media_url": data.get("media_url"),
             "formatted_json": formatted_json,
        }

        return render(request, "demo/result.html", context)