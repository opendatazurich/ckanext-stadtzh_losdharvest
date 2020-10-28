# coding: utf-8

import json
import logging

import ckan.plugins as p
from ckanext.dcat.harvesters.rdf import DCATRDFHarvester
from ckanext.dcat.interfaces import IDCATRDFHarvester

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

    def validate_config(self, source_config):
        source_config_obj = json.loads(source_config)

        if 'rdf_format' not in source_config_obj:
            source_config_obj['rdf_format'] = 'text/turtle'
            source_config = json.dumps(source_config_obj)

        return super(StadtzhLosdHarvester, self).\
            validate_config(source_config)

    def before_download(self, url, harvest_job):
        # save the harvest_job on the instance
        self.harvest_job = harvest_job

        return url, []

    def _get_guid(self, dataset_dict, source_url=None):  # noqa
        """
        Try to get a unique identifier for a harvested dataset.

        We use source URL + dataset name, which is not ideal as it might
        change. (If we get a more stable identifier from LOSD in the future,
        we can use that instead.)

        When data is output as DCAT for harvesting, the
        StadtzhSwissDcatProfile is used, which generates a guid from
        dataset id + organization id. That means this guid won't be used
        for opendata.swiss.
        """
        guid = None

        if dataset_dict.get('name'):
            guid = dataset_dict['name']
            if source_url:
                guid = source_url.rstrip('/') + '/' + guid

        return guid
