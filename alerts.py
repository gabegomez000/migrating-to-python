import requests
from dotenv import dotenv_values

config = dotenv_values(".env")

def sendNtfyAlert(message, title="Script Alert"):
    url = config['NTFY_URL']
    token = config['NTFY_TOKEN']

    headers = {
        "Authorization": f"Bearer {token}",
        "Title": title
    }

    # ntfy expects raw text in the body, not a JSON object
    result = requests.post(url, data=message, headers=headers)

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"Failed to send ntfy alert: {err}")
    else:
        print(f"Payload delivered successfully, code {result.status_code}.")