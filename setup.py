from setuptools import setup, find_packages

setup(
    name="OsmPoint",
    packages=find_packages(),
    install_requires=[
        'Flask >= 0.7',
        'flask-sqlalchemy',
        'flask-openid',
        'WTForms',
        'py',
    ],
    entry_points={'console_scripts': ['osm_point = osm_point:main']},
)
