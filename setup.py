from setuptools import setup
import os.path

with open('README.rst') as fd:
    long_description = fd.read()
    
# There was a problem with certbot's own requirements (requirement conflicts)
# Trying to get rid of the problem by requiring some packages directly:

certbot_requirements = ["requests[security]>=2.10", "six>=1.9"]

setup(
    name='multicerti',
    version='0.0.1',
    python_requires='>=3.3',
    install_requires = certbot_requirements + ['certbot>=0.14.2', 'naval>=0.8.0', 'docopt>=0.6.2', 'pyparsing>=1.5.5'],
    packages=['multicerti'],
    scripts=['bin/multicerti'],
    author = 'Benjamin Le Forestier',
    author_email = 'benjamin@leforestier.org',
    keywords = ["letsencrypt", "certbot", "reverse proxy", "ssl", "tls", "certificate", "https"],
    description = "Obtain and renew ssl certificates for multiple domains and configure a reverse proxy for these, all in one step.",
    long_description = long_description,
    classifiers = [
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        "Topic :: Internet :: Proxy Servers",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Internet :: WWW/HTTP :: Site Management",
        "Topic :: Security :: Cryptography",
        "Operating System :: Unix"
    ]
)
