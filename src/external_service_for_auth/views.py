import base64
import json
import os
import uuid

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from vonage import Auth, NetworkSimSwap, Vonage
from vonage_http_client import HttpClient
from vonage_network_auth import NetworkAuth
from vonage_network_sim_swap import SwapStatus
from vonage_network_sim_swap.requests import SimSwapCheckRequest
from django.utils import timezone
from .utils import (
    call_sim_swap_check_frm_gsma,
    call_sim_swap_date_from_gsma,
    check_sim_swap_from_vonage,
    get_access_token_from_idlayr,
)
from .models import SNARequest
from utils.commons import build_public_media_url


# TODO: convert GET api to POST
class TestNumberInsights(APIView):

    def get(self, request, phone_number: str, *args, **kwargs):

        url = "https://api.nexmo.com/ni/advanced/json"

        params = {
            "api_key": os.getenv("VONAGE_API_KEY"),
            "api_secret": os.getenv("VONAGE_API_SECRET"),
            "number": phone_number,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            return Response(
                {"error": "Failed to fetch data from Vonage", "details": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            data = response.json()
        except Exception as e:
            return Response(
                {
                    "error": "Failed to parse JSON from Vonage",
                    "raw": response.text,
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(data, status=status.HTTP_200_OK)

        #  Advanced API (need organization onboarding on vonage like APPLICATION_ID, PRIVATE-KEY (.pem))
        # auth = Auth(
        #     api_key=os.getenv("VONAGE_API_KEY"),
        #     api_secret=os.getenv("VONAGE_API_SECRET")
        # )
        # client = Vonage(auth=auth)
        # sim_swap = NetworkSimSwap(client)
        # response = sim_swap.check(
        #     phone_number="919818425790",
        #     max_age=240  # minutes (example: check SIM change within last 4 hours)
        # )
        # print(response)


class VerifyStartAPIView(APIView):
    def get(self, request, number: str):

        response = requests.post(
            "https://api.nexmo.com/verify/json",
            data={
                "api_key": os.getenv("VONAGE_API_KEY"),
                "api_secret": os.getenv("VONAGE_API_SECRET"),
                "number": number,
                "brand": "YourBankApp",
            },
            timeout=10,
        )

        return Response(response.json())


class VerifyCheckAPIView(APIView):
    def get(self, request, number, code, request_id):

        response = requests.post(
            "https://api.nexmo.com/verify/check/json",
            data={
                "api_key": os.getenv("VONAGE_API_KEY"),
                "api_secret": os.getenv("VONAGE_API_SECRET"),
                "request_id": request_id,
                "code": code,
            },
            timeout=10,
        )
        return Response(response.json())


class NetworkSimSwapAPIView(APIView):
    def get(self, request, phone):
        try:
            # NOTE: will work after organization onboarding on vonage for key and application-id (network-auth)
            # Create HTTP client (will handle OAuth token internally)
            http_client = HttpClient(
                api_key=os.getenv("VONAGE_API_KEY"),
                api_secret=os.getenv("VONAGE_API_SECRET"),
            )

            network_auth = NetworkAuth(http_client)
            sim_swap_api = NetworkSimSwap(http_client)

            request_model = SimSwapCheckRequest(phone_number=phone, max_age=240)

            swap_status: SwapStatus = sim_swap_api.check(request_model)

            return Response(
                {
                    "swapped": swap_status.swapped,
                    "last_swap_date": getattr(swap_status, "last_swap_date", None),
                }
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)


def SimSwapOpenGSMASandboxs(request):
    result_check = None
    result_date = None
    # NOTE: facing internal server error from open-GSMA
    # REFRESH PERIODICALLY before testing (background-job)
    # After changing os var related to GSMA restart server
    if request.method == "POST":
        phone = request.POST.get("phone")
        max_age = int(request.POST.get("max_age", 120))

        result_check = call_sim_swap_check_frm_gsma(phone, max_age)
        result_date = call_sim_swap_date_from_gsma(phone)

    print(
        f"success of sim-swap (open-gsma sandbox) view completed result_date={result_date} AND result_date={result_date} ..."
    )
    return render(
        request,
        "sim_swap.html",
        {"result_check": result_check, "result_date": result_date},
    )


class VonageSimSwap(APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.GET.get("phone_number")
        json_response = check_sim_swap_from_vonage(phone_number)
        print("completed check_sim_swap_from_vonage function: response:", json_response)
        return Response({"status": "success", "data": json_response}, status=200)


def SimInsightDemo(request):
    number = request.GET.get("number", "919818425790")

    api_url = f"http://localhost:8000/v1/sim-number/insights/{number}/"

    try:
        response = requests.get(api_url, timeout=5)
        data = response.json()
    except Exception as e:
        data = {"status_message": "Error", "error": str(e)}

    return render(request, "sim_insight_demo.html", {"data": data, "number": number})


#  IDlayr integration
CLIENT_ID = os.getenv("IDLAYR_CLIENT_ID")
CLIENT_SECRET = os.getenv("IDLAYR_CLIENT_SECRET")
DATA_RESIDENCY = os.getenv("IDLAYR_DATA_RESIDENCY").lower()


# If IDlayr sends asynchronous callbacks
@csrf_exempt
def idlayr_callback(request):
    # IDlayr sends POST here when status COMPLETED/ERROR/EXPIRED
    try:
        payload = request.body.decode()
        print("IDlayr callback:", payload)
    except Exception as e:
        print("Callback parse error:", str(e))
    print("running idlayr_callback views success...")
    return JsonResponse({"status": "ok"})


def idlayr_redirect(request):
    print("running idlayr_redirect views success...")
    return HttpResponse("Thank you! You may return to the app now.")



@csrf_exempt
def reachability_test(request):
    print("running reachbility views start ", request.POST)
    
    phone_number = request.POST.get("phone_number")
    my_uuid = uuid.UUID(request.POST.get("uuid"))
    result = False
    obj  = SNARequest.objects.filter( 
        idempotent_uuid = my_uuid
    ).first()
    if not obj:
        phone_number = phone_number,
        obj = SNARequest.objects.create( 
            result = result,
            idempotent_uuid = my_uuid
        )
        
    if not phone_number:
        return JsonResponse({"error": "phone_number is required"}, status=400)

    token = get_access_token_from_idlayr()
    api_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    reach_url = f"https://{DATA_RESIDENCY}.api.idlayr.com/coverage/v0.1/device_ip"
    check_api_resp = requests.get(
        reach_url,
        headers=api_headers,
    )
    
    check_data = None
    try:
        check_data = check_api_resp.json()
        print(f"check_api success json_data:{check_data}")
        
    except Exception as err:
        check_data = check_api_resp.text
        print('error in check api response json decoding, error', err)
        
    existing_json_data = obj.data
    
    existing_json_data['reachability_api'] = {
        'request': {
            'headers': api_headers ,
            'method':'POST',
            'url': reach_url,
            'payload':{}
        } , 
        'response' : check_data,
    }

    obj.data = existing_json_data
    obj.updated_at = timezone.now()
    
    obj.save()
    
    # NOTE: client need to load 'check_url' from response via mobile-cellular-data
    print("running reachbility views end:response.text==", check_api_resp.text)
    return JsonResponse(check_api_resp.json())


# --- Step 1: Create SubscriberCheck ---
@csrf_exempt
def create_subscriber_check(request):
    print("running create_subscriber_check views start...")
    
    phone_number = request.POST.get("phone_number")
    my_uuid = request.POST.get('uuid')
    result = False
    
    obj , created = SNARequest.objects.get_or_create( 
        idempotent_uuid = uuid.UUID(my_uuid),
        phone_number = phone_number,
        defaults={
            'result':False,
         }
    )
    if created:
        print('db obj created')
    
    if not phone_number:
        return JsonResponse({"error": "phone_number is required"}, status=400)

    token = get_access_token_from_idlayr()
    api_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    check_url = f"https://{DATA_RESIDENCY}.api.idlayr.com/subscriber_check/v0.2/checks"
    payload = {
            "phone_number": phone_number,
            "redirect_url": build_public_media_url() + "/v1/sim-number/idlayr-redirect/" ,
            # callback_url is optional if you want webhook events
        }
    check_api_resp = requests.post(
        check_url,
        headers=api_headers,
        json=payload,
    )
    
    check_data = None
    try:
        check_data = check_api_resp.json()
        print(f"check_api success json_data:{check_data}")
        
    except Exception as err:
        check_data = check_api_resp.text
        print('error in check api response json decoding, error', err)
        
    existing_json_data = obj.data
    
    existing_json_data['check_api'] = {
        'request': {
            'headers': api_headers ,
            'method':'POST',
            'url': check_url,
             'payload':payload
                } , 
        'response' : check_data,
    }
    
    try:
        links = existing_json_data['check_api']['response']['_links']
    except Exception as err:
        pass
    
    obj.data = existing_json_data
    obj.save()
    
    # NOTE: client need to load 'check_url' from response via their mobile cellular-data
    print("running create_subscriber_check views end:response.text==", check_api_resp.text)
    return JsonResponse(check_api_resp.json())


# --- Step 2: Complete SubscriberCheck ---
@csrf_exempt
def complete_subscriber_check(request):
    print("running complete_subscriber_check views started")
    idempotent_uuid = request.POST.get('uuid')
    check_id = request.POST.get("check_id")
    code = request.POST.get("code")
    
    obj = SNARequest.objects.get(
        idempotent_uuid = idempotent_uuid
    )
    if not check_id or not code or not obj:
        return JsonResponse({"error": "check_id and code are required"}, status=400)

    token = get_access_token_from_idlayr()
    api_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json-patch+json",
        }
    #  should be need to pooling here ?
    url = f"https://{DATA_RESIDENCY}.api.idlayr.com/subscriber_check/v0.2/checks/{check_id}"
    payload = [{"op": "add", "path": "/code", "value": code}]
    resp = requests.patch(
        url,
        headers=api_headers,
        json=payload,
        timeout=10
    )
    try:
        api_json_data = resp.json()
    except Exception as err:
        print('error in check verify api response json decoding=', err)
        api_json_data = resp.text
    print("running complete_subscriber_check views end")
    existing_json_data = obj.data
    existing_json_data['verify_check_api'] =  {
        'request': {
            'headers': api_headers ,
            'method':'PATCH',
            'url': url,
            'payload':payload
                } , 
        'response' : api_json_data,
    }
    if resp.status_code in [200,201,202]:
        obj.result = True
        obj.save()
        print(f'successfully completed SNA Authentication, API-Response:{resp.json()} ........ :)))')
    return JsonResponse(resp.json())
