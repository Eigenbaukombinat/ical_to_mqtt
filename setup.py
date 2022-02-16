#!/usr/bin/env python3
from setuptools import setup

version = "0.1"

setup(
    name="ical_to_mqtt",
    packages=["ical_to_mqtt"],
    install_requires=[
        "icalevents @ git+ssh://git@github.com/dhavlik/icalevents.git@master#egg=icalevents",
        "paho-mqtt"
    ],
    version=version,
    description="Creates mqtt messages from ical alarms.",
    author="nilo",
    url="https://github.com/Eigenbaukombinat/ical_to_mqtt",
    keywords=["iCal"],
    entry_points={
        "console_scripts": [
            "ical2mqtt = ical_to_mqtt:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    long_description="""\
Create mqtt messages from ical alarms.
--------------------------------------

for Details see https://github.com/Eigenbaukombinat/ical_to_mqtt

""",
)
