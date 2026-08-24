import asyncio
import datetime

from pricelist import pricelist, getTags, getCategories, getVenues
from alerts import sendNtfyAlert
from config_loader import load_config
from ramco_client import fetch_entities, CLASS_ATTRIBUTES
from event_processor import process_class
from wordpress_client import (
    load_reference_data, build_class_payload, submit_event_create, check_event_exists,
)


def newClasses():
    config = load_config()

    pricelist()
    getTags(config['WORDPRESS_URL'])
    getCategories(config['WORDPRESS_URL'])
    getVenues(config['WORDPRESS_URL'])

    date_start = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00")

    try:
        classes = fetch_entities(
            config, 'cobalt_class',
            f'createdon<ge>{date_start} AND statuscode<eq>1',
            CLASS_ATTRIBUTES,
        )
    except Exception as e:
        print(e)
        sendNtfyAlert(str(e), title="NewClasses: Error fetching new classes")
        return

    if not classes:
        print("No new classes to process")
        return

    prices, tag_search, cat_search, venue_search = load_reference_data()

    try:
        for obj in classes:
            print(f"Processing: {obj['cobalt_name']} - {obj['cobalt_classId']}")
            process_class(obj, prices, tag_search, cat_search, venue_search)
    except Exception as e:
        print(e)
        sendNtfyAlert(str(e), title="NewClasses: Error processing classes")

    new_classes = [obj for obj in classes if obj['ramcosub_calendar_override'] == 'false']

    print(f"New Classes: {len(new_classes)}")

    async def submit_new_class(data):
        if check_event_exists(config, data['cobalt_classId']):
            print(f"Skipping (already exists): {data['cobalt_name']} - {data['cobalt_classId']}")
            return
        payload = build_class_payload(data)
        response = submit_event_create(config, payload)
        if response.status_code == 201:
            print(f"Class processed: {data['cobalt_name']}")
        else:
            msg = f"Error submitting class: {data['cobalt_name']} - {response.text} - {response.status_code}"
            print(msg)
            sendNtfyAlert(msg, title="Error submitting class")

    async def submit_all(items):
        for obj in items:
            await submit_new_class(obj)

    asyncio.run(submit_all(new_classes))


try:
    newClasses()
except Exception as e:
    sendNtfyAlert(str(e), title="NewClasses: Unhandled Error")
    print(e)
