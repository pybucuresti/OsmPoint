from setuptools import setup, find_packages

setup(
    name="OsmPoint",
    packages=find_packages(),
    install_requires=['flask', 'flask-sqlalchemy'],
    entry_points={'console_scripts': ['osm_point = osm_point:main']},
)
