import datetime

# Order IDs that should always be excluded from price lookups
_EXCLUDED_ORDER_IDS = {
    '8d6bb524-f1d8-41ad-8c21-ae89d35d4dc3',
    'c3102913-ffd4-49d6-9bf6-5f0575b0b635',
}

# Venue ID → hex color
LOCATION_COLOR_MAP = {
    127640: '#798e2d',
    123527: '#798e2d',
    123525: '#798e2d',
    123523: '#798e2d',
    4694:   '#798e2d',
    120695: '#f26722',
    120675: '#121212',
    22099:  '#121212',
    78282:  '#005962',
    4718:   '#005962',
    4735:   '#9e182f',
    4720:   '#9e182f',
    4698:   '#0082c9',
}

_CLASS_REGISTRATION_BASE = (
    "https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx"
    "?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx%3Fcid%3D"
)

_RWORLD_CLASS_REGISTRATION_BASE = (
    "https://miamiportal.ramcoams.net/Login.aspx"
    "?ReturnUrl=%2fEducation%2fRegistration%2fDetails.aspx%3fcid%3d"
)


_MEETING_REGISTRATION_BASE = (
    "https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx"
    "?ReturnUrl=%2FEducation%2FRegistration%2FMeetingDetails.aspx%3Fmid%3D"
)

_RWORLD_MEETING_REGISTRATION_BASE = (
    "https://miamiportal.ramcoams.net/Login.aspx"
    "?ReturnUrl=%2fEducation%2fRegistration%2fMeetingDetails.aspx%3fmid%3d"
)

_BUTTON_STYLE = (
    "background-color: #4CAF50;border: none;color: white;padding: 15px 32px; margin-top: 10px;"
    "text-align: center;text-decoration: none;display: inline-block;font-size: 16px;"
)

_RWORLD_BUTTON_STYLE = (
    "background-color: #31C4B8;border: none;color: white;padding: 15px 32px; margin-top: 10px;"
    "text-align: center;text-decoration: none;display: inline-block;font-size: 16px;"
)


def _register_button(url, style, button_text="Register Now"):
    return (
        f'<br><input style="{style}" type="button" value="{button_text}" '
        f"onclick=\"window.location.href='{url}'\" />"
    )


def _resolve_price(fees, prices):
    """Return a formatted price string from a list of registration fee items."""
    order_ids = [
        {'id': item['cobalt_productid']['Value'], 'status': item['statuscode']['Value']}
        for item in fees
    ]
    order_ids = [
        i for i in order_ids
        if i['id'] not in _EXCLUDED_ORDER_IDS and i['id'] is not None and i['status'] == 1
    ]

    if not order_ids:
        return '0.00'

    match = [item for item in prices if item['ProductId'] == order_ids[0]['id']]
    print(f"Cost: {match}")
    if not match or match[0]['Price'] is None:
        return ''

    price = match[0]['Price']

    if isinstance(price, (int, float)):
        price = str(int(price))
    elif isinstance(price, str) and price != '':
        price = price[:-2]  # e.g. "10.0000" → "10.00"
    return price


def _resolve_tags_and_categories(raw_tags, tag_search, cat_search, name, entity_id):
    """Look up WordPress tag/category IDs for the given RAMCO tag names."""
    tags = []
    categories = []
    for item in raw_tags:
        result_tag = [t['id'] for t in tag_search if t['name'] == item['cobalt_name']]
        if result_tag:
            tags.append(result_tag[0])
        else:
            print(f"Tag not found in wordpress for ***{name}*** with id ***{entity_id}*** : {item['cobalt_name']}")

        result_cat = [c['id'] for c in cat_search if c['name'] == item['cobalt_name']]
        if result_cat:
            categories.append(result_cat[0])
        else:
            print(f"Category not found in wordpress for ***{name}*** with id ***{entity_id}*** : {item['cobalt_name']}")

    return tags, categories


def _resolve_venue(location_display, venue_search, name, entity_id):
    """Return a list containing the matching WordPress venue ID, or []."""
    result = [v['id'] for v in venue_search if v['name'] == location_display]
    if result:
        return result
    if not location_display or location_display in ('null', ''):
        return []
    print(f"Venue not found in wordpress for ***{name}*** with id ***{entity_id}*** : {location_display}")
    return []


def _apply_location_color(obj, location_ids):
    """Set obj['color'] and wrap cobalt_name in a colored span if applicable."""
    loc_id = None
    if location_ids:
        try:
            loc_id = int(location_ids[0])
        except (ValueError, TypeError):
            loc_id = location_ids[0]

    color = LOCATION_COLOR_MAP.get(loc_id)
    obj['color'] = color
    if color:
        obj['cobalt_name'] = f'<span style="color:{color};">{obj["cobalt_name"]}</span>'


def process_class(obj, prices, tag_search, cat_search, venue_search):
    """Process and enrich a raw RAMCO class object in-place.

    Mutates obj to add/normalise: dates, price, tags, categories, publish flag,
    all_day flag, venue ID, color, and description (register button + instructor).
    """
    # Dates
    obj['cobalt_ClassBeginDate']['Display'] = datetime.datetime.fromtimestamp(
        obj['cobalt_ClassBeginDate']['Value']
    ).strftime("%Y-%m-%d %H:%M:%S")
    obj['cobalt_ClassEndDate']['Display'] = datetime.datetime.fromtimestamp(
        obj['cobalt_ClassEndDate']['Value']
    ).strftime("%Y-%m-%d %H:%M:%S")

    # Price
    fees = obj.get('cobalt_cobalt_class_cobalt_classregistrationfee', [])
    obj['cobalt_price'] = _resolve_price(fees, prices)
    if obj.get('cobalt_OutsideProvider') == 'true':
        obj['cobalt_price'] = ''
    print(f"Price: {obj['cobalt_price']}")

    # Tags and categories
    raw_tags = obj.get('cobalt_cobalt_tag_cobalt_class', [])
    if raw_tags:
        tags, categories = _resolve_tags_and_categories(
            raw_tags, tag_search, cat_search, obj['cobalt_name'], obj['cobalt_classId']
        )
    else:
        tags, categories = [1660], []
    obj['cobalt_cobalt_tag_cobalt_class'] = tags
    obj['categories'] = categories

    # Status / publish
    obj['statuscode'] = obj['statuscode']['Display']
    if obj['statuscode'] == 'Inactive' or obj.get('cobalt_PublishtoPortal') == 'false':
        obj['publish'] = True
    elif obj['statuscode'] == 'Active' and obj.get('cobalt_PublishtoPortal') == 'true':
        obj['publish'] = False
    else:
        obj['publish'] = True

    # All day
    obj['all_day'] = obj.get('cobalt_fullday') == 'true'

    # Venue
    location_id_field = obj.get('cobalt_LocationId')
    location_display = location_id_field['Display'] if isinstance(location_id_field, dict) else ''
    obj['cobalt_LocationId'] = _resolve_venue(
        location_display, venue_search, obj['cobalt_name'], obj['cobalt_classId']
    )
    print(obj['cobalt_LocationId'])

    # Color
    _apply_location_color(obj, obj['cobalt_LocationId'])
    print(f"Color: {obj.get('color', 'No color set')}")

    # Description — register button
    if obj.get('cobalt_OutsideProvider') == 'true':
        reg_url = obj.get('cobalt_OutsideProviderLink', '')
        rworld_url = obj.get('cobalt_OutsideProviderLink', '')
    else:
        reg_url = _CLASS_REGISTRATION_BASE + obj['cobalt_classId']
        rworld_url = _RWORLD_CLASS_REGISTRATION_BASE + obj['cobalt_classId']
    obj['cobalt_Description'] = (obj.get('cobalt_Description') or '') + _register_button(reg_url, _BUTTON_STYLE, button_text="MIAMI Register Now")
    obj['cobalt_Description'] += _register_button(rworld_url, _RWORLD_BUTTON_STYLE, button_text="R-World Register Now")

    # Description — instructor prefix
    instructors = obj.get('cobalt_cobalt_classinstructor_cobalt_class', [])
    if instructors:
        instructor_name = instructors[0]['cobalt_name']
        obj['cobalt_Description'] = (
            f'<p style="font-weight:bold;color: black;">Instructor: {instructor_name}</p>'
            f'<br><br>{obj["cobalt_Description"]}'
        )

    print(
        f"Class processed: {obj['cobalt_name']} - {obj['cobalt_classId']} - "
        f"{obj['cobalt_LocationId']} - {obj['cobalt_price']} - "
        f"{obj['cobalt_cobalt_tag_cobalt_class']}"
    )
    return obj


def process_meeting(obj, prices, tag_search, cat_search, venue_search):
    """Process and enrich a raw RAMCO meeting object in-place.

    Mutates obj to add/normalise: dates, price, tags, categories, publish flag,
    all_day flag, venue ID, and description (register button).
    """
    # Dates
    obj['cobalt_BeginDate']['Display'] = datetime.datetime.fromtimestamp(
        obj['cobalt_BeginDate']['Value']
    ).strftime("%Y-%m-%d %H:%M:%S")
    obj['cobalt_EndDate']['Display'] = datetime.datetime.fromtimestamp(
        obj['cobalt_EndDate']['Value']
    ).strftime("%Y-%m-%d %H:%M:%S")

    # Price
    fees = obj.get('cobalt_Meeting_Cobalt_MeetingRegistrationFees', [])
    obj['cobalt_price'] = _resolve_price(fees, prices)
    if obj.get('cobalt_OutsideProvider') == 'true':
        obj['cobalt_price'] = ''
    print(f"Price: {obj['cobalt_price']}")

    # Tags and categories
    raw_tags = obj.get('cobalt_cobalt_tag_cobalt_meeting', [])
    if raw_tags:
        tags, categories = _resolve_tags_and_categories(
            raw_tags, tag_search, cat_search, obj['cobalt_name'], obj['cobalt_meetingId']
        )
    else:
        tags, categories = [1660], []
    obj['cobalt_cobalt_tag_cobalt_meeting'] = tags
    obj['categories'] = categories

    # Status / publish
    obj['statuscode'] = obj['statuscode']['Display']
    if obj['statuscode'] == 'Inactive' or obj.get('cobalt_PublishtoPortal') == 'false':
        obj['publish'] = True
    elif obj['statuscode'] == 'Active' and obj.get('cobalt_PublishtoPortal') == 'true':
        obj['publish'] = False
    else:
        obj['publish'] = True

    # All day (field name varies between datasets)
    full_day_val = obj.get('cobalt_FullDay') or obj.get('cobalt_fullday', 'false')
    obj['all_day'] = full_day_val == 'true'

    # Venue (meetings store location as a plain string, not a nested dict)
    location_display = obj.get('cobalt_Location', '')
    obj['cobalt_Location'] = _resolve_venue(
        location_display, venue_search, obj['cobalt_name'], obj['cobalt_meetingId']
    )

    # Description — register button
    if obj.get('cobalt_OutsideProvider') == 'true':
        reg_url = obj.get('cobalt_OutsideProviderLink', '')
        rworld_url = obj.get('cobalt_OutsideProviderLink', '')
    else:
        reg_url = _MEETING_REGISTRATION_BASE + obj['cobalt_meetingId']
        rworld_url = _RWORLD_MEETING_REGISTRATION_BASE + obj['cobalt_meetingId']
    obj['cobalt_Description'] = (obj.get('cobalt_Description') or '') + _register_button(reg_url, _BUTTON_STYLE, button_text="MIAMI Register Now")
    obj['cobalt_Description'] += _register_button(rworld_url, _RWORLD_BUTTON_STYLE, button_text="R-World Register Now")

    print(
        f"Meeting processed: {obj['cobalt_name']} - {obj['cobalt_meetingId']} - "
        f"{obj['cobalt_Location']} - {obj['cobalt_price']} - "
        f"{obj['cobalt_cobalt_tag_cobalt_meeting']}"
    )
    return obj
