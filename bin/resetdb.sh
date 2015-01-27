# !/bin/sh

# Load the configuration file if exist
if [ -f "etc/config.sh" ]; then
    . etc/config.sh
fi

if [ -z "$PYTHON" ]; then
    PYTHON=python
fi

rm kmanga/db.sqlite3
rm kmanga/main/migrations/000*
rm kmanga/registration/migrations/000*
$PYTHON kmanga/manage.py makemigrations
$PYTHON kmanga/manage.py migrate
$PYTHON kmanga/manage.py createsuperuser --username aplanas --email aplanas@gmail.com
$PYTHON kmanga/manage.py loaddata kmanga/initialdata.json
