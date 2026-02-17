from django.shortcuts import render
from django.shortcuts import render
import uuid
from rest_framework.views import APIView
from rest_framework import status
from vonage import Auth, Vonage
from vonage import NetworkSimSwap

from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
import requests
import os
import json

# TODO: convert GET api to POST 
class TestNumberInsights(APIView):


    def get(self, request , phone_number:str,  *args , **kwargs):
        
        url = "https://api.nexmo.com/ni/advanced/json"

        params = {
            "api_key": os.getenv("VONAGE_API_KEY"),
            "api_secret": os.getenv("VONAGE_API_SECRET"),
            "number": phone_number
        }
                
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            return Response(
                {"error": "Failed to fetch data from Vonage", "details": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        try:
            data = response.json() 
        except Exception as e:
            return Response(
                {"error": "Failed to parse JSON from Vonage", "raw": response.text, "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
    def get(self, request, number:str):
        
        response = requests.post(
            "https://api.nexmo.com/verify/json",
            data = {
                "api_key": os.getenv("VONAGE_API_KEY"),
                "api_secret": os.getenv("VONAGE_API_SECRET"),
                "number": number,
                "brand": "YourBankApp"
            }
        )
        return Response(response.json())
    
class VerifyCheckAPIView(APIView):
    def get(self, request, number, code):
       
        response = requests.post(
            "https://api.verify.vonage.com/check",
            data={
                "api_key": os.getenv("VONAGE_API_KEY"),
                "api_secret": os.getenv("VONAGE_API_SECRET"),
                "request_id": code,
                "code": code
            }
        )
        return Response(response.json())