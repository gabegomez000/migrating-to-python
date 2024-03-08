import requests, json, datetime, base64, os
from urllib.parse import urlencode
from dotenv import dotenv_values
from pricelist import pricelist, getTags, getCategories, getVenues
from alerts import sendDiscordAlert

#import env variables
config = dotenv_values(".env")

def redoSingleModule(guid, staging):

    # set up wordpress url if staging is true in env
    if staging == 'true':
        config['WORDPRESS_URL'] = config['STAGING_URL']
        print(f"Set Staging URL: {config['WORDPRESS_URL']}")

    #update pricelist
    pricelist()
    getTags(config['WORDPRESS_URL'])
    getCategories(config['WORDPRESS_URL'])
    getVenues(config['WORDPRESS_URL'])

    prices = json.load(open('./pricelist.json', 'r'))
    tagSearch = json.load(open('./tags.json', 'r'))
    catSearch = json.load(open('./categories.json', 'r'))
    venueSearch = json.load(open('./venues.json', 'r'))

    # Get the data from the API
    payload = {
        'Key': config['API_KEY'],
        'Operation': 'GetEntity',
        'Entity': 'cobalt_class',
        'Guid': guid,
        'Attributes': 'cobalt_classbegindate,cobalt_classenddate,cobalt_classid,cobalt_locationid,cobalt_name,cobalt_description,cobalt_locationid,cobalt_cobalt_tag_cobalt_class/cobalt_name,cobalt_fullday,cobalt_publishtoportal,statuscode,cobalt_cobalt_classinstructor_cobalt_class/cobalt_name,cobalt_cobalt_class_cobalt_classregistrationfee/cobalt_productid,cobalt_cobalt_class_cobalt_classregistrationfee/statuscode,cobalt_outsideprovider,cobalt_outsideproviderlink,ramcosub_calendar_override'
    }

    #request data from RAMCO API
    try:
        r = requests.post(config['API_URL'], data=payload)
    except Exception as e:
        sendDiscordAlert(f"Error: {e}")
        print(f"Error: {e}")
        return e

    # Parse the data
    data = json.loads(r.text)
    obj = data['Data']

    def processClass(obj):
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

        #
        # Check if the tags and categories exist in wordpress
        #

        tags = []
        categories = []

        if len(obj['cobalt_cobalt_tag_cobalt_class']) > 0:
            for item in obj['cobalt_cobalt_tag_cobalt_class']:
                resultTag = [tag['id'] for tag in tagSearch if tag['name'] == item['cobalt_name']]
                if len(resultTag)>0:
                    tags.append(resultTag[0])
                else:
                    print(f"Tag not found in wordpress for ***{obj['cobalt_name']}*** with id ***{obj['cobalt_classId']}*** : {item['cobalt_name']}")
                resultCat = [cat['id'] for cat in catSearch if cat['name'] == item['cobalt_name']]
                if len(resultCat)>0:
                    categories.append(resultCat[0])
                else:
                    print(f"Category not found in wordpress for ***{obj['cobalt_name']}*** with id ***{obj['cobalt_classId']}*** : {item['cobalt_name']}")
        else:
            tags.append(1660)

        obj['cobalt_cobalt_tag_cobalt_class'] = tags
        obj['categories'] = categories

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

        #
        # Check if the venue exists in wordpress and set the location id
        #

        cobalt_location_id = obj['cobalt_LocationId']['Display'] 

        resultVenue = [ven['id'] for ven in venueSearch if ven['name'] == cobalt_location_id]

        # print(resultVenue)
        # print(cobalt_location_id)

        if len(resultVenue) > 0:
            obj['cobalt_LocationId'] = resultVenue
        elif cobalt_location_id is None or cobalt_location_id == "null" or cobalt_location_id == "":
            obj['cobalt_LocationId'] = []
        else:
            print(f"Venue not found in wordpress for ***{obj['cobalt_name']}*** with id ***{obj['cobalt_classId']}*** : {cobalt_location_id}")
            obj['cobalt_LocationId'] = []

        #
        # Set syling for the class based on location
        #

        location_mapping = {
            "MIAMI HQ": "#798e2d",
            "West Broward - Sawgrass Office": "#0082c9",
            "Coral Gables Office": "#633e81",
            "JTHS MIAMI Training Room (Jupiter)": "#005962",
            "Northwestern Dade": "#9e182f",
            "Northwestern Dade Office": "#9e182f",
            "NE Broward Office-Ft. Lauderdale": "#f26722",
            "Aventura Office": "#000000",
            "null": "",
        }

        default_style = ""  # Default style value

        style = location_mapping.get(cobalt_location_id, default_style)

        if isinstance(obj['cobalt_LocationId'], (int, float)):
            obj['cobalt_name'] = f"<span style=\"color:{style};\">{obj['cobalt_name']}</span>"
        else:
            obj['cobalt_name'] = obj['cobalt_name']


        #set outside provider link
        if obj['cobalt_OutsideProvider'] == 'true':
            obj['cobalt_Description'] = f"{obj['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='{obj['cobalt_OutsideProviderLink']}'\" />"
        else:
            obj['cobalt_Description'] = f"{obj['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx%3Fcid%3D{obj['cobalt_classId']}'\" />"

        if(len(obj['cobalt_cobalt_classinstructor_cobalt_class']) > 0):
            classInstructor = [item['cobalt_name'] for item in obj['cobalt_cobalt_classinstructor_cobalt_class']]
            obj['cobalt_Description'] = f"<p style=\"font-weight:bold;color: black;\">Instructor: {classInstructor[0]}</p><br><br>{obj['cobalt_Description']}"
        else:
            obj['cobalt_Description'] = obj['cobalt_Description']

        #set tags
        obj['cobalt_cobalt_tag_cobalt_class'] = tags

        print(f"Class processed: {obj['cobalt_name']} - {obj['cobalt_classId']} - {obj['cobalt_LocationId']} - {obj['cobalt_price']} - {obj['cobalt_cobalt_tag_cobalt_class']}")

    try:
        processClass(obj)
    except Exception as e:
        sendDiscordAlert(f"Error: {e}")
        print(f"Error: {e}")
        return e

    featured_classes = []
    existing_classes = []
    new_classes = []
    class_shadowrealm=[]

    def check_if_exists(obj):
        if obj['ramcosub_calendar_override'] == 'false':
            response = requests.get(f"{config['WORDPRESS_URL']}/events/by-slug/{obj['cobalt_classId']}")

            print(f"Checking {obj['cobalt_name']} - {obj['cobalt_classId']} - {response.status_code}")

            if response.status_code == 200:

                response = response.json()

                response_tags = [response['id'] for response in response['tags']]
                all_tags = obj['cobalt_cobalt_tag_cobalt_class'] + response_tags

                response_categories = [response['id'] for response in response['categories']]
                all_categories = obj['categories'] + response_categories

                #print(all_tags)

                obj['sticky']= response['sticky']
                obj['featured']= response['featured']

                #print(f'Checking {obj['cobalt_name']} - {response['url']}')
                filtered_tags = list(set(all_tags))
                filtered_categories = list(set(all_categories))

                tagFix = ""
                catFix = ""

                for tag in filtered_tags:
                    tagFix += f"{tag},"
                tagFix = tagFix[:-1]
                for cat in filtered_categories:
                    catFix += f"{cat},"
                catFix = catFix[:-1]

                obj['cobalt_cobalt_tag_cobalt_class'] = tagFix
                obj['categories'] = catFix

                if response["image"] == False:
                    #obj['cobalt_cobalt_tag_cobalt_class'] = filtered_tags
                    print("No class image!")
                    existing_classes.append(obj)
                else:
                    #obj['cobalt_cobalt_tag_cobalt_class'] = filtered_tags
                    obj['featuredImage'] = response['image']['url']
                    print(response['image']['url'])
                    featured_classes.append(obj)
            else:
                new_classes.append(obj)
        else:
            print(f"Sending {obj['cobalt_name']} - {obj['cobalt_classId']} to the shadowrealm")
            class_shadowrealm.append(obj)

    try:
        check_if_exists(obj)
    except Exception as e:
        sendDiscordAlert(f"Error: {e}")
        print(f"Error: {e}")
        return e

    print(f'Featured: {len(featured_classes)} Existing: {len(existing_classes)} New: {len(new_classes)} Shadowrealm: {len(class_shadowrealm)}' )

    #print(f'Featured: {featured_classes} Existing: {existing_classes}' )

    def modify_existing_class(data):
        #print(data)

        print(f"Submitting existing class: {data[0]['cobalt_classId']} - {data[0]['cobalt_LocationId']} - {data[0]['cobalt_name']} - {data[0]['cobalt_price']} - {data[0]['cobalt_cobalt_tag_cobalt_class']}")

        ramco_class = {
            "title": data[0]['cobalt_name'],
            "status": "publish",
            "hide_from_listings": data[0]['publish'],
            "description": data[0]['cobalt_Description'],
            "all_day": data[0]['all_day'],
            "start_date": data[0]['cobalt_ClassBeginDate']['Display'],
            "end_date": data[0]['cobalt_ClassEndDate']['Display'],
            "slug": data[0]['cobalt_classId'],
            "categories": data[0]['categories'],
            "show_map_link": True,
            "show_map": True,
            "cost": data[0]['cobalt_price'],
            "tags": data[0]['cobalt_cobalt_tag_cobalt_class'],
            "featured": data[0]['featured'],
            "sticky": data[0]['sticky']
        }

        print(ramco_class)

        if data[0]['cobalt_LocationId'] != []:
            ramco_class["venue"] = data[0]['cobalt_LocationId']

        #payload = urlencode(ramco_class)
        print(ramco_class)
        url = f"{config['WORDPRESS_URL']}/events/by-slug/{data[0]['cobalt_classId']}"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic ' + base64.b64encode(config['WORDPRESS_CREDS'].encode()).decode()
        }
        response = requests.post(url, headers=headers, params=ramco_class)
        body = response.json()
        print(body)
        print(f"Class processed: {data[0]['cobalt_name']}")
        return f"Class processed: {data[0]['cobalt_name']}"

    def modify_featured_class(data):
        #print(data)
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
            "categories": data[0]['categories'],
            "show_map_link": True,
            "show_map": True,
            "cost": data[0]['cobalt_price'],
            "tags": data[0]['cobalt_cobalt_tag_cobalt_class'],
            "featured": data[0]['featured'],
            "sticky": data[0]['sticky']
        }

        if data[0]['cobalt_LocationId'] != []:
            ramco_class["venue"] = data[0]['cobalt_LocationId']

        #payload = urlencode(ramco_class)

        url = f"{config['WORDPRESS_URL']}/events/by-slug/{data[0]['cobalt_classId']}"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic ' + base64.b64encode(config['WORDPRESS_CREDS'].encode()).decode()
        }
        response = requests.post(url, headers=headers, params=ramco_class)

        body = response.json()

        print(body)
        print(f"Class processed: {data[0]['cobalt_name']}")
        return f"Class processed: {data[0]['cobalt_name']}"

    if len(existing_classes) > 0:
        try:
            response = modify_existing_class(existing_classes)
            return response
        except Exception as e:
            print(f"Error: {e}")
            sendDiscordAlert(f"Error: {e}")
            return e
    elif len(featured_classes) > 0:
        try:
            response = modify_featured_class(featured_classes)
            return response
        except Exception as e:
            print(f"Error: {e}")
            sendDiscordAlert(f"Error: {e}")
            return e