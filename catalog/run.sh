#!/bin/bash

until nc -z ${RABBIT_HOST} ${RABBIT_PORT}; do
    echo "$(date) - waiting for rabbitmq..."
    sleep 1
done

#alembic upgrade head

nameko run --config config.yml catalog.service --backdoor 3000