import requests, os, json, datetime, base64, asyncio, logging
from dotenv import dotenv_values
from pricelist import pricelist, getTags, getCategories, getVenues 
from alerts import sendDiscordAlert

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
            'filename': 'logs/Meeting.log',
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

logging.config.dictConfig(logging_config)
console_logger = logging.getLogger('Console')

def newClasses():
    #import env variables
    config = dotenv_values(".env")

    # set up wordpress url if staging is true in env
    if os.environ.get('STAGING') == 'true':
        config['WORDPRESS_URL'] = config['STAGING_URL']

    #update pricelist
    pricelist()
    getTags(config['WORDPRESS_URL'])
    getCategories(config['WORDPRESS_URL'])
    getVenues(config['WORDPRESS_URL'])

    #get date minus 1 hour
    date_start = datetime.datetime.now() - datetime.timedelta(hours=1)
    date_start = date_start.strftime("%Y-%m-%dT%H:00:00")

    # #build api request
    form_data = {
        'Key': config['API_KEY'],
        'Operation': 'GetEntities',
        'Entity': 'cobalt_meeting',
        'Filter': f'createdon<ge>{date_start} AND statuscode<eq>1',
        'Attributes': 'cobalt_BeginDate,cobalt_EndDate,cobalt_meetingId,cobalt_location,cobalt_name,cobalt_description,cobalt_cobalt_tag_cobalt_meeting/cobalt_name,cobalt_fullday,cobalt_publishtoportal,statuscode,cobalt_meeting_cobalt_meetingregistrationfees/cobalt_productid,cobalt_outsideprovider,cobalt_meeting_cobalt_meetingregistrationfees/statuscode,cobalt_meeting_cobalt_meetingregistrationfees/cobalt_publishtoportal,cobalt_outsideproviderlink'
    }

    #request data from RAMCO API
    try:
        response = requests.post(config['API_URL'], data=form_data)
        body = json.loads(response.text)
    except Exception as e:
        sendDiscordAlert(f"Error: {e}")
        print(f"Error: {e}")
        return e

    if 'Data' not in body:
        print("No new meetings to process")
        exit()
    else:  
        classes = body['Data']

    #loop through classes
    def process_classes(classes):
        #
        #   load pricelist and Meeting attribute data
        #

        prices = json.load(open('./pricelist.json', 'r'))
        tagSearch = json.load(open('./tags.json', 'r'))
        catSearch = json.load(open('./categories.json', 'r'))
        venueSearch = json.load(open('./venues.json', 'r'))
        
        for obj in classes:

            #format start date
            startDate = datetime.datetime.fromtimestamp(obj['cobalt_BeginDate']['Value'])
            obj['cobalt_BeginDate']['Display'] = startDate.strftime("%Y-%m-%d %H:%M:%S")

            #format end date
            endDate = datetime.datetime.fromtimestamp(obj['cobalt_EndDate']['Value'])
            obj['cobalt_EndDate']['Display'] = endDate.strftime("%Y-%m-%d %H:%M:%S")

            if len(obj['cobalt_Meeting_Cobalt_MeetingRegistrationFees']) > 0:
                for item in obj['cobalt_Meeting_Cobalt_MeetingRegistrationFees']:
                    orderIds.append({
                        'id': item['cobalt_productid']['Value'],
                        'status': item['statuscode']['Value'],
                    })
                
                #remove order ids
                orderIds = [item for item in orderIds if item['id'] != '8d6bb524-f1d8-41ad-8c21-ae89d35d4dc3']
                orderIds = [item for item in orderIds if item['id'] != 'c3102913-ffd4-49d6-9bf6-5f0575b0b635']
                orderIds = [item for item in orderIds if item['id'] != None]
                orderIds = [item for item in orderIds if item['status'] == 1]
            else:
                orderIds = []

            #set price
            if len(orderIds) > 0:
                cost = [item for item in prices if item['ProductId'] == orderIds[0]['id']]
                #print(f"Cost: {cost}")
                if cost[0]['Price'] == None:
                    obj['cobalt_price'] = ''
                else:
                    obj['cobalt_price'] = cost[0]['Price']
            else:
                obj['cobalt_price'] = '0.0000'

            #print(f"Price: {obj['cobalt_price']}")

            #remove decimals
            if obj['cobalt_price'] != '':
                obj['cobalt_price'] = obj['cobalt_price'][:-2]

            #set price to blank if outside provider
            if obj['cobalt_OutsideProvider'] == 'true':
                obj['cobalt_price'] = ''


            #
            # Check if the tags and categories exist in wordpress
            #
            tags = []
            categories = []

            if len(obj['cobalt_cobalt_tag_cobalt_meeting']) > 0:
                for item in obj['cobalt_cobalt_tag_cobalt_meeting']:
                    resultTag = [tag['id'] for tag in tagSearch if tag['name'] == item['cobalt_name']]
                    if len(resultTag)>0:
                        tags.append(resultTag[0])
                    else:
                        sendDiscordAlert(f"Tag not found in wordpress for ***{obj['cobalt_name']}*** with id ***{obj['cobalt_meetingId']}*** : {item['cobalt_name']}")
                    resultCat = [cat['id'] for cat in catSearch if cat['name'] == item['cobalt_name']]
                    if len(resultCat)>0:
                        categories.append(resultCat[0])
                    else:
                        sendDiscordAlert(f"Category not found in wordpress for ***{obj['cobalt_name']}*** with id ***{obj['cobalt_meetingId']}*** : {item['cobalt_name']}")
            else:
                tags.append(1660)

            obj['cobalt_cobalt_tag_cobalt_meeting'] = tags
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

            cobalt_location_id = obj['cobalt_Location']

            resultVenue = [ven['id'] for ven in venueSearch if ven['name'] == cobalt_location_id]

            # print(resultVenue)
            # print(cobalt_location_id)

            #print(f"Venue found: {resultVenue}")

            if len(resultVenue) > 0:
                obj['cobalt_Location'] = resultVenue
            elif cobalt_location_id is None or cobalt_location_id == "null" or cobalt_location_id == "":
                obj['cobalt_Location'] = []
            else:
                sendDiscordAlert(f"Venue not found in wordpress for ***{obj['cobalt_name']}*** with id ***{obj['cobalt_meetingId']}*** : {cobalt_location_id}")
                obj['cobalt_LocationId'] = []


            #set outside provider link
            if obj['cobalt_OutsideProvider'] == 'true':
                obj['cobalt_Description'] = f"{obj['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='{obj['cobalt_OutsideProviderLink']}'\" />"
            else:
                obj['cobalt_Description'] = f"{obj['cobalt_Description']}<br><input style=\"background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;\" type=\"button\" value=\"Register Now\" onclick=\"window.location.href='https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FMeetingDetails.aspx%3Fmid%3D{obj['cobalt_meetingId']}'\" />"

            # if(len(obj['cobalt_cobalt_classinstructor_cobalt_class']) > 0):
            #     classInstructor = [item['cobalt_name'] for item in obj['cobalt_cobalt_classinstructor_cobalt_class']]
            #     obj['cobalt_Description'] = f"<p style=\"font-weight:bold;color: black;\">Instructor: {classInstructor[0]}</p><br><br>{obj['cobalt_Description']}"
            # else:
            #     obj['cobalt_Description'] = obj['cobalt_Description']

            #set tags
            obj['cobalt_cobalt_tag_cobalt_meeting'] = tags

            print(f"Meeting processed: {obj['cobalt_name']} - {obj['cobalt_meetingId']} - {obj['cobalt_Location']} - {obj['cobalt_price']} - {obj['cobalt_cobalt_tag_cobalt_meeting']}")

    try:
        process_classes(classes)
    except Exception as e:
        print(e)
        sendDiscordAlert(e)

    new_classes = []
    featured_classes = []
    existing_classes = []

    #check if Meeting exists
    def check_if_exists(classes):
        for obj in classes:
            response = requests.get(f"{config['WORDPRESS_URL']}/events/by-slug/{obj['cobalt_meetingId']}")

            print(f'Checking {obj['cobalt_name']} - {obj['cobalt_meetingId']} - {response.status_code}')

            if response.status_code == 200:

                response = response.json()

                response_tags = [response['id'] for response in response['tags']]
                all_tags = obj['cobalt_cobalt_tag_cobalt_meeting'] + response_tags

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

                obj['cobalt_cobalt_tag_cobalt_meeting'] = tagFix
                obj['categories'] = catFix

                if response["image"] == False:
                    #obj['cobalt_cobalt_tag_cobalt_class'] = filtered_tags
                    print("No Meeting image!")
                    existing_classes.append(obj)
                else:
                    #obj['cobalt_cobalt_tag_cobalt_class'] = filtered_tags
                    obj['featuredImage'] = response['image']['url']
                    print(response['image']['url'])
                    featured_classes.append(obj)
            else:
                new_classes.append(obj)

    #get response

    if len(classes) == 0:
        print("No new classes to process")
        exit()
    else:
        try:
            check_if_exists(classes)
        except Exception as e:
            sendDiscordAlert(e)
            print(e)

    print(f"Existing Classes: {len(existing_classes)}")
    print(f"Featured Classes: {len(featured_classes)}")
    print(f"New Classes: {len(new_classes)}")

    async def submit_new_class(data):
        print(f"Submitting new Meeting: {data['cobalt_name']} - {data['cobalt_meetingId']}")
        ramcoClass = {
                    "title": data['cobalt_name'],
                    "status": "publish",
                    "hide_from_listings": data['publish'],
                    "description": data['cobalt_Description'],
                    "all_day": data['all_day'],
                    "start_date": data['cobalt_BeginDate']['Display'],
                    "end_date": data['cobalt_EndDate']['Display'],
                    "slug": data['cobalt_meetingId'],
                    "categories": data['categories'],
                    "show_map_link": True,
                    "show_map": True,
                    "cost": data['cobalt_price'],
                    "tags": data['cobalt_cobalt_tag_cobalt_meeting']
                }
        
        if data['cobalt_Location'] != []:
            ramcoClass["venue"] = data['cobalt_Location']

        #payload = urlencode(ramco_class)
        #print(ramcoClass)
        url = f"{config['WORDPRESS_URL']}/events"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + base64.b64encode(config['WORDPRESS_CREDS'].encode()).decode()
        }

        #post data
        response = requests.post(url, headers=headers, params=ramcoClass)
        
        if response.status_code == 201:
            print(f"Meeting processed: {data['cobalt_name']}")
        else:
            print(f'Error submitting Meeting: {data['cobalt_name']} - {response.text} - {response.status_code}')
            sendDiscordAlert(f'Error submitting Meeting: {data['cobalt_name']} - {response.text} - {response.status_code}')

        #print(response)

    async def sumbit_classes(data):
        for obj in data:
            await submit_new_class(obj)

    asyncio.run(sumbit_classes(new_classes))

try:
    newClasses()
except Exception as e:
    print(e)
    sendDiscordAlert(str(e))
