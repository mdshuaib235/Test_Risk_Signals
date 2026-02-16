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

import requests
import os

class TestNumberInsights(APIView):


    def post(self, request , phone_number:str,  *args , **kwargs):
        

        url = "https://api.nexmo.com/ni/advanced/json"

        params = {
            "api_key": os.getenv("VONAGE_API_KEY"),
            "api_secret": os.getenv("VONAGE_API_SECRET"),
            "number": phone_number
        }
        response = requests.get(url, params=params)
        print(response.json())
        
        return Response(response, status=200)


        #  Advanced API (need organization onboarding on vonage)
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