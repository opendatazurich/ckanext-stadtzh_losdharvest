.. image:: https://www.repostatus.org/badges/latest/active.svg
   :alt: Project Status: Active – The project has reached a stable, usable state and is being actively developed.
   :target: https://www.repostatus.org/#active

===========================
ckanext-stadtzh_losdharvest
===========================

A harvester to import datasets from the City of Zürich's LOSD portal to its
CKAN instance (https://data.stadt-zuerich.ch/).


------------
Requirements
------------

This harvester was developed against CKAN 2.7.


------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-stadtzh_losdharvest:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-stadtzh_losdharvest Python package into your virtual environment::

     pip install ckanext-stadtzh_losdharvest

3. Add ``stadtzh_losdharvest`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config Settings
---------------

Add the profile to the CKAN config as below. If you have multiple profiles,
separate them with spaces::

   ckanext.dcat.rdf.profiles = stadtzh_losdharvest_dcat


-----------------------
Harvester Configuration
-----------------------

The RDF format of the data to be harvested can be set in the harvester
configuration. If it is not set, the default value is "text/turtle"::

    {
      "rdf_format":"text/turtle"
    }


------------------------
Development Installation
------------------------

To install ckanext-stadtzh_losdharvest for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/opendatazurich/ckanext-stadtzh_losdharvest.git
    cd ckanext-stadtzh_losdharvest
    python setup.py develop
    pip install -r dev-requirements.txt


-----------------
Running the Tests
-----------------

To run the tests, do::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.stadtzh_losdharvest --cover-inclusive --cover-erase --cover-tests

