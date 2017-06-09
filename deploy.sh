#!/usr/bin/env bash
docker run willassistant/core:"$1" /bin/sh -c "cd /W.I.L.L/tests; nosetests *.py;"
docker login -u="$2" -p="$3"
docker push willassistant/core:"$1"