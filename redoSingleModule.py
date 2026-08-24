import traceback
import requests
from pricelist import pricelist, getTags, getCategories, getVenues
from alerts import sendNtfyAlert
from config_loader import load_config
from ramco_client import fetch_entity, CLASS_ATTRIBUTES
from event_processor import process_class
from wordpress_client import (
    load_reference_data, merge_wp_tags_and_categories,
    build_class_payload, submit_event_update,
)


def redoSingleModule(guid, staging):
    config = load_config(staging)

    pricelist()
    getTags(config['WORDPRESS_URL'])
    getCategories(config['WORDPRESS_URL'])
    getVenues(config['WORDPRESS_URL'])

    prices, tag_search, cat_search, venue_search = load_reference_data()

    try:
        obj = fetch_entity(config, 'cobalt_class', guid, CLASS_ATTRIBUTES)
    except Exception as e:
        return e

    try:
        process_class(obj, prices, tag_search, cat_search, venue_search)
    except Exception as e:
        sendNtfyAlert(str(e), title="RedoSingleModule: Error processing class")
        print(f"Error [Class Formatting]: {e}")
        return e

    featured_classes = []
    existing_classes = []
    new_classes = []
    class_shadowrealm = []

    def check_if_exists(obj):
        if obj['ramcosub_calendar_override'] == 'false':
            response = requests.get(f"{config['WORDPRESS_URL']}/events/by-slug/{obj['cobalt_classId']}")
            print(f"Checking {obj['cobalt_name']} - {obj['cobalt_classId']} - {response.status_code}")

            if response.status_code == 200:
                if not response.text:
                    print(f"Sending {obj['cobalt_name']} - {obj['cobalt_classId']} to the shadowrealm")
                    class_shadowrealm.append(obj)
                    return

                wp_response = response.json()
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
        check_if_exists(obj)
    except Exception as err:
        sendNtfyAlert(str(err), title="RedoSingleModule: Error checking if class exists")
        print(f"Error [Check if Exists]: {err=}, {type(err)=}")
        traceback.print_exc()
        return err

    print(f'Featured: {len(featured_classes)} Existing: {len(existing_classes)} New: {len(new_classes)} Shadowrealm: {len(class_shadowrealm)}')

    def modify_existing_class(data):
        print(f"Submitting existing class: {data[0]['cobalt_classId']} - {data[0]['cobalt_LocationId']} - {data[0]['cobalt_name']} - {data[0]['cobalt_price']} - {data[0]['cobalt_cobalt_tag_cobalt_class']}")
        payload = build_class_payload(data[0])
        print(f"Payload: {payload}")
        submit_event_update(config, data[0]['cobalt_classId'], payload)
        print(f"Class processed: {data[0]['cobalt_name']}")
        return f"Class processed: {data[0]['cobalt_name']}"

    def modify_featured_class(data):
        payload = build_class_payload(data[0], featured_image=data[0]['featuredImage'])
        submit_event_update(config, data[0]['cobalt_classId'], payload)
        print(f"Class processed: {data[0]['cobalt_name']}")
        return f"Class processed: {data[0]['cobalt_name']}"

    if len(existing_classes) > 0:
        try:
            return modify_existing_class(existing_classes)
        except Exception as e:
            print(f"Error [Existing Push]: {e}")
            sendNtfyAlert(str(e), title="RedoSingleModule: Error pushing existing class")
            return e
    elif len(featured_classes) > 0:
        try:
            return modify_featured_class(featured_classes)
        except Exception as e:
            print(f"Error [Featured Push]: {e}")
            sendNtfyAlert(str(e), title="RedoSingleModule: Error pushing featured class")
            return e