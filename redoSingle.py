import requests

from pricelist import pricelist
from alerts import sendNtfyAlert
from config_loader import load_config
from logging_setup import setup_logging
from ramco_client import fetch_entity, CLASS_ATTRIBUTES
from event_processor import process_class
from wordpress_client import (
    load_reference_data, get_wp_headers, merge_wp_tags_and_categories,
    build_class_payload, submit_event_update,
)

setup_logging()

config = load_config()

pricelist()

prices, tag_search, cat_search, venue_search = load_reference_data()

guid = input("Enter GUID: ")

try:
    data = fetch_entity(config, 'cobalt_class', guid, CLASS_ATTRIBUTES)
except Exception as e:
    print(e)
    raise

try:
    process_class(data, prices, tag_search, cat_search, venue_search)
    print(data)
except Exception as e:
    sendNtfyAlert(str(e), title="RedoSingle: Error processing class")
    print(f"Error: {e}")
    raise

# Must use inline request to detect empty-body 200 (shadowrealm check)
headers = get_wp_headers(config)
slug = data['cobalt_classId']
wp_url = f"{config['WORDPRESS_URL']}/events/by-slug/{slug}"
response = requests.get(wp_url, headers=headers)

if response.status_code != 200:
    print(f"Event not found in WordPress: {slug}")
elif not response.text:
    print(f"Sending {data['cobalt_name']} to the shadowrealm")
else:
    wp_response = response.json()
    merge_wp_tags_and_categories(data, wp_response, 'cobalt_cobalt_tag_cobalt_class', 'categories')

    if wp_response.get('image') is False:
        print("No class image!")
        payload = build_class_payload(data)
    else:
        data['featuredImage'] = wp_response['image']['url']
        print(wp_response['image']['url'])
        payload = build_class_payload(data, featured_image=data['featuredImage'])

    submit_event_update(config, slug, payload)
    print(f"Class processed: {data['cobalt_name']}")
