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

export LD_LIBRARY_PATH=$VENV/lib

# Link some modules to the local library
ln -rs mobi $VENV/lib/python2.7/site-packages/
ln -rs scraper/scraper $VENV/lib/python2.7/site-packages/

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
pip install pyOpenSSL==0.13.1
pip install Scrapy Pillow easy-thumbnails django-rq service-identity psycopg2
