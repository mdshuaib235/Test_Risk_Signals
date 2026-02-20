from django.conf import settings
import requests


def build_public_media_url():
    if settings.DEBUG:
        # ngrok should be running manually for testing
        try:
            tunnels = requests.get(
                "http://127.0.0.1:4040/api/tunnels", timeout=10
            ).json()
            return tunnels["tunnels"][0]["public_url"]
        except Exception:
            return None
    else:
        #  return hosted/deployed domain after deployments
        return None
    