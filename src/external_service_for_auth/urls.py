from django.contrib import admin
from django.urls import include, path

from .views import *

urlpatterns = [
    path(
        "insights/<str:phone_number>/",
        TestNumberInsights.as_view(),
        name="test_number_insights_vonage",
    ),
    path("sim-insight-demo/", SimInsightDemo, name="sim_insight_demo"),
    path(
        "open-gsma/sim-swap/",
        SimSwapOpenGSMASandboxs,
        name="sim_swap_open_gsma_sandbox",
    ),
    path("vonage/sim-swap/", VonageSimSwap.as_view(), name="sim_swap_vonage"),
    path(
        "send-otp/<str:number>/", VerifyStartAPIView.as_view(), name="otp_sent_vonage"
    ),
    path(
        "verify-otp/<str:number>/<str:code>/<str:request_id>/",
        VerifyCheckAPIView.as_view(),
        name="otp_verify_vonage",
    ),
    
    #  IDlayr callback and redirect urls
    #  https://nida-debonair-unprotuberantly.ngrok-free.dev/v1/sim-number/idlayr-callback/
    #  https://nida-debonair-unprotuberantly.ngrok-free.dev/v1/sim-number/idlayr-redirect/
    path("idlayr-callback/", idlayr_callback, name="idlayr_registered_callback"),
    path("idlayr-redirect/", idlayr_redirect, name="idlayr_registered_redirect"),
    path("create-sna-check/", create_subscriber_check, name="create_subscriber_check"),
    path("complete-sna-check/", complete_subscriber_check, name="complete_subscriber_check"),
    path("reachability-check/", reachability_test, name="reachability_test"),
    
    
    # vonage regsitered url (You can allow up to 5 numbers for testing. Tap 'Configure Playground' to manage your phone numbers. For full access, you need to submit your business registratio)
    # https://nida-debonair-unprotuberantly.ngrok-free.dev/v1/sim-number/advanced-verify-v2 (Verify V2 -> Status URL)
    # https://nida-debonair-unprotuberantly.ngrok-free.dev/v1/sim-number/advanced-network-verify-event-callback (network -> Verify Event status callback )
    # https://nida-debonair-unprotuberantly.ngrok-free.dev/v1/sim-number/advanced-network-number-verification-redirect (network -> Number verification Redirect URI )
]
