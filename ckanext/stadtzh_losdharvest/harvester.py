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
            "name": "stadtzh_losdharvest",
            "title": "LOSD Harvester for the City of Zurich",
            "description": "Harvester for the LOSD Portal of the City of Zurich",  # noqa
        }

    def validate_config(self, source_config):
        source_config_obj = json.loads(source_config)

        if "rdf_format" not in source_config_obj:
            source_config_obj["rdf_format"] = "text/turtle"
            source_config = json.dumps(source_config_obj)

        return super(StadtzhLosdHarvester, self).validate_config(source_config)

    def before_download(self, url, harvest_job):
        # save the harvest_job on the instance
        self.harvest_job = harvest_job

        return url, []

    def _get_guid(self, dataset_dict, source_url=None):
        """
        Overwritten from DCATRDFHarvester to return the given dataset
        name, or None if the dataset has no name.
        """
        if dataset_dict.get("name"):
            return dataset_dict["name"]

        return None
