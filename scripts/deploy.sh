#!/usr/bin/env bash
coverage combine .coveragec
codecov
docker login -u="$1" -p="$2"
docker push willassistant/core:"$3"