from setuptools import setup
import json


with open('metadata.json', encoding='utf-8') as fp:
    metadata = json.load(fp)


setup(
    name='lexibank_liljegrenhindukush',
    description=metadata['title'],
    license=metadata.get('license', ''),
    url=metadata.get('url', ''),
    py_modules=['lexibank_liljegrenhindukush'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'lexibank.dataset': [
            'liljegrenhindukush=lexibank_liljegrenhindukush:Dataset',
        ],
        'cldfbench.commands': [
            'liljegrenhindukush=liljegrenhindukushcommands',
        ],
    },
    install_requires=[
        'html5lib',
        'pycldf>=1.25',
        'cdstarcat>=1.3',
        'cldfbench>=1.2.3',
        'pylexibank>=2.7.1',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
