import textwrap

import setuptools


setuptools.setup(
    name='novastats',
    version='0.1',
    url='https://github.com/Semyazz/nova-stats.git',
    license='',
    author='Semyazz',
    author_email='semyazz@gmail.com',
    description='',
    packages=setuptools.find_packages(exclude=['bin']),
    include_package_data=True,
    scripts=['bin/health-monitor'],
)



#from setuptools import setup
#
#
#setup(
#    name='novastats',
#    version='',
#    url='',
#    license='',
#    author='semy',
#    author_email='',
#    description='',
#    packages=['novastats', 'novastats.algorithms'],
#    include_package_data=True,
#)
