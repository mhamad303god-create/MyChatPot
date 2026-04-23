import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

def create_social_apps():
    # Ensure Site exists
    site, created = Site.objects.get_or_create(id=1, defaults={'domain': 'example.com', 'name': 'example.com'})
    
    # Google
    google_app, created = SocialApp.objects.get_or_create(
        provider='google',
        defaults={
            'name': 'Google',
            'client_id': 'PLACEHOLDER_CLIENT_ID',
            'secret': 'PLACEHOLDER_SECRET',
        }
    )
    google_app.sites.add(site)
    if created:
        print("Created Google SocialApp")
    else:
        print("Google SocialApp already exists")

    # Facebook
    facebook_app, created = SocialApp.objects.get_or_create(
        provider='facebook',
        defaults={
            'name': 'Facebook',
            'client_id': 'PLACEHOLDER_CLIENT_ID',
            'secret': 'PLACEHOLDER_SECRET',
        }
    )
    facebook_app.sites.add(site)
    if created:
        print("Created Facebook SocialApp")
    else:
        print("Facebook SocialApp already exists")

if __name__ == '__main__':
    create_social_apps()
