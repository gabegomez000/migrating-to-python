import asyncio
import datetime

from pricelist import pricelist, getTags, getCategories, getVenues
from alerts import sendDiscordAlert
from config_loader import load_config
from ramco_client import fetch_entities, CLASS_ATTRIBUTES
from event_processor import process_class
from wordpress_client import (
    load_reference_data, check_event_exists, merge_wp_tags_and_categories,
    build_class_payload, submit_event_update,
)


def incremental():
    config = load_config()

    pricelist()
    getTags(config['WORDPRESS_URL'])
    getCategories(config['WORDPRESS_URL'])
    getVenues(config['WORDPRESS_URL'])

    date_start = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00")

    try:
        classes = fetch_entities(config, 'cobalt_class', f'modifiedon<ge>{date_start}', CLASS_ATTRIBUTES)
    except Exception as e:
        print(e)
        sendDiscordAlert(e)
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
        sendDiscordAlert(e)

    existing_classes = []
    featured_classes = []
    new_classes = []
    class_shadowrealm = []

    def check_if_exists(classes):
        for obj in classes:
            if obj['ramcosub_calendar_override'] == 'false':
                print(f"Checking {obj['cobalt_name']} - {obj['cobalt_classId']}")
                wp_response = check_event_exists(config, obj['cobalt_classId'])

                if wp_response is not None:
                    merge_wp_tags_and_categories(
                        obj, wp_response, 'cobalt_cobalt_tag_cobalt_class', 'categories'
                    )
                    if wp_response.get('image') is False:
                        print("No class image!")
                        existing_classes.append(obj)
                    else:
                        obj['featuredImage'] = wp_response['image']['url']
                        print(wp_response['image']['url'])
                        featured_classes.append(obj)
                else:
                    new_classes.append(obj)
            else:
                print(f"Sending {obj['cobalt_name']} - {obj['cobalt_classId']} to the shadowrealm")
                class_shadowrealm.append(obj)

    try:
        check_if_exists(classes)
    except Exception as e:
        sendDiscordAlert(e)
        print(e)

    print(f"Existing Classes: {len(existing_classes)}")
    print(f"Featured Classes: {len(featured_classes)}")
    print(f"New Classes: {len(new_classes)}")
    print(f"Shadowrealm Classes: {len(class_shadowrealm)}")

    async def submit_existing_class(data):
        print(f"Submitting existing class: {data['cobalt_classId']} - {data['cobalt_name']}")
        payload = build_class_payload(data)
        submit_event_update(config, data['cobalt_classId'], payload)
        print(f"Class processed: {data['cobalt_name']}")

    async def submit_featured_class(data):
        print(f"Submitting featured class: {data['cobalt_classId']}")
        payload = build_class_payload(data, featured_image=data['featuredImage'])
        submit_event_update(config, data['cobalt_classId'], payload)
        print(f"Featured class processed: {data['cobalt_name']}")

    async def submit_all(items, submit_fn):
        for obj in items:
            await submit_fn(obj)

    asyncio.run(submit_all(existing_classes, submit_existing_class))
    asyncio.run(submit_all(featured_classes, submit_featured_class))


try:
    incremental()
except Exception as e:
    sendDiscordAlert(e)
    print(e)
