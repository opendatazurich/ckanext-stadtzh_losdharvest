# coding: utf-8

from ckanext.harvest.harvesters import HarvesterBase
from ckanext.stadtzh_losdharvest.processors import RDFParser
from pylons import config
import logging
log = logging.getLogger(__name__)


class StadtzhLosdHarvester(HarvesterBase):
    """
    LOSD harvester for the City of Zürich
    """
    def __init__(self, **kwargs):
        HarvesterBase.__init__(self, **kwargs)
        try:
            self.CKAN_SITE_URL = config['ckan.site_url']
        except KeyError as e:
            raise Exception("'%s' not found in config" % e.message)

    def info(self):
        return {
            'name': 'stadtzh_losd_harvester',
            'title': 'Harvester for the City of Zurich',
            'description': 'Harvester for the LOSD Portal of the City of Zurich'  # noqa
        }

    def gather_stage(self, harvest_job):
        log.debug('In StadtzhLosdHarvester gather_stage')
        parser = RDFParser()
        return True

    def fetch_stage(self, harvest_object):
        log.debug('In StadtzhLosdHarvester fetch_stage')
        return True

    def import_stage(self, harvest_object):
        log.debug('In StadtzhLosdHarvester import_stage')
        return True
