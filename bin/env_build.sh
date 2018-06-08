#!/bin/bash

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

if [ -d $VENV ]; then
    echo "Virtual environment $VENV found."
    exit 1
fi

$PYTHON -m venv $VENV
source $VENV/bin/activate

# Update PIP, as we use the one from the system
pip install --upgrade pip

export LD_LIBRARY_PATH=$VENV/lib

# Link some modules to the local library
ln -rs mobi $VENV/lib/$PYTHON/site-packages/
ln -rs scraper/scraper $VENV/lib/$PYTHON/site-packages/

# Link the configuration file
ln -rs bin/kmanga.conf $VENV/bin/

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

# Install a local copy of libffi
if [ -n "$LIBFFI" ]; then
    bin/libffi_build.sh
    export PKG_CONFIG_PATH=$VENV/lib/pkgconfig
fi

# Install Python packages
pip install Pillow
pip install Scrapy service-identity
pip install spidermonkey
pip install Django easy-thumbnails django-rq psycopg2-binary

if [ -n "$DEVEL" ]; then
    pip install coverage django-debug-toolbar
fi
