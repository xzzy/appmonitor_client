from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import requests, json, os 
import platform
import django
import importlib.metadata
import decouple
import subprocess
import sys
import getpass

class Command(BaseCommand):
    help = 'Provide system platform information to appmonitor.'

    def handle(self, *args, **options):
        VERSION="1.8"
        print (settings.BASE_DIR)
        print ("Running appmonitor check sync with version {}".format(VERSION))
        platform_obj = {"system_info": {}, "debian_packages": {},"linux_system": {"linux_username": "", "linux_uid": None}}

        platform_obj["linux_system"]["linux_uid"] = os.getuid()
        platform_obj["linux_system"]["linux_username"] = getpass.getuser()

        APP_MONITOR_URL=decouple.config("APP_MONITOR_URL", default="")
        APP_MONITOR_PLATFORM_ID=decouple.config("APP_MONITOR_PLATFORM_ID", default="")
        APP_MONITOR_APIKEY=decouple.config("APP_MONITOR_APIKEY", default="")
        APP_MONITOR_AUTH_ENABLED=decouple.config("APP_MONITOR_AUTH_ENABLED", default="False")
        APP_MONITOR_AUTH_USER=decouple.config("APP_MONITOR_AUTH_USER", default="")
        APP_MONITOR_AUTH_PASS=decouple.config("APP_MONITOR_AUTH_PASS", default="")
        IMAGE_TAG=decouple.config("IMAGE_TAG", default="")
        IMAGE_NAME=decouple.config("IMAGE_NAME", default="") 

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

            # get debian packages
            debian_packages=subprocess.check_output(["dpkg-query", "--show", "--showformat=${Package}-!-${Version}-!-${Architecture}\n"])
            debian_packages_decoded = debian_packages.decode()            
            debian_packages_lines = debian_packages_decoded.splitlines()
            platform_debian_packages_array = []
            for dp in debian_packages_lines:
                dp_split = dp.split("-!-")
                row = {}
                row['package_name'] = dp_split[0]
                row['package_version'] = dp_split[1]
                row['package_architecture'] = dp_split[2]
                platform_debian_packages_array.append(row)

            platform_obj["debian_packages"] = platform_debian_packages_array

            # Find NodeJS packages if installed
            platform_npm_package_versions = []
            for file_path in self.scan_dir(settings.BASE_DIR, {'__pycache__', '.git', 'private-media','media','cache','session_store', 'db'}):
                if "package-lock.json" in file_path:                                        
                    platform_npm_package_versions = self.extract_versions_from_package_lock(file_path,platform_npm_package_versions)                            
            platform_obj["npm_packages"] = platform_npm_package_versions
            
            url = APP_MONITOR_URL+'/api/update-platform-information/'
            myobj = {'APP_MONITOR_PLATFORM_ID': APP_MONITOR_PLATFORM_ID, 'APP_MONITOR_APIKEY': APP_MONITOR_APIKEY, 'IMAGE_TAG' : IMAGE_TAG, 'IMAGE_NAME': IMAGE_NAME, 'platform_obj': platform_obj}       

            if APP_MONITOR_AUTH_ENABLED == 'True':
                auth_request = requests.auth.HTTPBasicAuth(APP_MONITOR_AUTH_USER, APP_MONITOR_AUTH_PASS)
                resp = requests.post(url, json = myobj, auth=auth_request)
            else:
                resp = requests.post(url, json = myobj)
                print (resp)
            print (resp.text)
        else:
            print ("Please provide a APP_MONITOR_URL environment variable.")


    def scan_dir(self,path, excluded_dirs):
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name not in excluded_dirs:
                        yield from self.scan_dir(entry.path, excluded_dirs)
                elif entry.is_file():
                    yield entry.path




    def extract_versions_from_package_lock(self,filepath="package-lock.json",versions=[]):
        """
        Extracts a list of package names and their versions from a package-lock.json file.

        Args:
            filepath (str): The path to the package-lock.json file.

        Returns:
            list: A list of dictionaries, where each dictionary contains 'name' and 'version'
                for a package. Returns an empty list if the file is not found or invalid.
        """
        print ("Extracting NPM versions from {}".format(filepath))
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # The structure of package-lock.json can vary slightly with lockfileVersion.
            # For lockfileVersion 2 and 3, 'packages' is the main key.
            # For lockfileVersion 1, 'dependencies' is the main key.
            if 'packages' in data:
                for package_path, details in data['packages'].items():
                    if package_path:  # Exclude the root project entry
                        package_name = package_path.split('node_modules/')[-1]
                        if 'version' in details:
                            versions.append({'name': package_name, 'version': details['version'], 'source_file': filepath})
            elif 'dependencies' in data: # For older lockfileVersion 1
                for package_name, details in data['dependencies'].items():
                    if 'version' in details:
                        versions.append({'name': package_name, 'version': details['version'], 'source_file': filepath})

        except FileNotFoundError:
            print(f"Error: The file '{filepath}' was not found.")
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{filepath}'. Ensure it's a valid JSON file.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        return versions
