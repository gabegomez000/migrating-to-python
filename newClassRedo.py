import asyncio
import datetime

from logging_setup import setup_logging
from pricelist import pricelist, getTags, getCategories, getVenues
from alerts import sendNtfyAlert
from config_loader import load_config
from ramco_client import fetch_entities, CLASS_ATTRIBUTES
from event_processor import process_class
from wordpress_client import (
    load_reference_data, build_class_payload, submit_event_create, check_event_exists,
)

setup_logging('logs/newClasses.log')

config = load_config()

pricelist()
getTags(config['WORDPRESS_URL'])
getCategories(config['WORDPRESS_URL'])
getVenues(config['WORDPRESS_URL'])

date_start = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:00:00")

try:
    classes = fetch_entities(
        config, 'cobalt_class',
        f'cobalt_classbegindate<ge>{date_start}',
        CLASS_ATTRIBUTES,
    )
except Exception as e:
    print(e)
    sendNtfyAlert(str(e), title="NewClassRedo: Error fetching new classes")
    raise

prices, tag_search, cat_search, venue_search = load_reference_data()

try:
    for obj in classes:
        print(f"Processing: {obj['cobalt_name']} - {obj['cobalt_classId']}")
        process_class(obj, prices, tag_search, cat_search, venue_search)
except Exception as e:
    print(e)
    sendNtfyAlert(str(e), title="NewClassRedo: Error processing classes")

new_classes = [obj for obj in classes if obj['ramcosub_calendar_override'] == 'false']

print(f"New Classes: {len(new_classes)}")


async def submit_new_class(data):
    if check_event_exists(config, data['cobalt_classId']):
        print(f"Skipping (already exists): {data['cobalt_name']} - {data['cobalt_classId']}")
        return False
    print(f"Submitting new class: {data['cobalt_classId']} - {data['cobalt_name']}")
    payload = build_class_payload(data)
    response = submit_event_create(config, payload)
    if response.status_code == 201:
        print(f"Class processed: {data['cobalt_name']}")
        return True
    else:
        msg = f"Error submitting class: {data['cobalt_name']} - {response.text} - {response.status_code}"
        print(msg)
        sendNtfyAlert(msg, title="NewClassRedo: Error submitting class")
        return False


async def submit_all():
    submitted = 0
    for obj in new_classes:
        if await submit_new_class(obj):
            submitted += 1
    # summary count of successful submissions, distinct from skipped/failed
    print(f"Submitted {submitted} of {len(new_classes)} new classes")


asyncio.run(submit_all())
