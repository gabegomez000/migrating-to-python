import requests
import json
from datetime import datetime
import pytz
import os
import base64
from urllib.parse import urlencode
from dotenv import dotenv_values

config = dotenv_values(".env")

# set up wordpress url if staging is true in env
if os.environ.get('STAGING') == 'true':
    config['WORDPRESS_URL'] = config['STAGING_URL']

def push_classes():
    with open('logs/logs.txt', 'a') as log_file:
        log_file.write(f"[{datetime.now().strftime('%I:%M:%S %p')}] RAMCO to WordPress Sync started.\n")

    class_guid = input('Class GUID: ')

    api_url = config['API_URL']
    api_key = config['API_KEY']
    staging = os.environ.get('STAGING')

    if staging == 'false':
        print('PUSHING TO: Live Environment')
    elif staging == 'true':
        print('PUSHING TO: Staging Environment')
    else:
        print('ERROR: STAGING variable not provided.')
        exit()  # Stop execution

    form_data = {
        'Key': api_key,
        'Operation': 'GetEntity',
        'Entity': 'cobalt_class',
        'Guid': class_guid,
        'Attributes': 'cobalt_classbegindate,cobalt_classenddate,cobalt_classid,cobalt_locationid,cobalt_name,'
                      'cobalt_description,cobalt_locationid,cobalt_cobalt_tag_cobalt_class/cobalt_name,cobalt_fullday,'
                      'cobalt_publishtoportal,statuscode,cobalt_cobalt_classinstructor_cobalt_class/cobalt_name,'
                      'cobalt_cobalt_class_cobalt_classregistrationfee/cobalt_productid,'
                      'cobalt_cobalt_class_cobalt_classregistrationfee/statuscode'
    }

    response = requests.post(api_url, data=form_data)
    body = json.loads(response.text)
    data = body['Data']

    start = datetime.strptime(data['cobalt_ClassBeginDate']['Display'], '%Y-%m-%dT%H:%M:%S')
    end = datetime.strptime(data['cobalt_ClassEndDate']['Display'], '%Y-%m-%dT%H:%M:%S')

    start = pytz.timezone('Etc/GMT').localize(start).astimezone(pytz.timezone('America/New_York'))
    end = pytz.timezone('Etc/GMT').localize(end).astimezone(pytz.timezone('America/New_York'))

    data['cobalt_ClassBeginDate']['Display'] = start.strftime('%Y-%m-%d %H:%M:%S')
    data['cobalt_ClassEndDate']['Display'] = end.strftime('%Y-%m-%d %H:%M:%S')

    order_ids = []
    for item in data['cobalt_cobalt_class_cobalt_classregistrationfee']:
        order_ids.append({
            'id': item['cobalt_productid']['Value'],
            'status': item['statuscode']['Value']
        })

    prices = json.load(open('./pricelist.json', 'r'))

    order_ids = [item for item in order_ids if item['id'] != '8d6bb524-f1d8-41ad-8c21-ae89d35d4dc3']
    order_ids = [item for item in order_ids if item['status'] == 1]

    if len(order_ids) > 0:
        cost = next((price['Price'] for price in prices if price['ProductId'] == order_ids[0]['id']), None)
        data['cobalt_price'] = cost or '0.0000'
    else:
        data['cobalt_price'] = '0.0000'

    data['cobalt_price'] = data['cobalt_price'] if data['cobalt_price'] else '0.0000'

    if len(data['cobalt_cobalt_tag_cobalt_class']) > 0:
        data['cobalt_cobalt_tag_cobalt_class'] = ', '.join([tag['cobalt_name']
                                                            for tag in data['cobalt_cobalt_tag_cobalt_class']])
    else:
        data['cobalt_cobalt_tag_cobalt_class'] = ''

    # Console.log(data.cobalt_price)
    # Console.log(`-------`)

    # Remove the last two characters from data.cobalt_price
    data['cobalt_price'] = data['cobalt_price'][:-2]

    # Set data.statuscode to data.statuscode.Display
    data['statuscode'] = data['statuscode']['Display']

    # Check conditions for data.publish
    if data['statuscode'] == 'Inactive' or data['cobalt_PublishtoPortal'] == 'false':
        data['publish'] = True
    elif data['statuscode'] == 'Active' and data['cobalt_PublishtoPortal'] == 'true':
        data['publish'] = False
    else:
        data['publish'] = True

    # Set data.all_day based on data.cobalt_fullday
    data['all_day'] = data['cobalt_fullday'] == 'true'

    cobalt_location_id = data['cobalt_LocationId']['Display']

    # Switch case for data.cobalt_LocationId.Display
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

    # Console.log(data.cobalt_LocationId.Display)
    # Console.log(data.cobalt_LocationId.Value)
    # print(data['cobalt_LocationId']['Display'])
    # print(data['cobalt_LocationId']['Value'])

    if len(data['cobalt_cobalt_classinstructor_cobalt_class']) > 0:
        classInstructor = [item['cobalt_name'] for item in data['cobalt_cobalt_classinstructor_cobalt_class']]
        data[
            'cobalt_Description'] = f"<p style=\"font-weight:bold;color: black;\">Instructor: {classInstructor[0]}</p" \
                                    f"><br><br>{data['cobalt_Description']}<br><input style=\"background-color: " \
                                    f"#4CAF50;border: none;color: white;padding: 15px 32px;text-align: " \
                                    f"center;text-decoration: none;display: inline-block;font-size: 16px;\" " \
                                    f"type=\"button\" value=\"Register Now\" " \
                                    f"onclick=\"window.location.href='https://miamiportal.ramcoams.net/Authentication" \
                                    f"/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx" \
                                    f"%3Fcid%3D{data['cobalt_classId']}'\" />"
    else:
        data[
            'cobalt_Description'] = f"{data['cobalt_Description']}<br><input style=\"background-color: " \
                                    f"#4CAF50;border: none;color: white;padding: 15px 32px;text-align: " \
                                    f"center;text-decoration: none;display: inline-block;font-size: 16px;\" " \
                                    f"type=\"button\" value=\"Register Now\" " \
                                    f"onclick=\"window.location.href='https://miamiportal.ramcoams.net/Authentication" \
                                    f"/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx" \
                                    f"%3Fcid%3D{data['cobalt_classId']}'\" />"

    data['cobalt_name'] = data['cobalt_name']

    with open('logs/apiData.json', 'a') as file:
        current_time = datetime.now().strftime('%I:%M:%S %p')
        file.write(f"[{current_time}] {json.dumps(data)} \n")

    def submitNewClass(data_input):
        # Check if the event already exists in the WordPress database (Check for staging or live)
        if staging == 'false':
            wp_response = requests.get(f"{os.getenv('WPEVENT_URL')}/{data_input['cobalt_classId']}",
                                       headers={
                                           'Authorization': 'Basic ' + base64.b64encode(
                                               os.getenv('WORDPRESS_CREDS').encode('utf-8')).decode('utf-8')
                                       })
        else:
            wp_response = requests.get(f"{os.getenv('STAGINGWPEVENT_URL')}/{data_input['cobalt_classId']}/",
                                       headers={
                                           'Authorization': 'Basic ' + base64.b64encode(
                                               os.getenv('WORDPRESS_CREDS').encode('utf-8')).decode('utf-8')
                                       })

        print(f"Response Status Code:{wp_response.status_code}")

        if wp_response.status_code == 200:
            # Event already exists, do not submit
            print(f"Event with class ID {data['cobalt_classId']} already exists in the WordPress database.")
            with open('logs/logs.txt', 'a') as f:
                f.write(
                    f"[{datetime.now().strftime('%I:%M:%S %p')}] Event with class ID {data['cobalt_classId']}"
                    f"already exists in the WordPress database.\n")
        else:
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
                "tags": data['cobalt_cobalt_tag_cobalt_class'],
            }

            if isinstance(location_id, (int, float)):
                ramcoClass["venue"] = data[0]['cobalt_LocationId']

            payload = urlencode(ramcoClass)

            url = config['WORDPRESS_URL']
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Basic ' + base64.b64encode(config['WORDPRESS_CREDS'].encode()).decode()
            }
            response = requests.post(url, headers=headers, data=payload)

            #body = response.json()

            print(f"Class processed: {data[0]['cobalt_name']}")

    submitNewClass(data.copy())


if __name__ == '__main__':
    push_classes()
