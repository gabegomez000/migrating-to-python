import requests
import os
import json
import datetime
import base64
from dotenv import dotenv_values
from pricelist import pricelist
import logging.config


#setup logging
logging_config = {
    'version': 1,
    'handlers': {
        'Console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'stream': 'ext://sys.stderr',  # Redirect to stderr
            'formatter': 'simple',
        },
    },
    'formatters': {
        'simple': {
            'format': '[%(asctime)s] [%(process)d] [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S %z'
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['Console'],
    },
}

logging.config.dictConfig(logging_config)
console_logger = logging.getLogger('Console')

#import env variables
config = dotenv_values(".env")

# set up wordpress url if staging is true in env
if os.environ.get('STAGING') == 'true':
    config['WORDPRESS_URL'] = config['STAGING_URL']

#request guid from user
guid = input("Class GUID: ")

#update pricelist
pricelist()

# Get the data from the API
payload = {
    'Key': config['API_KEY'],
    'Operation': 'GetEntity',
    'Entity': 'cobalt_class',
    'Guid': guid,
    'Attributes': 'cobalt_classbegindate,cobalt_classenddate,cobalt_classid,cobalt_locationid,cobalt_name,cobalt_description,cobalt_locationid,cobalt_cobalt_tag_cobalt_class/cobalt_name,cobalt_fullday,cobalt_publishtoportal,statuscode,cobalt_cobalt_classinstructor_cobalt_class/cobalt_name,cobalt_cobalt_class_cobalt_classregistrationfee/cobalt_productid,cobalt_cobalt_class_cobalt_classregistrationfee/statuscode,cobalt_outsideprovider,cobalt_outsideproviderlink'
}

#request data from RAMCO API
r = requests.post(config['API_URL'], data=payload)

# Parse the data
data = json.loads(r.text)
data = data['Data']

startDate = datetime.datetime.fromtimestamp(data['cobalt_ClassBeginDate']['Value'])
data['cobalt_ClassBeginDate']['Display'] = startDate.strftime("%Y-%m-%d %H:%M:%S")

endDate = datetime.datetime.fromtimestamp(data['cobalt_ClassEndDate']['Value'])
data['cobalt_ClassEndDate']['Display'] = endDate.strftime("%Y-%m-%d %H:%M:%S")

orderIds = []
for item in data['cobalt_cobalt_class_cobalt_classregistrationfee']:
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

for item in data['cobalt_cobalt_tag_cobalt_class']:
    tags.append(item['cobalt_name'])

data['statuscode'] = data['statuscode']['Display']

if data['statuscode'] == 'Inactive' or data['cobalt_PublishtoPortal'] == 'false':
    data['publish'] = True
elif data['statuscode'] == 'Active' and data['cobalt_PublishtoPortal'] == 'true':
    data['publish'] = False
else:
    data['publish'] = True

if data['cobalt_fullday'] == 'true':
    data['all_day'] = True
else:
    data['all_day'] = False

cobalt_location_id = data['cobalt_LocationId']['Display']

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
    data['cobalt_Description'] = f"{data['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='{data['cobalt_OutsideProviderLink']}'\" />"
else:
    data['cobalt_Description'] = f"{data['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx%3Fcid%3D{data['cobalt_classId']}'\" />"

if(len(data['cobalt_cobalt_classinstructor_cobalt_class']) > 0):
    classInstructor = [item['cobalt_name'] for item in data['cobalt_cobalt_classinstructor_cobalt_class']]
    data['cobalt_Description'] = f"<p style=\"font-weight:bold;color: black;\">Instructor: {classInstructor[0]}</p><br><br>{data['cobalt_Description']}"
else:
    data['cobalt_Description'] = data['cobalt_Description']

data['cobalt_cobalt_tag_cobalt_class'] = tags

featured_classes = []
existing_classes = []
new_classes = []

def check_if_exists():
    response = requests.get(f"{config['WORDPRESS_URL']}/by-slug/{data['cobalt_classId']}")
    return response

response = check_if_exists()

if response.status_code == 200:

    response = response.json()

    response_tags = [data['name'] for data in response['tags']]
    all_tags = data['cobalt_cobalt_tag_cobalt_class'] + response_tags

    #print(response['url'])
    filtered_tags = list(set(all_tags))

    if response['image'] == False :
        data['cobalt_cobalt_tag_cobalt_class'] = filtered_tags
        #print("No class image!")
        existing_classes.append(data)

    else:

        data['cobalt_cobalt_tag_cobalt_class'] = filtered_tags
        data['featuredImage'] = response['image']['url']
        #print(response['image']['url'])
        featured_classes.append(data)

else:
    new_classes.append(data)



def modify_existing_class(data):
    console_logger.debug(data)

    ramco_class = {
        "title": data[0]['cobalt_name'],
        "status": "publish",
        "hide_from_listings": data[0]['publish'],
        "description": data[0]['cobalt_Description'],
        "all_day": data[0]['all_day'],
        "start_date": data[0]['cobalt_ClassBeginDate']['Display'],
        "end_date": data[0]['cobalt_ClassEndDate']['Display'],
        "slug": data[0]['cobalt_classId'],
        "categories": data[0]['cobalt_cobalt_tag_cobalt_class'],
        "show_map_link": True,
        "show_map": True,
        "cost": data[0]['cobalt_price'],
        "tags": data[0]['cobalt_cobalt_tag_cobalt_class']
    }

    if isinstance(location_id, (int, float)):
        ramco_class["venue"] = {"id": data[0]['cobalt_LocationId']}
    

    url = f"{config['WORDPRESS_URL']}/by-slug/{data[0]['cobalt_classId']}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(config['WORDPRESS_CREDS'].encode()).decode()
    }
    response = requests.post(url, headers=headers, data=json.dumps(ramco_class))
    body = response.json()
    console_logger.debug(body)
    print(f"Class processed: {data[0]['cobalt_name']}")

def modify_featured_class(data):
    console_logger.debug(data)
    ramco_class = {
        "title": data[0]['cobalt_name'],
        "status": "publish",
        "hide_from_listings": data[0]['publish'],
        "description": data[0]['cobalt_Description'],
        "image": data[0]['featuredImage'],
        "all_day": data[0]['all_day'],
        "start_date": data[0]['cobalt_ClassBeginDate']['Display'],
        "end_date": data[0]['cobalt_ClassEndDate']['Display'],
        "slug": data[0]['cobalt_classId'],
        "categories": data[0]['cobalt_cobalt_tag_cobalt_class'],
        "show_map_link": True,
        "show_map": True,
        "cost": data[0]['cobalt_price'],
        "tags": data[0]['cobalt_cobalt_tag_cobalt_class'],
        "featured": True
    }

    if isinstance(location_id, (int, float)):
        ramco_class["venue"] = {"id": data[0]['cobalt_LocationId']}

    url = f"{config['WORDPRESS_URL']}/by-slug/{data[0]['cobalt_classId']}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(config['WORDPRESS_CREDS'].encode()).decode()
    }
    response = requests.post(url, headers=headers, data=json.dumps(ramco_class))

    body = response.json()

    console_logger.debug(body)
    print(f"Class processed: {data[0]['cobalt_name']}")

if len(existing_classes) > 0:
    modify_existing_class(existing_classes)
elif len(featured_classes) > 0:
    modify_featured_class(featured_classes)