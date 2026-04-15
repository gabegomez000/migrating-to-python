import os
from dotenv import dotenv_values


def load_config(staging=None):
    """Load .env config and apply staging URL override.

    Args:
        staging: True to force staging, False to force live, None to read the
                 STAGING environment variable (used by cron/batch scripts).
    """
    config = dotenv_values(".env")

    use_staging = staging if staging is not None else (os.environ.get('STAGING') == 'true')

    if use_staging:
        config['WORDPRESS_URL'] = config['STAGING_URL']
        print(f"Set Staging URL: {config['WORDPRESS_URL']}")
    else:
        print(f"Set Live URL: {config['WORDPRESS_URL']}")

    return config
