



import requests
import time

from django.conf import settings
from deepfake_detection.models import ServiceProviderChoices, ServiceProvider, SensityTaskChoices
import requests
import requests
import time
import requests
import time
from typing import Optional, Dict, Any

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
    
# curl --request POST \
#   --url https://api.sensity.ai/tasks/face_manipulation \
#   --header 'Authorization: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJodHRwczovL2FwaS5zZW5zaXR5LmFpIiwianRpIjoiZmJiZTY0ODItMjljMC00ZDI0LWJlNzMtY2U2NDY4NGViODgxIiwiaWF0IjoxNzcwODcyNDYzLCJpc3MiOiJTZW5zaXR5Iiwic3ViIjoic2F0ZW5kcmEua0B0aW1ibGV0ZWNoLmNvbSJ9.U4ptr91yoOiYdfcbgo526df5_c00AQ3AshSRLOn7lMA' \
#   --header 'content-type: multipart/form-data' \
#   --form url=https://upload.wikimedia.org/wikipedia/commons/9/99/Black_square.jpg

# curl --request GET \
#   --url https://api.sensity.ai/tasks/face_manipulation/febbe494-bc00-461b-be87-0894981be42c \
#   --header 'Authorization: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJodHRwczovL2FwaS5zZW5zaXR5LmFpIiwianRpIjoiZmJiZTY0ODItMjljMC00ZDI0LWJlNzMtY2U2NDY4NGViODgxIiwiaWF0IjoxNzcwODcyNDYzLCJpc3MiOiJTZW5zaXR5Iiwic3ViIjoic2F0ZW5kcmEua0B0aW1ibGV0ZWNoLmNvbSJ9.U4ptr91yoOiYdfcbgo526df5_c00AQ3AshSRLOn7lMA'

# Use hyphen endpoints as per Sensity docs
TASK_MAP = {
    "image": [
        "ai_generated_image_detection",
        "forensic_analysis",
        'face_manipulation',
    ],
    "video": [
        "face_manipulation",
        "ai_generated_image_detection",
        "forensic_analysis",
    ],
    "audio": [
        "voice_analysis",
    ],
}


class SensityClient(ProviderClient):
 
    def __init__(self, token: str):
        super().__init__(token)

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        })

   
    def create_tasks(
        self,
        media_file=None,
        media_url: Optional[str] = None,
        **kwargs
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

        for task_name in tasks:
            try:

                if media_url:
                    # multipart with URL
                    files = {"url": (None, media_url)}

                else:
                    # Important: reset pointer if reused
                    media_file.seek(0)

                    files = {
                        "file": (
                            media_file.name,
                            media_file,
                            media_file.content_type
                        )
                    }

                print(
                    f"Calling Sensity API: {BASE_URL}/{task_name}"
                )

                response = self.session.post(
                    f"{BASE_URL}/{task_name}",
                    files=files,
                    timeout=60,
                )

                print("Status:", response.status_code)
                print("Response:", response.text)

                response.raise_for_status()

                body = response.json()

                report_ids[task_name] = (
                    body.get("task_id")
                    or body.get("report_id")
                )

            except requests.exceptions.HTTPError as e:
                report_ids[task_name] = {
                    "error": f"{e.response.status_code} - {e.response.text}"
                }
            except Exception as e:
                report_ids[task_name] = {"error": str(e)}

        return report_ids

    def get_results(self, report_ids: dict) -> Dict[str, Any]:
        """
        Fetch results for created tasks
        """
        print('started get_results of sensity...')
        results = {}

        for task_name, report_id in report_ids.items():

            if isinstance(report_id, dict):
                results[task_name] = report_id
                continue

            try:
                print(f" actual sensity result api call : url : {BASE_URL}/{task_name}/{report_id} GET")
                response = self.session.get(
                    f"{BASE_URL}/{task_name}/{report_id}",
                    timeout=30,
                )

                
                response.raise_for_status()
                results[task_name] = response.json()
                print(f"complete actual sensity result api call: response: {response.json()}")


            except requests.exceptions.HTTPError as e:
                results[task_name] = {
                    "error": f"{e.response.status_code} - {e.response.text}"
                }
            except Exception as e:
                results[task_name] = {"error": str(e)}
        print('completed get_results of sensity...')
        return results


    def _resolve_media_url(self, media_file, media_url: Optional[str]) -> Optional[str]:
        
        if media_url:
            return media_url

        if media_file:
            return media_file

        return None


ClientClassMap = {
    "SENSITY": SensityClient,
}