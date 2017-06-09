#!/usr/bin/env bash
pip install -r ../requirements.txt
python -m spacy donwload en
docker build -t willassistant/core:"$1" .