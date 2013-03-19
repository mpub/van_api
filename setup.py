import os
import sys
from setuptools import setup, find_packages

_here = os.path.dirname(__file__)

f = open(os.path.join(_here, 'README.txt'), 'r')
README = f.read()
f.close()

install_requires = []

if sys.version_info[:2] == (2, 5):
    install_requires.append('simplejson')
if sys.version_info[:2] == (2, 4):
    install_requires.append('simplejson < 1.9999')

tests_require = [
        'mock'
        ]

testing_extra = tests_require + [
        'coverage'
        ]

setup(name="van_api",
      version="1.2",
      description="Utilities to ease access to the Vanguardistas APIs from python.",
      py_modules=['van_api'],
      long_description=README,
      license='BSD',
      author="Vanguardistas LLC",
      author_email='brian@vanguardistas.net',
      install_requires=install_requires,
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Intended Audience :: Developers",
          "Operating System :: OS Independent",
          "License :: OSI Approved :: BSD License",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.5",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.2",
          "Programming Language :: Python :: 3.3",
          ],
      extras_require = {
          'testing':testing_extra,
          },
      test_suite='tests',
      tests_require=tests_require,
      )
