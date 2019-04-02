#!/bin/bash

until nc -z ${RABBIT_HOST} ${RABBIT_PORT}; do
    echo "$(date) - waiting for rabbitmq..."
    sleep 1
done


nameko run --config config.yml warehouse.service --backdoor 3000
#python -m gateway.flask_service