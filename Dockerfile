# Dockerfile for bonsai-common unit tests
FROM python:3.6.9-slim

RUN pip3 install -U \
    setuptools \
    aiohttp \
    pytest \
    pytest-cov \
    coverage

COPY microsoft_bonsai_api*.whl ./
RUN pip3 install microsoft_bonsai_api*

COPY bonsai-common/ bonsai-common
RUN pip3 install -e bonsai-common/

WORKDIR bonsai-common/

CMD ["pytest", \
    "--junit-xml", \
    "test-results/junit-linux-bonsai3-py.xml", \
    "--junit-prefix", \
    "src.sdk3.bonsai-common",\
    "--cov"]
