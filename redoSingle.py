import requests
import json
import datetime
import pytz
from dotenv import dotenv_values

#import env variables
config = dotenv_values(".env")

#set timezone
timezone = pytz.timezone('US/Eastern')


#request guid from user
# guid = input("Class GUID: ")

# Get the data from the API
payload = {
    'Key': config['API_KEY'],
    'Operation': 'GetEntity',
    'Entity': 'cobalt_class',
    'Guid': '4D008EFA-640C-EE11-9DF5-00155D10107E',
    'Attributes': 'cobalt_classbegindate,cobalt_classenddate,cobalt_classid,cobalt_locationid,cobalt_name,cobalt_description,cobalt_locationid,cobalt_cobalt_tag_cobalt_class/cobalt_name,cobalt_fullday,cobalt_publishtoportal,statuscode,cobalt_cobalt_classinstructor_cobalt_class/cobalt_name,cobalt_cobalt_class_cobalt_classregistrationfee/cobalt_productid,cobalt_cobalt_class_cobalt_classregistrationfee/statuscode,cobalt_outsideprovider,cobalt_outsideproviderlink'
}

#request data from RAMCO API
r = requests.post(config['API_URL'], data=payload)

# Parse the data
data = json.loads(r.text)
data = data['Data']

data['cobalt_ClassBeginDate']['Display'] = datetime.datetime.fromtimestamp(data['cobalt_ClassBeginDate']['Value'])

data['cobalt_ClassEndDate']['Display'] = datetime.datetime.fromtimestamp(data['cobalt_ClassEndDate']
['Value'])

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


