import requests
import json
from dotenv import dotenv_values


config = dotenv_values(".env")

# Get the data from the API
payload = {
    'Key': config['API_KEY'],
    'Operation': 'GetEntities',
    'Entity': 'product',
    'Filter': 'producttypecode<eq>4 OR producttypecode<eq>2',
    'Attributes': 'productid,name,price,producttypecode'
}

r = requests.post(config['API_URL'], data=payload)

# Parse the data
data = json.loads(r.text)
data = data['Data']

print(data)

# Save the data to a file
with open('pricelist.json', 'w') as f:
    f.write(json.dumps(data))
