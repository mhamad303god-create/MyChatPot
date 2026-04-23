import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.sites.models import Site

def update_site_domain():
    # Update the default site to point to localhost:8000
    # This is crucial for Google/Facebook redirects to match the development server
    site = Site.objects.get(id=1)
    site.domain = '127.0.0.1:8000'
    site.name = 'Local Development'
    site.save()
    print(f"Updated Site ID {site.id} to domain: {site.domain}")

if __name__ == '__main__':
    update_site_domain()
