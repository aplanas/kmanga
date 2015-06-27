#!/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

V=$LIBFFI_VER
PREFIX=$VENV

cd $LIBFFI

tar -xzvf libffi-$V.tar.gz
cd libffi-$V
./configure --prefix=$PREFIX
make -j 4 && make install
cd ..
rm -fr libffi-$V
