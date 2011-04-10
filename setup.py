from setuptools import setup, find_packages

setup(
    name="OsmPoint",
    packages=find_packages(),
    install_requires=[
        'Flask',
        'flask-sqlalchemy',
        'flask-openid',
    ],
    entry_points={'console_scripts': ['osm_point = osm_point:main']},
)
