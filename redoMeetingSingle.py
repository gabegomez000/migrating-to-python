import requests
import json
import datetime
import base64
from dotenv import dotenv_values

# import env variables
config = dotenv_values(".env")

# request guid from user
guid = input("Meeting GUID: ")

# Get the data from the API
payload = {
    'Key': config['API_KEY'],
    'Operation': 'GetEntity',
    'Entity': 'cobalt_meeting',
    'Guid': guid,
    'Attributes': 'cobalt_BeginDate,cobalt_EndDate,cobalt_meetingid,cobalt_Location,cobalt_name,cobalt_description,cobalt_cobalt_tag_cobalt_meeting/cobalt_name,cobalt_FullDay,cobalt_publishtoportal,statuscode,cobalt_Meeting_Cobalt_MeetingRegistrationFees/cobalt_productid,cobalt_Meeting_Cobalt_MeetingRegistrationFees/statuscode,cobalt_outsideprovider,cobalt_outsideproviderlink'
}

# request data from RAMCO API
r = requests.post(config['API_URL'], data=payload)

# Parse the data
data = json.loads(r.text)
data = data['Data']

print(data)

startDate = datetime.datetime.fromtimestamp(data['cobalt_BeginDate']['Value'])
data['cobalt_BeginDate']['Display'] = startDate.strftime("%Y-%m-%d %H:%M:%S")

EndDate = datetime.datetime.fromtimestamp(data['cobalt_EndDate']['Value'])
data['cobalt_EndDate']['Display'] = EndDate.strftime("%Y-%m-%d %H:%M:%S")

orderIds = []
for item in data['cobalt_Meeting_Cobalt_MeetingRegistrationFees']:
    orderIds.append({
        'id': item['cobalt_productid']['Value'],
        'status': item['statuscode']['Value']
    })

prices = json.load(open('./pricelist.json', 'r'))

orderIds = [item for item in orderIds if item['id'] != '8d6bb524-f1d8-41ad-8c21-ae89d35d4dc3']
orderIds = [item for item in orderIds if item['id'] != 'c3102913-ffd4-49d6-9bf6-5f0575b0b635']
orderIds = [item for item in orderIds if item['id'] != None]
orderIds = [item for item in orderIds if item['status'] == 1]

if len(orderIds) > 0:
    cost = [item for item in prices if item['ProductId'] == orderIds[0]['id']]
    data['cobalt_price'] = cost[0]['Price']
else:
    data['cobalt_price'] = '0.0000'

data['cobalt_price'] = data['cobalt_price'][:-2]

if data['cobalt_OutsideProvider'] == 'true':
    data['cobalt_price'] = ''

tags = []

for item in data['cobalt_cobalt_tag_cobalt_meeting']:
    tags.append(item['cobalt_name'])

data['statuscode'] = data['statuscode']['Display']

if data['statuscode'] == 'Inactive' or data['cobalt_PublishtoPortal'] == 'false':
    data['publish'] = False
elif data['statuscode'] == 'Active' and data['cobalt_PublishtoPortal'] == 'true':
    data['publish'] = True
else:
    data['publish'] = False

if data['cobalt_FullDay'] == 'true':
    data['all_day'] = True
else:
    data['all_day'] = False

cobalt_location_id = data['cobalt_Location']

location_mapping = {
    "MIAMI HQ": ("#798e2d", 4694),
    "West Broward - Sawgrass Office": ("#0082c9", 4698),
    "Coral Gables Office": ("#633e81", 4696),
    "JTHS - MIAMI Training Room (Jupiter)": ("#005962", 4718),
    "Northwestern Dade": ("#9e182f", 4735),
    "Northwestern Dade Office": ("#9e182f", 4735),
    "NE Broward Office-Ft. Lauderdale": ("#f26722", 4702),
    "Aventura Office": ("#000000", 22099)
}

default_style = ""  # Default style value
default_location_id = ""  # Default location ID value

style, location_id = location_mapping.get(cobalt_location_id, (default_style, default_location_id))

if isinstance(location_id, (int, float)):
    data['cobalt_name'] = f"<span style=\"color:{style};\">{data['cobalt_name']}</span>"
    data['cobalt_LocationId'] = location_id
else:
    data['cobalt_name'] = data['cobalt_name']

if data['cobalt_OutsideProvider'] == 'true':
    data[
        'cobalt_Description'] = f"{data['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='{data['cobalt_OutsideProviderLink']}'\" />"
else:
    data[
        'cobalt_Description'] = f"${data['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx%3Fcid%3D{data['cobalt_meetingId']}'\" />"

data['cobalt_cobalt_tag_cobalt_meeting'] = tags

featured_meetings = []
existing_meetings = []
new_meetings = []


def check_if_exists():
    response = requests.get(f"{config['WORDPRESS_URL']}/by-slug/{data['cobalt_meetingId']}")
    return response.json()


response = check_if_exists()

if isinstance(response['id'], int):

    response_tags = [data['name'] for data in response['tags']]
    all_tags = data['cobalt_cobalt_tag_cobalt_meeting'] + response_tags

    print(response['url'])
    filtered_tags = list(set(all_tags))

    if response['image'] == False:
        data['cobalt_cobalt_tag_cobalt_meeting'] = filtered_tags
        print("No meeting image!")
        existing_meetings.append(data)

    else:

        data['cobalt_cobalt_tag_cobalt_meeting'] = filtered_tags
        data['featuredImage'] = response['image']['url']
        print(response['image']['url'])
        featured_meetings.append(data)

else:
    new_meetings.append(data)


def modify_existing_meeting(data):
    print(data)

    ramco_meeting = {
        "title": data[0]['cobalt_name'],
        "status": "publish",
        "hide_from_listings": data[0]['publish'],
        "description": data[0]['cobalt_Description'],
        "all_day": data[0]['all_day'],
        "start_date": data[0]['cobalt_BeginDate']['Display'],
        "end_date": data[0]['cobalt_EndDate']['Display'],
        "slug": data[0]['cobalt_meetingId'],
        "categories": data[0]['cobalt_cobalt_tag_cobalt_meeting'],
        "show_map_link": True,
        "show_map": True,
        "cost": data[0]['cobalt_price'],
        "tags": data[0]['cobalt_cobalt_tag_cobalt_meeting']
    }

    if isinstance(location_id, (int, float)):
        ramco_meeting["venue"] = {"id": data[0]['locationId']}

    url = f"{config['WORDPRESS_URL']}/by-slug/{data[0]['cobalt_meetingId']}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(config['WORDPRESS_CREDS'].encode()).decode()
    }
    response = requests.post(url, headers=headers, data=json.dumps(ramco_meeting))
    body = response.json()
    print(body)
    print(f"Meeting processed: {data[0]['cobalt_name']}")


def modify_featured_meeting(data):
    ramco_meeting = {
        "title": data[0]['cobalt_name'],
        "status": "publish",
        "hide_from_listings": data[0]['publish'],
        "description": data[0]['cobalt_Description'],
        "image": data[0]['featuredImage'],
        "all_day": data[0]['all_day'],
        "start_date": data[0]['cobalt_BeginDate']['Display'],
        "end_date": data[0]['cobalt_EndDate']['Display'],
        "slug": data[0]['cobalt_meetingId'],
        "categories": data[0]['cobalt_cobalt_tag_cobalt_meeting'],
        "show_map_link": True,
        "show_map": True,
        "cost": data[0]['cobalt_price'],
        "tags": data[0]['cobalt_cobalt_tag_cobalt_meeting']
    }

    if isinstance(location_id, (int, float)):
        ramco_meeting["venue"] = {"id": data[0]['locationId']}

    url = f"{config['WORDPRESS_URL']}/by-slug/{data[0]['cobalt_meetingId']}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(config['WORDPRESS_CREDS'].encode()).decode()
    }
    response = requests.post(url, headers=headers, data=json.dumps(ramco_meeting))

    body = response.json()

    print(body)
    print(f"Meeting processed: {data[0]['cobalt_name']}")


if len(existing_meetings) > 0:
    modify_existing_meeting(existing_meetings)
elif len(featured_meetings) > 0:
    modify_featured_meeting(featured_meetings)