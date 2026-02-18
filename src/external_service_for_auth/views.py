import json
import os
import uuid

import requests
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from vonage import Auth, NetworkSimSwap, Vonage
from vonage_network_sim_swap import SwapStatus
from vonage_network_sim_swap.requests import SimSwapCheckRequest
from vonage_network_auth import NetworkAuth
from vonage_http_client import HttpClient
from django.conf import settings
from .utils import call_sim_swap_check_frm_gsma, call_sim_swap_date_from_gsma, check_sim_swap_from_vonage

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
            timeout=10
        )
        return Response(response.json())




class NetworkSimSwapAPIView(APIView):
    def get(self, request, phone):
        try:
            # NOTE: will work after organization onboarding on vonage for key and application-id (network-auth)
            # Create HTTP client (will handle OAuth token internally)
            http_client = HttpClient(
                api_key=os.getenv('VONAGE_API_KEY'),
                api_secret=os.getenv('VONAGE_API_SECRET'),
            )

            network_auth = NetworkAuth(http_client)
            sim_swap_api = NetworkSimSwap(http_client)

            request_model = SimSwapCheckRequest(
                phone_number=phone,
                max_age=240
            )

            swap_status: SwapStatus = sim_swap_api.check(request_model)

            return Response({
                "swapped": swap_status.swapped,
                "last_swap_date": getattr(swap_status, "last_swap_date", None)
            })

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
        
    print(f'success of sim-swap (open-gsma sandbox) view completed result_date={result_date} AND result_date={result_date} ...')
    return render(request, "sim_swap.html", {
        "result_check": result_check,
        "result_date": result_date
    })
    
    

class VonageSimSwap(APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.GET.get("phone_number")
        json_response = check_sim_swap_from_vonage(phone_number)
        print('completed check_sim_swap_from_vonage function: response:', json_response)
        return Response({"status":"success", "data": json_response}, status=200)
    
    
    
def SimInsightDemo(request):
    number = request.GET.get("number", "919818425790")

    api_url = f"http://localhost:8000/v1/sim-number/insights/{number}/"

    try:
        response = requests.get(api_url, timeout=5)
        data = response.json()
    except Exception as e:
        data = {"status_message": "Error", "error": str(e)}

    return render(request, "sim_insight_demo.html", {
        "data": data,
        "number": number
    })
    