########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from setuptools import setup

setup(
    name='plugin-tests-framework',
    version='1.6.3',
    author='Gigaspaces',
    author_email='cosmo-admin@gigaspaces.com',
    packages=['cloudify_tester', 'cloudify_tester.helpers',
              'cloudify_tester.commands', 'cloudify_tester.steps'],
    license='LICENSE',
    description='Cloudify plugin tests framework',
    install_requires=[
        'PyYAML==3.10',
        'Jinja2==2.7.2',
        'click==6.6',
    ],
    entry_points={
        'console_scripts': [
            'cloudify_tester = '
            'cloudify_tester.commands.base:cloudify_tester',
        ],
    },
    package_data={'cloudify_tester': ['schemas/*.yaml']},
    # pytest-bdd failed to find steps when zipped
    zip_safe=False,
)
