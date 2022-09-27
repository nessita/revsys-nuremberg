FROM python:3.8

RUN mkdir /nuremberg
WORKDIR /nuremberg

ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_SRC=/usr/local/src

# Get Node 10 instead of version in APT repository.
# Downloads an installation script, which ends by running
# apt-get update: no need to re-run at this layer
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash - \
    && apt-get install -y nodejs npm \
    && npm install -g less

COPY requirements.txt ./requirements.txt
COPY nuremberg/core/tests/requirements.txt ./test-requirements.txt
RUN pip install -U pip
    && pip install -r requirements.txt -r test-requirements.txt \
    && rm requirements.txt \
    && rm test-requirements.txt
