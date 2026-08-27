import requests
from dotenv import dotenv_values

config = dotenv_values(".env")

def sendNtfyAlert(message, title="Script Alert"):
    url = config['NTFY_URL']
    token = config['NTFY_TOKEN']

    payload = {
        "device_key": token,
        "title": title,
        "body": message
    }

    result = requests.post(url, json=payload)  # json= sets Content-Type and encodes correctly

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"Failed to send Bark alert: {err}")
    else:
        print(f"Payload delivered successfully, code {result.status_code}.")