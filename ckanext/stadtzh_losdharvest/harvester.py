# coding: utf-8

import ckan.plugins as p

from ckanext.dcat.harvesters.rdf import DCATRDFHarvester
from ckanext.dcat.interfaces import IDCATRDFHarvester
import logging
log = logging.getLogger(__name__)


class StadtzhLosdHarvester(DCATRDFHarvester):
    """
    LOSD harvester for the City of Zürich
    """
    p.implements(IDCATRDFHarvester, inherit=True)

    harvest_job = None

    def info(self):
        return {
            'name': 'stadtzh_losdharvest',
            'title': 'LOSD Harvester for the City of Zurich',
            'description': 'Harvester for the LOSD Portal of the City of Zurich'  # noqa
        }
