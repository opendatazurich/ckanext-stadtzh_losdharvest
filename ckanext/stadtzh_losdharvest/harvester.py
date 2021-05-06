# coding: utf-8

import json
import logging

import ckan.plugins as p
import requests

from ckanext.dcat.harvesters.rdf import DCATRDFHarvester
from ckanext.dcat.interfaces import IDCATRDFHarvester
from ckanext.dcat.processors import RDFParserException
from processors import LosdViewsParser

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

    def update_session(self, session):
        session.headers.update({"Accept": "text/turtle"})
        return session

    def _get_content_and_type(self, views_url, harvest_job, page=1,
                              content_type=None):
        """
        Overwritten from parent method because our source url goes to a
        list of links to views. We need to get all those links out first,
        and then get their content and concatenate it together.
        """
        if not views_url.lower().startswith('http'):
            self._save_gather_error('Could not get content for this views_url',
                                    harvest_job)
            return None, None

        try:
            if page > 1:
                views_url = views_url + '&' if '?' in views_url else views_url + '?'  # noqa
                views_url = views_url + 'page={0}'.format(page)

            log.debug('Getting file %s', views_url)

            session = requests.Session()
            self.update_session(session)
            r = session.get(views_url, stream=True)

            content = ''
            for chunk in r.iter_content(chunk_size=self.CHUNK_SIZE):
                content = content + chunk

            if content_type is None and r.headers.get('content-type'):
                content_type = r.headers.get('content-type').split(";", 1)[0]

        except requests.exceptions.RequestException, error:
            msg = '''Could not get content from %s because an
                                error occurred. %s''' % (views_url, error)
            self._save_gather_error(msg, harvest_job)
            return None, None

        parser = LosdViewsParser()

        try:
            parser.parse(content, _format=content_type)
        except RDFParserException, e:
            self._save_gather_error('Error parsing the views graph: {0}'
                                    .format(e), harvest_job)
            return None, None

        results = ''

        for view_url in parser.views():
            # Pass this UriRef to the parent _get_content_and_type method,
            # get the content and concatenate it to existing content
            view, view_type = super(DCATRDFHarvester, self)._get_content_and_type(  # noqa
                view_url, harvest_job)
            # log.warning(view)
            results += view

        return results, content_type

    def _get_guid(self, dataset_dict, source_url=None):
        """
        Overwritten from DCATRDFHarvester to return the given dataset
        name, or None if the dataset has no name.
        """
        if dataset_dict.get("name"):
            return dataset_dict["name"]

        return None
