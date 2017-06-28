FROM ubuntu:16.04

MAINTAINER oayunin@gmail.com

RUN apt-get update && apt-get install -y \
    git \
    vim \
    curl \
    python-dev \
    python-pip

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

CMD sleep infinity

