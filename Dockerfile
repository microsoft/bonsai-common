# Dockerfile for bonsai-common unit tests
FROM python:3.8-slim

RUN pip3 install -U \
    setuptools \
    aiohttp \
    pytest \
    pytest-cov \
    coverage

COPY . bonsai-common
RUN pip3 install -e bonsai-common/

WORKDIR bonsai-common/

CMD ["pytest", \
    "--junit-xml", \
    "test-results/junit-linux-bonsai3-py.xml", \
    "--junit-prefix", \
    "src.sdk3.bonsai-common",\
    "--cov"]
