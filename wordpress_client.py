import base64
import json
import requests
from urllib.parse import urlencode

from alerts import sendDiscordAlert


def load_reference_data():
    """Load the four local JSON reference files.

    Returns:
        (prices, tag_search, cat_search, venue_search) tuple of lists.
    """
    prices = json.load(open('./pricelist.json', 'r'))
    tag_search = json.load(open('./tags.json', 'r'))
    cat_search = json.load(open('./categories.json', 'r'))
    venue_search = json.load(open('./venues.json', 'r'))
    return prices, tag_search, cat_search, venue_search


def get_wp_headers(config, content_type='application/x-www-form-urlencoded'):
    """Return WordPress REST API request headers with Basic Auth."""
    return {
        'Content-Type': content_type,
        'Authorization': 'Basic ' + base64.b64encode(
            config['WORDPRESS_CREDS'].encode()
        ).decode(),
    }


def check_event_exists(config, slug):
    """Check whether a WordPress event exists by slug.

    Returns:
        The parsed JSON response dict if the event exists (HTTP 200), else None.
    """
    response = requests.get(f"{config['WORDPRESS_URL']}/events/by-slug/{slug}")
    if response.status_code == 200 and response.text:
        return response.json()
    return None


def merge_wp_tags_and_categories(obj, wp_response, tag_key, cat_key):
    """Merge existing WordPress tag/category IDs into the obj and set sticky/featured.

    Updates obj[tag_key], obj[cat_key], obj['sticky'], and obj['featured'] in-place.
    Tags and categories are stored as comma-separated ID strings (no trailing comma).
    """
    wp_tag_ids = [t['id'] for t in wp_response.get('tags', [])]
    all_tags = list(set(obj[tag_key] + wp_tag_ids))

    wp_cat_ids = [c['id'] for c in wp_response.get('categories', [])]
    all_cats = list(set(obj[cat_key] + wp_cat_ids))

    obj['sticky'] = wp_response['sticky']
    obj['featured'] = wp_response['featured']
    obj[tag_key] = ','.join(str(t) for t in all_tags)
    obj[cat_key] = ','.join(str(c) for c in all_cats)


def build_class_payload(data, featured_image=None):
    """Build the WordPress event payload dict for a class.

    Args:
        data: Processed class object (output of event_processor.process_class).
        featured_image: Optional image URL to include in the payload.

    Returns:
        Dict suitable for use as query params or URL-encoded form data.
    """
    payload = {
        'title': data['cobalt_name'],
        'status': 'publish',
        'hide_from_listings': data['publish'],
        'description': data['cobalt_Description'],
        'all_day': data['all_day'],
        'start_date': data['cobalt_ClassBeginDate']['Display'],
        'end_date': data['cobalt_ClassEndDate']['Display'],
        'slug': data['cobalt_classId'],
        'categories': data['categories'],
        'show_map_link': True,
        'show_map': True,
        'cost': data['cobalt_price'],
        'tags': data['cobalt_cobalt_tag_cobalt_class'],
        'featured': data.get('featured'),
        'sticky': data.get('sticky'),
    }
    if data['cobalt_LocationId']:
        payload['venue'] = data['cobalt_LocationId']
    if featured_image:
        payload['image'] = featured_image
    return payload


def build_meeting_payload(data, featured_image=None):
    """Build the WordPress event payload dict for a meeting.

    Args:
        data: Processed meeting object (output of event_processor.process_meeting).
        featured_image: Optional image URL to include in the payload.

    Returns:
        Dict suitable for use as query params or URL-encoded form data.
    """
    payload = {
        'title': data['cobalt_name'],
        'status': 'publish',
        'hide_from_listings': data['publish'],
        'description': data['cobalt_Description'],
        'all_day': data['all_day'],
        'start_date': data['cobalt_BeginDate']['Display'],
        'end_date': data['cobalt_EndDate']['Display'],
        'slug': data['cobalt_meetingId'],
        'categories': data['categories'],
        'show_map_link': True,
        'show_map': True,
        'cost': data['cobalt_price'],
        'tags': data['cobalt_cobalt_tag_cobalt_meeting'],
        'featured': data.get('featured'),
        'sticky': data.get('sticky'),
    }
    if data['cobalt_Location']:
        payload['venue'] = data['cobalt_Location']
    if featured_image:
        payload['image'] = featured_image
    return payload


def submit_event_update(config, slug, payload):
    """POST an event update to the WordPress by-slug endpoint.

    Uses query params for non-image updates and URL-encoded body for image updates
    (image uploads require the payload to be sent as form data).

    Returns:
        The requests.Response object.
    """
    url = f"{config['WORDPRESS_URL']}/events/by-slug/{slug}"
    headers = get_wp_headers(config)

    if payload.get('image'):
        response = requests.post(url, headers=headers, data=urlencode(payload))
    else:
        response = requests.post(url, headers=headers, params=payload)
    return response


def submit_event_create(config, payload):
    """POST a new event to the WordPress events endpoint.

    Returns:
        The requests.Response object.
    """
    url = f"{config['WORDPRESS_URL']}/events"
    headers = get_wp_headers(config, content_type='application/json')
    response = requests.post(url, headers=headers, params=payload)
    return response
