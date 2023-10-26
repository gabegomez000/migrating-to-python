import requests
import os
import json
import datetime
import base64
import asyncio
from dotenv import dotenv_values
from pricelist import pricelist
import logging.config

#import env variables
config = dotenv_values(".env")

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
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/incremental.log',
            'level': 'DEBUG',
            'formatter': 'simple'
        }
    },
    'formatters': {
        'simple': {
            'format': '[%(asctime)s] [%(process)d] [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S %z'
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['Console', 'file'],
    },
}

def send_slack_message(message):
    payload = {
        "text": message
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(config["SLACK_WEBHOOK"], headers=headers, data=json.dumps(payload))

logging.config.dictConfig(logging_config)
console_logger = logging.getLogger('Console')

# set up wordpress url if staging is true in env
if os.environ.get('STAGING') == 'true':
    config['WORDPRESS_URL'] = config['STAGING_URL']

#update pricelist
pricelist()

#get date minus 1 hour
date_start = datetime.datetime.now() - datetime.timedelta(hours=1)
date_start = date_start.strftime("%Y-%m-%dT%H:00:00")

# #build api request
payload = {
    'Key': config['API_KEY'],
    'Operation': 'GetEntities',
    'Entity': 'cobalt_class',
    'Filter': f'modifiedon<ge>{date_start}',
    'Attributes': 'cobalt_classbegindate,cobalt_classenddate,cobalt_classid,cobalt_locationid,cobalt_name,cobalt_description,cobalt_locationid,cobalt_cobalt_tag_cobalt_class/cobalt_name,cobalt_fullday,cobalt_publishtoportal,statuscode,cobalt_cobalt_classinstructor_cobalt_class/cobalt_name,cobalt_cobalt_class_cobalt_classregistrationfee/cobalt_productid,cobalt_cobalt_class_cobalt_classregistrationfee/statuscode,cobalt_outsideprovider,cobalt_outsideproviderlink,cobalt_cobalt_class_cobalt_classregistrationfee/cobalt_publishtoportal'
}

#request data from RAMCO API
response = requests.post(config['API_URL'], data=payload)
body = json.loads(response.text)
classes = body['Data']

#loop through classes
def process_classes(classes):
    for obj in classes:

        #format start date
        startDate = datetime.datetime.fromtimestamp(obj['cobalt_ClassBeginDate']['Value'])
        obj['cobalt_ClassBeginDate']['Display'] = startDate.strftime("%Y-%m-%d %H:%M:%S")

        #format end date
        endDate = datetime.datetime.fromtimestamp(obj['cobalt_ClassEndDate']['Value'])
        obj['cobalt_ClassEndDate']['Display'] = endDate.strftime("%Y-%m-%d %H:%M:%S")

        #get order ids
        orderIds = []
        for item in obj['cobalt_cobalt_class_cobalt_classregistrationfee']:
            orderIds.append({
                'id': item['cobalt_productid']['Value'],
                'status': item['statuscode']['Value'],
            })
        
        #remove order ids
        orderIds = [item for item in orderIds if item['id'] != '8d6bb524-f1d8-41ad-8c21-ae89d35d4dc3']
        orderIds = [item for item in orderIds if item['id'] != 'c3102913-ffd4-49d6-9bf6-5f0575b0b635']
        orderIds = [item for item in orderIds if item['id'] != None]
        orderIds = [item for item in orderIds if item['status'] == 1]

        #get price
        prices = json.load(open('./pricelist.json', 'r'))

        #set price
        if len(orderIds) > 0:
            cost = [item for item in prices if item['ProductId'] == orderIds[0]['id']]
            obj['cobalt_price'] = cost[0]['Price']
        else:
            obj['cobalt_price'] = '0.0000'

        #remove decimals
        obj['cobalt_price'] = obj['cobalt_price'][:-2]

        #set price to blank if outside provider
        if obj['cobalt_OutsideProvider'] == 'true':
            obj['cobalt_price'] = ''

        #create an array for tags
        tags = []

        #loop through tags
        for item in obj['cobalt_cobalt_tag_cobalt_class']:
            tags.append(item['cobalt_name'])
        
        #set status code
        obj['statuscode'] = obj['statuscode']['Display']

        #set publish status
        if obj['statuscode'] == 'Inactive' or obj['cobalt_PublishtoPortal'] == 'false':
            obj['publish'] = True
        elif obj['statuscode'] == 'Active' and obj['cobalt_PublishtoPortal'] == 'true':
            obj['publish'] = False
        else:
            obj['publish'] = True

        #set all day status
        if obj['cobalt_fullday'] == 'true':
            obj['all_day'] = True
        else:
            obj['all_day'] = False
        
        #set location id
        cobalt_location_id = obj['cobalt_LocationId']['Display']

        #map locations
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

        #set default style and location id
        default_style = ""  # Default style value
        default_location_id = 0  # Default location ID value

        #set style and location id
        style, location_id = location_mapping.get(cobalt_location_id, (default_style, default_location_id))

        #set style
        if isinstance(location_id, (int, float)):
            obj['cobalt_name'] = f"<span style=\"color:{style};\">{obj['cobalt_name']}</span>"
            obj['cobalt_LocationId'] = location_id
        else:
            obj['cobalt_name'] = obj['cobalt_name']

        #set outside provider link
        if obj['cobalt_OutsideProvider'] == 'true':
            obj['cobalt_Description'] = f"{obj['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='{obj['cobalt_OutsideProviderLink']}'\" />"
        else:
            obj['cobalt_Description'] = f"${obj['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx%3Fcid%3D{obj['cobalt_classId']}'\" />"

        if(len(obj['cobalt_cobalt_classinstructor_cobalt_class']) > 0):
            classInstructor = [item['cobalt_name'] for item in obj['cobalt_cobalt_classinstructor_cobalt_class']]
            obj['cobalt_Description'] = f"<p style=\"font-weight:bold;color: black;\">Instructor: ${classInstructor[0]}</p><br><br>${obj['cobalt_Description']}"
        else:
            obj['cobalt_Description'] = obj['cobalt_Description']

        #set tags
        obj['cobalt_cobalt_tag_cobalt_class'] = tags

try:
    process_classes(classes)
except Exception as e:
    console_logger.error(e)

new_classes = []
featured_classes = []
existing_classes = []

#check if class exists
def check_if_exists(classes):
    for obj in classes:
        response = requests.get(f"{config['WORDPRESS_URL']}/by-slug/{obj['cobalt_classId']}")
        response = response.json()

        #print(response)

        if 'id' in response:

            response_tags = [obj['name'] for obj in response['tags']]
            all_tags = obj['cobalt_cobalt_tag_cobalt_class'] + response_tags

            print(response['url'])
            filtered_tags = list(set(all_tags))

            if response['image'] == False :
                obj['cobalt_cobalt_tag_cobalt_class'] = filtered_tags
                print("No class image!")
                existing_classes.append(obj)

            else:

                obj['cobalt_cobalt_tag_cobalt_class'] = filtered_tags
                obj['featuredImage'] = response['image']['url']
                print(response['image']['url'])
                featured_classes.append(obj)

        else:
            new_classes.append(obj)

#get response

if len(classes) == 0:
    console_logger.debug("No new classes to process")
    exit()
else:
    try:
        check_if_exists(classes)
    except Exception as e:
        console_logger.error(e)

console_logger.debug(f"Existing Classes: {len(existing_classes)}")
console_logger.debug(f"Featured Classes: {len(featured_classes)}")
console_logger.debug(f"New Classes: {len(new_classes)}")

async def submit_existing_class(data):
    console_logger.debug(f"Submitting existing class: {data['cobalt_classId']} - {data['cobalt_LocationId']}")
    ramcoClass = {
                "title": data['cobalt_name'],
                "status": "publish",
                "hide_from_listings": data['publish'],
                "description": data['cobalt_Description'],
                "all_day": data['all_day'],
                "start_date": data['cobalt_ClassBeginDate']['Display'],
                "end_date": data['cobalt_ClassEndDate']['Display'],
                "slug": data['cobalt_classId'],
                "categories": data['cobalt_cobalt_tag_cobalt_class'],
                "show_map_link": True,
                "show_map": True,
                "cost": data['cobalt_price'],
                "tags": data['cobalt_cobalt_tag_cobalt_class']
            }
    
    if data['cobalt_LocationId'] != 0:
        ramcoClass['venue'] = {
            "id": data['cobalt_LocationId']
        }
    
    #set url and headers
    url = f"{config['WORDPRESS_URL']}/by-slug/{data['cobalt_classId']}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(config['WORDPRESS_CREDS'].encode()).decode()
    }

    #post data
    response = requests.post(url, headers=headers, data=json.dumps(ramcoClass))
    
    if response.status_code == 201:
        console_logger.debug("Class updated successfully!")
    else:
        console_logger.error(response.text)
        send_slack_message(response.text)

    #print(response)

async def submit_featured_class(data):
    console_logger.debug(f"Submitting featured class: {data['cobalt_classId']} - {data['cobalt_LocationId']}")
    ramcoClass = {
                "title": data['cobalt_name'],
                "status": "publish",
                "hide_from_listings": data['publish'],
                "description": data['cobalt_Description'],
                "all_day": data['all_day'],
                "start_date": data['cobalt_ClassBeginDate']['Display'],
                "end_date": data['cobalt_ClassEndDate']['Display'],
                "slug": data['cobalt_classId'],
                "categories": data['cobalt_cobalt_tag_cobalt_class'],
                "show_map_link": True,
                "show_map": True,
                "cost": data['cobalt_price'],
                "tags": data['cobalt_cobalt_tag_cobalt_class']
            }
    
    if data['cobalt_LocationId'] != 0:
        ramcoClass['venue'] = {
            "id": data['cobalt_LocationId']
        }

    #set url and headers
    url = f"{config['WORDPRESS_URL']}/by-slug/{data['cobalt_classId']}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(config['WORDPRESS_CREDS'].encode()).decode()
    }

    #post data
    response = requests.post(url, headers=headers, data=json.dumps(ramcoClass))
    
    if response.status_code == 201:
        console_logger.debug("Class updated successfully!")
    else:
        console_logger.error(response.text)
        send_slack_message(response.text)


    #print(response)

async def sumbit_e_classes(data):
    for obj in data:
        await submit_existing_class(obj)

async def sumbit_f_classes(data):
    for obj in data:
        await submit_featured_class(obj)

asyncio.run(sumbit_e_classes(existing_classes))
asyncio.run(sumbit_f_classes(featured_classes))
