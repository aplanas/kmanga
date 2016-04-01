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
			  coverage run --branch --source=mobi,scraper \
			  -m unittest discover -s ./tests
fi
if [ $? -ne 0 ]; then
    echo "Error in external tests"
    error_code=1
fi

# Scrapy tests
cd scraper
spiders="batoto mangafox mangareader mangahere"
for spider in $spiders; do
    if [ $run_coverage -eq 0 ]; then
	DJANGO_SETTINGS_MODULE=kmanga.settings scrapy check $spider
    else
	mv ../.coverage .
	DJANGO_SETTINGS_MODULE=kmanga.settings \
			      coverage run -a --branch --source=scraper \
			      $VENV/bin/scrapy check $spider
	mv .coverage ../
    fi
    if [ $? -ne 0 ]; then
	echo "Error in spider $spider test "
	error_code=1
    fi
done
cd ..

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
cd ..

if [ $run_coverage -eq 0 ]; then
    exit $error_code
fi

# Compare the max coverage
coverage=`coverage report | awk '/TOTAL/ {print $NF}' | grep -o '[^%]*'`
coverage_max=0
if [ -f ".coverage_max" ]; then
    coverage_max=`cat .coverage_max`
fi
if [ "$coverage_max" -gt "$coverage" ]; then
    echo "The coverage has decreased from $coverage_max% to $coverage%"
    error_code=2
elif [ "$coverage_max" -lt "$coverage" ]; then
    echo "The coverage has increased to $coverage% from $coverage_max%"
    echo $coverage > .coverage_max
else
    echo "Same coverage of $coverage%"
fi

exit $error_code
