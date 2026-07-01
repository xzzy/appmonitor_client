from setuptools import setup

setup(name='appmonitor_client',
      version='2.0',
      description='App Monitor Client',
      url='https://github.com/dbca-wa/appmonitor_client',
      author='Department of Biodiversity, Conservation and Attractions',
      author_email='asi@dbca.wa.gov.au',
      license='BSD',
      packages=['appmonitor_client','appmonitor_client.management','appmonitor_client.management.commands',
                ],
      install_requires=[],
      include_package_data=True,
      zip_safe=False)
