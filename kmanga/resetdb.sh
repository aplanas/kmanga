# !/bin/sh

rm db.sqlite3
rm main/migrations/000*
./manage.py makemigrations
./manage.py migrate
./manage.py createsuperuser --noinput --username aplanas --email aplanas@gmail.com
./manage.py loaddata initialdata.json
