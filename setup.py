"""aws-stackermods setup"""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='aws-stackermods',
    version='0.0.1.',
    description='Collection of stacker blueprint modules',
    long_description=long_description,
    url='https://github.com/ashleygould/aws-stackermods',
    author='Ashley Gould',
    author_email='agould@ucop.edu',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='aws stacker troposphere cloudformation',
    packages=find_packages(exclude=['scratch', 'notes']),
    install_requires=['botocore', 'docopt', 'stacker', 'troposphere'],
    package_data={
        'awsorgs': [
            'conf/*.yml',
        ],
    },
    entry_points={
        'console_scripts': [
            'stackermods=stackermods.modhelp:main',
        ],
    },

)

