import requests
import json
from dotenv import dotenv_values
import logging.config

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

def pricelist():

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

    # print(data)

    # Save the data to a file
    with open('pricelist.json', 'w') as f:
        f.write(json.dumps(data))

def getTags(url):

    headers = {
        'accept': 'application/json',
    }

    params = {
        'per_page': '1000',
    }

    url = url + '/tags'

    r = requests.get(
        url,
        params=params,
        headers=headers,
    )

    data = r.json()

    if 'total_pages' in data:
        for i in range(2, data['total_pages'] + 1):
            params['page'] = i
            r = requests.get(
                url,
                params=params,
                headers=headers,
            )
            print(f'Adding page {i} of {data["total_pages"]} tags to the list.')
            data['tags'].extend(r.json()['tags'])

    tagsLite = []

    for tag in data['tags']:
        tagsLite.append({
            'id': tag['id'],
            'name': tag['name'],
            'slug': tag['slug']
        })
            
    tagsLite.append({
        'id': 1714,
        'name': 'Effective Communication for Real Estate Professionals  - Livestream',
        'slug': 'Effective Communication for Real Estate Professionals  - Livestream'
    })

    tagsLite.append({
        'id': 1719,
        'name': 'Stop Working for Free - IN-Person',
        'slug': 'Stop Working for Free - IN-Person'
    })

    #print(data)

    #Save the data to a file
    with open('tags.json', 'w') as f:
        f.write(json.dumps(tagsLite))

def getCategories(url):
    headers = {
        'accept': 'application/json',
    }

    params = {
        'per_page': '1000',
    }

    url = url + '/categories'

    r = requests.get(
        url,
        params=params,
        headers=headers,
    )

    data = r.json()

    if 'total_pages' in data:
        for i in range(2, data['total_pages'] + 1):
            params['page'] = i
            r = requests.get(
                url,
                params=params,
                headers=headers,
            )
            print(f'Adding page {i} of {data["total_pages"]} categories to the list.')
            data['categories'].extend(r.json()['categories'])

    categoriesLite = []

    for category in data['categories']:
        categoriesLite.append({
            'id': category['id'],
            'name': category['name'],
            'slug': category['slug']
        })

    categoriesLite.append({
        'id': 90,
        'name': 'NE Broward - Fort Lauderdale Office',
        'slug': 'NE Broward - Fort Lauderdale Office'
    })

    categoriesLite.append({
        'id': 1713,
        'name': 'Effective Communication for Real Estate Professionals  - Livestream',
        'slug': 'Effective Communication for Real Estate Professionals  - Livestream'
    })

    categoriesLite.append({
        'id': 1720,
        'name': 'Stop Working for Free - IN-Person',
        'slug': 'Stop Working for Free - IN-Person'
    })

    # print(data)

    # Save the data to a file
    with open('categories.json', 'w') as f:
        f.write(json.dumps(categoriesLite))

def getVenues(url):
    headers = {
        'accept': 'application/json',
    }

    params = {
        'per_page': '1000',
    }

    url= url + '/venues'

    r = requests.get(
        url,
        params=params,
        headers=headers,
    )

    data = r.json()

    if 'total_pages' in data:
        for i in range(2, data['total_pages'] + 1):
            params['page'] = i
            r = requests.get(
                url,
                params=params,
                headers=headers,
            )
            print(f'Adding page {i} of {data["total_pages"]} venues to the list.')
            data['venues'].extend(r.json()['venues'])

    venuesLite = []

    for venue in data['venues']:
        venuesLite.append({
            'id': venue['id'],
            'name': venue['venue'],
            'slug': venue['slug']
        })
    
    venuesLite.append({
        'id': 120675,
        'name': 'Aventura Office Computer Lab',
        'slug': 'Aventura Office Computer Lab'
    })

    venuesLite.append({
        'id': 4702,
        'name': 'NE Broward Office Ft. Lauderdale',
        'slug': 'NE Broward Office Ft. Lauderdale'
    })

    # print(data)

    # Save the data to a file
    with open('venues.json', 'w') as f:
        f.write(json.dumps(venuesLite))             