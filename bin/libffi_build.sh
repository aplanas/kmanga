#!/bin/sh

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

V=$LIBFFI_VER
PREFIX=$VENV

cd $LIBFFI

tar -xzvf libffi-$V.tar.gz
cd libffi-$V
./configure --prefix=$PREFIX
make -j 4 && make install
cd ..
rm -fr libffi-$V
