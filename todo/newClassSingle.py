import requests
import json
from datetime import datetime, timedelta
import pytz
from prompt_toolkit import prompt
import os
import base64


def push_classes():
    with open('logs/logs.txt', 'a') as log_file:
        log_file.write(f"[{datetime.now().strftime('%I:%M:%S %p')}] RAMCO to WordPress Sync started.\n")

    class_guid = prompt('Class GUID: ')

    date_start = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    print(date_start)

    api_url = os.environ['API_URL']
    api_key = os.environ['API_KEY']

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
        print(data['cobalt_classid'])
        print(cost)
        data['cobalt_price'] = cost or '0.0000'
    else:
        data['cobalt_price'] = '0.0000'

    data['cobalt_price'] = data['cobalt_price'] if data['cobalt_price'] else '0.0000'

    if len(data['cobalt_cobalt_tag_cobalt_class']) > 0:
        data['cobalt_cobalt_tag_cobalt_class'] = ', '.join([tag['cobalt_name'] for tag in data['cobalt_cobalt_tag_cobalt_class']])
    else:
        data['cobalt_cobalt_tag_cobalt_class'] = ''

    instructor = data['cobalt_cobalt_classinstructor_cobalt_class'][0]['cobalt_name'] if len(data['cobalt_cobalt_classinstructor_cobalt_class']) > 0 else ''

    # Console.log(data.cobalt_price)
    # Console.log(`-------`)
    print(data['cobalt_price'])

    # Remove the last two characters from data.cobalt_price
    data['cobalt_price'] = data['cobalt_price'][:-2]

    # Create a list of tags
    tags = [data['cobalt_name'] for data in data['cobalt_cobalt_tag_cobalt_class']]

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

    # Switch case for data.cobalt_LocationId.Display
    location_id = data['cobalt_LocationId']['Display']
    if location_id == "MIAMI HQ":
        data['cobalt_name'] = f"<span style='color:#798e2d;'>{data['cobalt_name']}</span>"
        data['locationId'] = 4694
    elif location_id == "West Broward - Sawgrass Office":
        data['cobalt_name'] = f"<span style='color:#0082c9;'>{data['cobalt_name']}</span>"
        data['locationId'] = 4698
    elif location_id == "Coral Gables Office":
        data['cobalt_name'] = f"<span style='color:#633e81;'>{data['cobalt_name']}</span>"
        data['locationId'] = 4696
    elif location_id == "JTHS - MIAMI Training Room (Jupiter)":
        data['cobalt_name'] = f"<span style='color:#005962;'>{data['cobalt_name']}</span>"
        data['locationId'] = 4718
    elif location_id == "Northwestern Dade":
        data['cobalt_name'] = f"<span style='color:#9e182f;'>{data['cobalt_name']}</span>"
        data['locationId'] = 4735
    elif location_id == "Northwestern Dade Office":
        data['cobalt_name'] = f"<span style='color:#9e182f;'>{data['cobalt_name']}</span>"
        data['locationId'] = 4735
    elif location_id == "NE Broward Office-Ft. Lauderdale":
        data['cobalt_name'] = f"<span style='color:#f26722;'>{data['cobalt_name']}</span>"
        data['locationId'] = 4702
    elif location_id == "Aventura Office":
        data['cobalt_name'] = f"<span style='color:#000000;'>{data['cobalt_name']}</span>"
        data['locationId'] = 22099
    else:
        data['cobalt_name'] = data['cobalt_name']

    # Console.log(data.cobalt_LocationId.Display)
    # Console.log(data.cobalt_LocationId.Value)
    print(data['cobalt_LocationId']['Display'])
    print(data['cobalt_LocationId']['Value'])

    if len(data['cobalt_cobalt_classinstructor_cobalt_class']) > 0:
        classInstructor = [item['cobalt_name'] for item in data['cobalt_cobalt_classinstructor_cobalt_class']]
        data[
            'cobalt_Description'] = f"<p style=\"font-weight:bold;color: black;\">Instructor: {classInstructor[0]}</p><br><br>{data['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx%3Fcid%3D{data['cobalt_classId']}'\" />"
    else:
        data[
            'cobalt_Description'] = f"{data['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx%3Fcid%3D{data['cobalt_classId']}'\" />"

    data['cobalt_name'] = data['cobalt_name']

    data['cobalt_cobalt_tag_cobalt_class'] = tags

    with open('logs/apiData.json', 'a') as file:
        current_time = datetime.now().strftime('%I:%M:%S %p')
        file.write(f"[{current_time}] {json.dumps(data)} \n")


    data = form_data    # print(data)

    existingClasses = []
    newClasses = []

    with open('logs/logs.txt', 'a') as f:
        f.write(
            f"[{datetime.now().strftime('%I:%M:%S %p')}] Total classes found: {len(data)} with {len(newClasses)} new classes and {len(existingClasses)} existing classes\n")

    print(f"Found {len(newClasses)} new classes. Discarding {len(existingClasses)} existing classes.")

    with open('logs/logs.txt', 'a') as f:
        f.write(f"Found {len(newClasses)} new classes. Discarding {len(existingClasses)} existing classes.\n")

    newClasses = []

    newClasses.append(data)

    def submitNewClass(data):
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
            "venue": {
                "id": data['locationId']
            }
        }

        response = requests.post(os.environ['WORDPRESS_URL'], headers={
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + base64.b64encode(os.environ['WORDPRESS_CREDS'].encode('utf-8')).decode('utf-8')
        }, json=ramcoClass)

        body = response.json()
        with open('logs/results.json', 'a') as f:
            f.write(f"[{datetime.now().strftime('%I:%M:%S %p')}] {json.dumps(body)}\n")

        print(f"Class processed: {data['cobalt_name']}\n")
        with open('logs/logs.txt', 'a') as f:
            f.write(f"[{datetime.now().strftime('%I:%M:%S %p')}] Class processed: {data['cobalt_name']}\n")

    submitNewClass(data)

if __name__ == '__main__':
    push_classes()
