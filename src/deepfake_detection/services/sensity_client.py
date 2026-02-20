import hashlib
import hmac
import time
from typing import Any, Dict, Optional

import requests
from deepfake_detection.models import (
    SensityTaskChoices,
    ServiceProvider,
    ServiceProviderChoices,
)
from django.conf import settings

BASE_URL = "https://api.sensity.ai/tasks"
from abc import ABC, abstractmethod


class ProviderClient(ABC):
    """
    Abstract interface for provider clients.
    """

    def __init__(self, token: str):
        self.token = token

    @abstractmethod
    def create_tasks(self, media_file=None, media_url=None, **kwargs):
        """
        Create analysis tasks. Return dict of task_name -> report_id
        """
        pass

    @abstractmethod
    def get_results(self, report_ids: dict):
        """
        Retrieve results for all tasks. Return dict of task_name -> full response JSON
        """
        pass


# Use hyphen endpoints as per Sensity docs
TASK_MAP = {
    "image": [
        "ai_generated_image_detection",
        "forensic_analysis",
        "face_manipulation",
    ],
    "video": [
        "face_manipulation",
        "ai_generated_image_detection",
        "forensic_analysis",
        "voice_analysis",
        # remove if not works
        "liveness_detection",
    ],
    "audio": [
        "voice_analysis",
        "forensic_analysis",
    ],
}
# forensic_analysis : Looks at subtle artifacts, metadata, file inconsistencies, editing signatures and more to find evidence of manipulation — even beyond visual deepfakes.


def verify_signature_sensity(request):
    if settings.DEBUG:
        return True
    received_signature = request.headers.get("X-Sensity-Signature")
    secret = settings.SENSITY_WEBHOOK_SECRET.encode()

    computed_signature = hmac.new(secret, request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received_signature, computed_signature)


class SensityClient(ProviderClient):

    def __init__(self, token: str):
        super().__init__(token)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            }
        )

    # use httpx/aiohttp instead of requests (for async requests)
    def create_tasks(
        self, media_file=None, media_url: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        print("started create_tasks of sensity...")
        media_type = kwargs.get("media_type")
        report_ids = {}

        if not media_type:
            return {"error": "media_type is required"}

        tasks = TASK_MAP.get(media_type)
        if not tasks:
            return {"error": f"No tasks configured for media_type={media_type}"}

        # Ensure only one provided
        if media_file and media_url:
            return {"error": "Provide either media_file OR media_url, not both"}

        if not media_file and not media_url:
            return {"error": "Provide media_file or media_url"}
        from utils.commons import build_public_media_url
        base_ngrok_url, localhost = build_public_media_url(), "http://127.0.0.1:8000"
        for task_name in tasks:
            try:

                if media_url:
                    if localhost in media_url and base_ngrok_url:
                        media_url = media_url.replace(localhost, base_ngrok_url)
                    files = {"url": (None, media_url)}

                else:
                    # Important: reset pointer if reused
                    media_file.seek(0)
                    media_file_name = media_file.name
                    if localhost in media_file_name and base_ngrok_url:
                        media_file_name = media_file_name.replace(
                            localhost, base_ngrok_url
                        )
                    files = {
                        "file": (media_file_name, media_file, media_file.content_type)
                    }

                print(f"Calling Sensity API: {BASE_URL}/{task_name}")

                response = self.session.post(
                    f"{BASE_URL}/{task_name}",
                    files=files,
                    timeout=60,
                )

                print("Status:", response.status_code)
                print("Response:", response.text)

                response.raise_for_status()

                body = response.json()

                report_ids[task_name] = body.get("task_id") or body.get("report_id")

            except requests.exceptions.HTTPError as e:
                report_ids[task_name] = {
                    "error": f"{e.response.status_code} - {e.response.text}"
                }
            except Exception as e:
                report_ids[task_name] = {"error": str(e)}

        return report_ids

    def get_results(self, report_ids: dict) -> Dict[str, Any]:
        #  use webhooks for result not instead of pooling
        print("started get_results of sensity...")
        results = {}

        for task_name, report_id in report_ids.items():

            if isinstance(report_id, dict):
                results[task_name] = report_id
                continue

            try:
                print(
                    f" actual sensity result api call : url : {BASE_URL}/{task_name}/{report_id} GET"
                )
                response = self.session.get(
                    f"{BASE_URL}/{task_name}/{report_id}",
                    timeout=30,
                )
                response.raise_for_status()
                results[task_name] = response.json()
                print(
                    f"complete actual sensity result api call: response: {response.json()}"
                )

            except requests.exceptions.HTTPError as e:
                results[task_name] = {
                    "error": f"{e.response.status_code} - {e.response.text}"
                }
            except Exception as e:
                results[task_name] = {"error": str(e)}
        print("completed get_results of sensity...")
        return results


import requests



ClientClassMap = {
    "SENSITY": SensityClient,
}
