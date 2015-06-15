#/bin/sh

# Load the configuration file if exist
if [ ! -f "bin/kmanga.conf" ]; then
    echo "Please, create a bin/kmanga.conf configuration file."
    exit 1
fi
source bin/kmanga.conf


function usage {
    echo "Wrapper to test KManga."
    echo
    echo "$0 [-h | -c]"
    echo "  -h  for help"
    echo "  -c  to run the test with coverage.py"
    echo
}


error_code=0
run_coverage=0

while [ "$1" != "" ]; do
    case $1 in
	-c)
	    run_coverage=1
	    ;;
 
	-h | --help)
	    usage $0
	    exit 0
	    ;;
	*)
	    usage $0
	    exit 0
	    ;;
    esac
    shift
done

# External tests
if [ $run_coverage -eq 0 ]; then
    DJANGO_SETTINGS_MODULE=kmanga.settings \
			  python -m unittest discover -s ./tests
else
    DJANGO_SETTINGS_MODULE=kmanga.settings \
			  coverage run --branch -m --source=mobi,scraper \
			  unittest discover -s ./tests
fi
if [ $? -ne 0 ]; then
    echo "Error in external tests"
    error_code=1
fi

# Django tests
cd kmanga
if [ $run_coverage -eq 0 ]; then
    ./manage.py test
else
    mv ../.coverage .
    coverage run -a --branch --source='.' manage.py test
    mv .coverage ../
fi
if [ $? -ne 0 ]; then
    echo "Error in django tests"
    error_code=1
fi

exit $error_code
