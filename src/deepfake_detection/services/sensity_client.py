



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
        """
        Create Sensity tasks.
        Supports:
            - media_url (public URL)
            - media_file (auto-upload via uploader hook)
        """

        media_type = kwargs.get("media_type")
        report_ids = {}

        try:
            # Step 1 — ensure we have public URL
            final_url = self._resolve_media_url(media_file, media_url)

            if not final_url:
                return {
                    "error": "Public media_url is required for Sensity processing."
                }

            # Step 2 — create tasks
            for task_name in TASK_MAP.get(media_type, []):
                try:
                    payload = {"url": final_url}
                    print(f'payload:{payload}, url: {BASE_URL}/{task_name}, ')
                    response = self.session.post(
                        f"{BASE_URL}/{task_name}",
                        json=payload,
                        files={"url": (None, final_url)},
                        timeout=30,

                    )

                    response.raise_for_status()
                    body = response.json()

                    # Sensity usually returns task_id
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

        except Exception as e:
            return {"error": str(e)}

        return report_ids

    def get_results(self, report_ids: dict) -> Dict[str, Any]:
        """
        Fetch results for created tasks
        """
        results = {}

        for task_name, report_id in report_ids.items():

            if isinstance(report_id, dict):
                results[task_name] = report_id
                continue

            try:
                response = self.session.get(
                    f"{BASE_URL}/{task_name}/{report_id}",
                    timeout=30,
                )

                response.raise_for_status()
                results[task_name] = response.json()

            except requests.exceptions.HTTPError as e:
                results[task_name] = {
                    "error": f"{e.response.status_code} - {e.response.text}"
                }
            except Exception as e:
                results[task_name] = {"error": str(e)}

        return results

    def wait_for_completion(
        self,
        task_name: str,
        report_id: str,
        timeout: int = 120,
        interval: int = 5,
    ):
        """
        Poll until task completed
        """

        start_time = time.time()

        while True:
            response = self.session.get(
                f"{BASE_URL}/{task_name}/{report_id}",
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            status = data.get("status")

            if status in ["completed", "finished", "done"]:
                return data

            if status in ["failed", "error"]:
                return data

            if time.time() - start_time > timeout:
                raise TimeoutError("Sensity task did not complete in time")

            time.sleep(interval)

    # -----------------------------
    # INTERNAL HELPERS
    # -----------------------------

    def _resolve_media_url(self, media_file, media_url: Optional[str]) -> Optional[str]:
        """
        If media_url provided → use it
        If media_file provided → upload via configured uploader
        """

        # Case 1: already public URL
        if media_url:
            return media_url

        # Case 2: file upload
        if media_file:
            uploader = getattr(settings, "SENSITY_FILE_UPLOADER", None)

            if not uploader:
                raise ValueError(
                    "Media file provided but no SENSITY_FILE_UPLOADER configured."
                )

            # uploader must return public URL
            return uploader(media_file)

        return None


ClientClassMap = {
    "SENSITY": SensityClient,
}