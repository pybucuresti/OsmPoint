from setuptools import setup, find_packages

setup(
    name="OsmPoint",
    packages=find_packages(),
    install_requires=[
        'Flask >= 0.7',
        'flask-sqlalchemy',
        'flask-openid',
        'flask-actions',
        'WTForms',
        'py',
        'pytest', # not sure why this is needed
        'PyYAML',
        'imposm.parser',
    ],
    entry_points={'console_scripts': ['osmpoint = osmpoint.manage:main',
                                      'parser = pbf_parser:main']},
)

# Also required for development: 'unittest2', 'mock', 'OsmApi.py' (from
# http://svn.openstreetmap.org/applications/utils/python_lib/OsmApi/OsmApi.py).
# Deploying can be done with 'fabric'.
# imposm.parser needs build-essential, python-dev, protobuf-compiler and
# libprotobuf-dev.
