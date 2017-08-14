#!/usr/bin/env bash
# Create a fresh environment for integration testing
echo "Creating db"
# sudo docker run -d --publish "3306":"3306" --rm --name=mysql_container -e MYSQL_ROOT_PASSWORD="$1" mysql
# Wait for the db to build
echo "Waiting for db to build"
sleep 10
echo "Initializing db"
CLIENT_SECRET=`python3 create_db.py 127.0.0.1 3306 root "$1" super-secret web-official`
echo "Got client_secret $CLIENT_SECRET"
echo "Setting up environment and running W.I.L.L"
sudo python3 env_gen.py root "$1" "0.0.0.0" "super-secret"
if [ "$3" = "--local" ]; then
    echo "Running locally"
    export DB_URL=0.0.0.0
    export DB_USERNAME=root
    export DB_PASSWORD="$1"
    export SECRET_KEY=super-secret
    gunicorn app:api &
else
    echo "Running in docker container"
    sudo docker run -d --rm --name will_container --env-file=.env --net=host willassistant/core:"$2"
fi
python3 integration_tests/user_tests.py "$CLIENT_SECRET"
# Kill the running services in different ways
if [ "$3" = "--local" ]; then
   sudo killall gunicorn
else
   sudo docker kill will_container
fi
# sudo docker kill mysql_container