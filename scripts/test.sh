#!/usr/bin/env bash
nosetests --with-coverage ../tests
docker run willassistant/core:"$1" /bin/sh -c "cd /W.I.L.L/tests; nosetests *.py;"