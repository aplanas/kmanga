#!/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
source bin/kmanga.conf

if [ -d $VENV ]; then
    echo "Virtual environment $VENV found."
    exit 1
fi

# Install Python virtual environment
virtualenv $VENV
source $VENV/bin/activate

# Install PostgreSQL
if [ -n "$PSQL" ]; then
    bin/psql_build.sh
    ln -rs bin/psql_start.sh $VENV/bin/
    ln -rs bin/psql_stop.sh $VENV/bin/
fi

# Install Redis
if [ -n "$REDIS" ]; then
    bin/redis_build.sh
    ln -rs bin/redis_start.sh $VENV/bin/
    ln -rs bin/redis_stop.sh $VENV/bin/
fi

# Install Python packages
pip install Scrapy Pillow django-rq service-identity psycopg2
