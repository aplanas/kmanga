#/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
source bin/kmanga.conf

error_code=0

# External tests
DJANGO_SETTINGS_MODULE=kmanga.settings python -m unittest discover -s ./tests
if [ $? -ne 0 ]; then
    echo "Error in external tests"
    error_code=1
fi

# Django tests
cd kmanga
./manage.py test
if [ $? -ne 0 ]; then
    echo "Error in django tests"
    error_code=1
fi

exit $error_code
