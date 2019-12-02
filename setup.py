from os import chdir, pardir, path

from setuptools import find_packages, setup

README = open(path.join(path.dirname(__file__), "README.rst")).read()

# allow setup.py to be run from any path
chdir(path.normpath(path.join(path.abspath(__file__), pardir)))

setup(
    name="django-request-profiler",
    version="0.15",
    packages=find_packages(),
    install_requires=["Django>=2.0,<4.0"],
    include_package_data=True,
    description="Django Request Profiler - a simple profiler for timing HTTP requests.",
    long_description=README,
    url="https://github.com/yunojuno/django-request-profiler",
    author="YunoJuno",
    author_email="code@yunojuno.com",
    maintainer="YunoJuno",
    maintainer_email="code@yunojuno.com",
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 2.0",
        "Framework :: Django :: 2.1",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.0",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
)
