#!/usr/bin/env bash
docker login -u="$2" -p="$3"
docker push willassistant/core:"$1"