FROM postgres:11.2-alpine

ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=password

# run create.sql on init
ADD create.sql /docker-entrypoint-initdb.d