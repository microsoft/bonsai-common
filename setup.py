import logging
from setuptools import setup, find_packages

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.debug("Running setup...")

setup(
    name="bonsai-common",
    version="1.0.3",
    description="Simulator interface library for Bonsai AI platform v3",
    long_description=open("README.md").read(),
    url="https://bons.ai",
    author="Microsoft, Inc.",
    author_email="opensource@bons.ai",
    license="BSD",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.8",
        "Natural Language :: English",
    ],
    keywords="bonsai",
    install_requires=[
        "jsons<1.7",
        "microsoft-bonsai-api==0.1.4",
        "numpy>=1.22,<1.24",
    ],
    python_requires=">=3.8",
    packages=find_packages(),
)
