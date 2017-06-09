FROM python:3
MAINTAINER Will Beddow
ADD . /W.I.L.L
RUN pip3 install -r W.I.L.L/requirements.txt
RUN python3 -m spacy download en
EXPOSE 80
WORKDIR /W.I.L.L
CMD ["gunicorn", "app:api"]