from django.contrib import admin
from django.urls import include, path

from .views import TestNumberInsights, VerifyCheckAPIView, VerifyStartAPIView, sim_swap_open_gsma_sandbox



urlpatterns = [
    path( "insights/<str:phone_number>/", TestNumberInsights.as_view(), name="test_number_insights" ),
    path( "send-otp/<str:number>/", VerifyStartAPIView.as_view(), name="vonage_otp_sent"),
    path( "verify-otp/<str:number>/<str:code>/<str:request_id>/", VerifyCheckAPIView.as_view(), name="vonage_otp_verify"),

    path('open-gsma/sim-swap/', sim_swap_open_gsma_sandbox, name='sim_swap_open_gsma_sandbox')
    
    # vonage regsitered url (You can allow up to 5 numbers for testing. Tap 'Configure Playground' to manage your phone numbers. For full access, you need to submit your business registratio)
    
    # https://nida-debonair-unprotuberantly.ngrok-free.dev/v1/sim-number/advanced-verify-v2 (Verify V2 -> Status URL)
    # https://nida-debonair-unprotuberantly.ngrok-free.dev/v1/sim-number/advanced-network-verify-event-callback (network -> Verify Event status callback )
    # https://nida-debonair-unprotuberantly.ngrok-free.dev/v1/sim-number/advanced-network-number-verification-redirect (network -> Number verification Redirect URI )
    
]
