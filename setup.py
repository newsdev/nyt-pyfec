import os.path

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


setup(
    name='nyt-pyfec',
    version='0.0.8',
    author='Jeremy Bowers',
    author_email='jeremy.bowers@nytimes.com',
    url='https://github.com/newsdev/nyt-pyfec',
    description="Python client for parsing campaign finance data from the Federal Election Commission's web site.",
    long_description=read('README.rst'),
    packages=['pyfec'],
    package_dir={'pyfec': 'pyfec'},
    package_data={'pyfec': ['fec-csv-sources/*.csv']},
    license="Apache License 2.0",
    keywords='FEC election finance campaign data parsing scraping donation expenditure candidate committee',
    install_requires=['python-dateutil==2.4.2','requests==2.7.0','six==1.9.0','wheel==0.24.0','colorama==0.3.3','humanize==0.5.1'],
    classifiers=['Development Status :: 3 - Alpha',
                 'Intended Audience :: Developers',
                 'Programming Language :: Python',
                 'Topic :: Software Development :: Libraries :: Python Modules']
)
