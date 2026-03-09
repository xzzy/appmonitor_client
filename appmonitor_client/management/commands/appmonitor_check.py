from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import requests, json, os 
import platform
import django
import importlib.metadata
import decouple
import sys

class Command(BaseCommand):
    help = 'Provide system platform information to appmonitor.'

    def handle(self, *args, **options):
        platform_obj = {"system_info": {}}
        APP_MONITOR_URL=decouple.config("APP_MONITOR_URL", default="")
        APP_MONITOR_PLATFORM_ID=decouple.config("APP_MONITOR_PLATFORM_ID", default="")
        APP_MONITOR_APIKEY=decouple.config("APP_MONITOR_APIKEY", default="")
        APP_MONITOR_AUTH_ENABLED=decouple.config("APP_MONITOR_AUTH_ENABLED", default="False")
        APP_MONITOR_AUTH_USER=decouple.config("APP_MONITOR_AUTH_USER", default="")
        APP_MONITOR_AUTH_PASS=decouple.config("APP_MONITOR_AUTH_PASS", default="")

        if len(APP_MONITOR_URL) > 0:

            # Retreive Operating System Information
            system_os_file = '/etc/os-release'
            if os.path.isfile(system_os_file) is True:
                f = open(system_os_file, "r")
                platform_string = f.read()
                platform_lines = platform_string.splitlines()
                for pl in platform_lines:
                    pl_line = pl.split("=")
                    pl_key = pl_line[0]
                    pl_value = pl_line[1]
                    quotes_check = pl_value[0]+pl_value[-1]
                    pl_value_cleaned = ""
                    if quotes_check == '""':
                        pl_line_length = len(pl_line[1]) - 1
                        pl_value_cleaned = pl_line[1][1:pl_line_length]
                    else:
                        pass
                        pl_value_cleaned = pl_value

                    platform_obj["system_info"][pl_key] = pl_value_cleaned

            # Python Version        
            platform_obj["system_info"]["python_version"] = platform.python_version()
            
            # Django Version
            platform_obj["system_info"]["django_version"] = django.get_version()

            # Build a list of installed python packages
            installed_packages_list = sorted([
                "%s==%s" % (dist.metadata["Name"], dist.metadata["Version"])
                for dist in importlib.metadata.distributions()
            ])
            platform_obj["python_packages"] = installed_packages_list

            url = APP_MONITOR_URL+'/api/update-platform-information/'
            myobj = {'APP_MONITOR_PLATFORM_ID': APP_MONITOR_PLATFORM_ID, 'APP_MONITOR_APIKEY': APP_MONITOR_APIKEY, 'platform_obj': platform_obj}       

            if APP_MONITOR_AUTH_ENABLED == 'True':
                auth_request = requests.auth.HTTPBasicAuth(APP_MONITOR_AUTH_USER, APP_MONITOR_AUTH_PASS)
                resp = requests.post(url, json = myobj, auth=auth_request)
            else:
                resp = requests.post(url, json = myobj)

            print (resp.text)
        else:
            print ("Please provide a APP_MONITOR_URL environment variable.")