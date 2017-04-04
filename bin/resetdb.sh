# !/bin/sh

# Load the configuration file if exist
KMANGA_CONF=$(dirname $0)/kmanga.conf
if [ ! -f "$KMANGA_CONF" ]; then
    echo "Please, create a $KMANGA_CONF configuration file."
    exit 1
fi
source $KMANGA_CONF

dropdb -p $PSQL_PORT --if-exists kmanga
createdb -p $PSQL_PORT kmanga
rm kmanga/core/migrations/000*
rm kmanga/registration/migrations/000*
$PYTHON kmanga/manage.py makemigrations
cp bin/0002_full_text_search.py kmanga/core/migrations/
$PYTHON kmanga/manage.py migrate
$PYTHON kmanga/manage.py createsuperuser --username aplanas --email aplanas@gmail.com
$PYTHON kmanga/manage.py loaddata bin/initialdata.json
