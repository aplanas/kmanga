# !/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
. bin/kmanga.conf

dropdb --if-exists kmanga
createdb kmanga
rm kmanga/main/migrations/000*
rm kmanga/registration/migrations/000*
$PYTHON kmanga/manage.py makemigrations
ln -sr bin/0002_full_text_search.py kmanga/main/migrations/
$PYTHON kmanga/manage.py migrate
$PYTHON kmanga/manage.py createsuperuser --username aplanas --email aplanas@gmail.com
$PYTHON kmanga/manage.py loaddata kmanga/initialdata.json
