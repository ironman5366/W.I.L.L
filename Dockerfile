FROM python:3
MAINTAINER Will Beddow
ADD . /W.I.L.L
# This fixes a bug with the default installation of openssl
RUN echo "deb http://httpredir.debian.org/debian/ jessie-backports main" >> /etc/apt/sources.list && \
  apt update && apt install -y -t jessie-backports openssl
RUN pip3 install -r W.I.L.L/requirements.txt
RUN python3 -m spacy download en
EXPOSE 8000
WORKDIR /W.I.L.L
CMD ["gunicorn", "app:api"]