import os, requests, time, jwt



OPENGW_CLIENT_ID =os.getenv('OPENGW_CLIENT_ID')
OPENGW_CLIENT_SECRET = os.getenv("OPENGW_CLIENT_SECRET")

TOKEN_URL = os.getenv("OPENGW_TOKEN_URL")
API_BASE = os.getenv("OPENGW_API_BASE")
OPENGW_TOKEN_URL =os.getenv('OPENGW_TOKEN_URL')


def check_sim_swap_from_vonage(phone_number):
    jwt_token = os.getenv("VONAGE_ACCESS_TOKEN")
    print(f'token vonage = {jwt_token} in sim-swap-vonage func')
    url = "https://api.nexmo.com/v2/verify"

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "phoneNumber": phone_number
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    data = None
    try:
        data = response.json()
        print('completed check_sim_swap_from_vonage .... response=', response.json())
    except Exception as err:
        print('error in vonage sim-swap json decoding response, error=', err)
        print('response-text=', response.text)
        
    print("Status Code:", response.status_code)
    
    if response.status_code != 200:
        return  {
            "error": "Vonage API Error",
            "status_code": response.status_code,
            "response_text": response.text
        }

    return data

    

def call_sim_swap_check_frm_gsma(phone_number, max_age):

    token = os.getenv('OPENGW_CLIENT_SECRET')
    url = f"{API_BASE}/sim-swap/v1/check"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {"phoneNumber": phone_number, "maxAge": max_age}

    resp = requests.post(url, json=body, headers=headers , timeout=10)
    return resp.json()

def call_sim_swap_date_from_gsma(phone_number):
    token = os.getenv('OPENGW_CLIENT_SECRET')
    url = f"{API_BASE}/sim-swap/v1/retrieve-date"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {"phoneNumber": phone_number}

    resp = requests.post(url, json=body, headers=headers , timeout=10)
    return resp.json()



def get_access_token_from_gsma():
    # NOTE: facing internal server error from open-GSMA
    # REFRESH PERIODICALLY and update in env before testing for now (background-job)
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

def get_access_token_from_vonage():
    
    application_id = os.getenv("VONAGE_APPLICATION_ID")

    with open("vonage_private.key", "r") as f:
        private_key = f.read()

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "application_id": application_id
    }

    token = jwt.encode(payload, private_key, algorithm="RS256")

    print(token, "------ vonage access token")
    return token
