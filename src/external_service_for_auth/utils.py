import os, requests



CLIENT_ID = os.getenv("OPENGW_CLIENT_ID")
CLIENT_SECRET = os.getenv("OPENGW_CLIENT_SECRET")
TOKEN_URL = os.getenv("OPENGW_TOKEN_URL")
API_BASE = os.getenv("OPENGW_API_BASE")


def call_sim_swap_check(phone_number, max_age):
    
    token = os.getenv('OPENGW_CLIENT_SECRET')
    url = f"{API_BASE}/sim-swap/v1/check"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {"phoneNumber": phone_number, "maxAge": max_age}

    resp = requests.post(url, json=body, headers=headers)
    return resp.json()

def call_sim_swap_date(phone_number):
    token = os.getenv('OPENGW_CLIENT_SECRET')
    url = f"{API_BASE}/sim-swap/v1/retrieve-date"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {"phoneNumber": phone_number}

    resp = requests.post(url, json=body, headers=headers)
    return resp.json()


OPENGW_CLIENT_ID =os.getenv('OPENGW_CLIENT_ID')
OPENGW_CLIENT_SECRET = os.getenv("OPENGW_CLIENT_SECRET")
OPENGW_TOKEN_URL =os.getenv('OPENGW_TOKEN_URL')

def get_access_token():
    # NOTE: facing internal server error from open-GSMA
    # REFRESH PERIODICALLY before testing (background-job)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": OPENGW_CLIENT_ID,
        "client_secret": OPENGW_CLIENT_SECRET,
        "scope": "sim-swap:check sim-swap:retrieve-date"
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    token = response.json().get("access_token")
    return token
