#!/bin/bash

set -e

function cleanup {
    exit $?
}

trap "cleanup" EXIT

# Check PEP-8 code style and McCabe complexity
flake8 --statistics --show-source ckanext
# Check imports are sorted
isort -c -rc ckanext

# run tests
nosetests --ckan --with-pylons=subdir/test.ini --verbose ckanext/stadtzh_losdharvest
