#!/usr/bin/env bash
coverage combine .coveragec
codecov
docker login -u="$DOCKER_USERNAME" -p="$DOCKER_PASSWORD"
docker push willassistant/core:"$TRAVIS_BRANCH"