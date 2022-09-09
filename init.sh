#!/usr/bin/env bash

set -xe

DOCKER_COMPOSE="docker-compose exec -T"
MYSQL="$DOCKER_COMPOSE db mysql --host=127.0.0.1 --port=3306"
SOLR_CONTAINER_ID=`docker ps -f "name=solr" --format "{{.ID}}"`

echo "Wait for DB to be ready..."
while ! $MYSQL -e "SELECT 1" >/dev/null 2>&1; do
    sleep 1
done
echo "DB ready!!!"

echo "Setting up development database"
$MYSQL -e "CREATE DATABASE IF NOT EXISTS nuremberg_dev"
$MYSQL -e "CREATE USER nuremberg; GRANT ALL ON nuremberg_dev.* TO nuremberg"
$MYSQL -u nuremberg nuremberg_dev < nuremberg/core/tests/data.sql

echo "Setting up persistent test database"
$MYSQL -e "CREATE DATABASE IF NOT EXISTS test_nuremberg_dev"
$MYSQL -e "GRANT ALL ON test_nuremberg_dev.* TO nuremberg"
$MYSQL -unuremberg test_nuremberg_dev < nuremberg/core/tests/data.sql

echo "Migrating databases"
$DOCKER_COMPOSE web python manage.py migrate

echo "Setting up solr index (slow)"
$DOCKER_COMPOSE -u root solr mkdir -p /var/solr/data/nuremberg_dev
$DOCKER_COMPOSE -u root solr cp -pr "/opt/solr-8.8.1/example/files/conf" "/var/solr/data/nuremberg_dev/"
docker cp solr_conf/schema.xml $SOLR_CONTAINER_ID:/var/solr/data/nuremberg_dev/conf/
docker cp solr_conf/solrconfig.xml $SOLR_CONTAINER_ID:/var/solr/data/nuremberg_dev/conf/
$DOCKER_COMPOSE -u root solr chown -R solr:solr /var/solr/data

$DOCKER_COMPOSE solr curl -sSL 'http://localhost:8983/solr/admin/cores?action=CREATE&name=nuremberg_dev&instanceDir=/var/solr/data/nuremberg_dev&schema=schema.xml'
$DOCKER_COMPOSE web python manage.py rebuild_index --noinput
