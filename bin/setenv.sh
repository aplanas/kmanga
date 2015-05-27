# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
source bin/kmanga.conf

if [ ! -d $VENV ]; then
    echo "Virtual environment not $VENV found."
    exit 1
fi

export LD_LIBRARY_PATH=$VENV/lib
source $VENV/bin/activate
