import os.path

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


setup(
    name='nyt-pyfec',
    version='0.0.1',
    author='Jeremy Bowers',
    author_email='jeremy.bowers@nytimes.com',
    url='https://github.com/newsdev/nyt-pyfec',
    description='Python client for parsing campaign finance data from the Federal Election Commission\'s web site.',
    long_description=read('README.rst'),
    packages=['pyfec'],
    license="Apache License 2.0",
    keywords='FEC election finance campaign data parsing scraping donation expenditure candidate committee',
    install_requires=['lxml==3.4.4','psycopg2==2.6.1','python-dateutil==2.4.2','requests==2.7.0','six==1.9.0','wheel==0.24.0'],
    classifiers=['Development Status :: 4 - Beta',
                 'Intended Audience :: Developers',
                 'Programming Language :: Python',
                 'Topic :: Software Development :: Libraries :: Python Modules']
)
