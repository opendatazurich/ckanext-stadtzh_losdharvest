# coding: utf-8

import datetime
import json
import logging

import ckan.model as model
import ckan.plugins as p
import requests
from ckan.logic import get_action

from ckanext.dcat.harvesters.rdf import DCATRDFHarvester
from ckanext.dcat.interfaces import IDCATRDFHarvester
from ckanext.dcat.processors import RDFParserException
from ckanext.stadtzh_losdharvest.processors import LosdViewsParser
from ckanext.stadtzhtheme.plugin import (
    ogdzh_package_create_default_resource_views,
)

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
            "description": "Harvester for the LOSD Portal of the City of Zurich",
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

    def _is_published(self, dataset):
        """Return True if the dataset has a dateFirstPublished in the past.
        This value is mapped from the attribute dcterms:issued.
        """
        date_str = dataset.get("dateFirstPublished", None)
        if date_str is None:
            log.info(
                "Not harvesting dataset {} because it has no value for dcterms:issued"
            )
            return False
        try:
            datetime_obj = datetime.datetime.strptime(date_str, "%d.%m.%Y")
            if datetime_obj > datetime.datetime.now():
                log.info(
                    "Not harvesting dataset {} because its dcterms:issued date is in "
                    "the future"
                )
            return datetime_obj < datetime.datetime.now()
        except (ValueError, TypeError):
            # If the date_str doesn't have the expected format %d.%m.%Y, it means we
            # got a weird value from the source and couldn't convert it.
            log.warning(
                "Value of DCT.issued in dataset {} should be an ISO 8601 date string. "
                "Instead we got: {}".format(dataset.get("name"), date_str)
            )
            return False

    def after_parsing(self, rdf_parser, harvest_job):
        """Called just after the content from the remote RDF file has been parsed

        Filters the datasets in the parser to only include those that have been
        published (according to the dateFirstPublished field).
        """
        all_datasets = rdf_parser.datasets()

        def filter_datasets():
            for dataset in filter(self._is_published, all_datasets):
                yield dataset

        rdf_parser.datasets = filter_datasets

        return rdf_parser, []

    def after_create(self, harvest_object, dataset_dict, temp_dict):
        log.debug("In StadtzhLosdHarvester after_create")
        self._touch_resources(dataset_dict)

    def after_update(self, harvest_object, dataset_dict, temp_dict):
        log.debug("In StadtzhLosdHarvester after_update")
        self._touch_resources(dataset_dict)

    # submit resources to xloader
    def _touch_resources(self, dataset_dict):
        context = {
            "model": model,
            "session": model.Session,
            "user": self._get_user_name(),
            "ignore_auth": True,
        }
        dataset = get_action("package_show")(context, {"id": dataset_dict["id"]})

        for resource in dataset["resources"]:
            get_action("xloader_submit")(context, {"resource_id": resource["id"]})

        ogdzh_package_create_default_resource_views(context, dataset)

    def _get_content_and_type(self, views_url, harvest_job, page=1, content_type=None):
        """
        Overwritten from parent method because our source url goes to a
        list of links to views. We need to get all those links out first,
        and then get their content and concatenate it together.
        """
        if not views_url.lower().startswith("http"):
            self._save_gather_error(
                "Could not get content for this views_url", harvest_job
            )
            return None, None

        try:
            if page > 1:
                views_url = views_url + "&" if "?" in views_url else views_url + "?"
                views_url = views_url + "page={0}".format(page)

            log.debug("Getting file %s", views_url)

            session = requests.Session()
            self.update_session(session)
            r = session.get(views_url, stream=True)

            content = b""
            for chunk in r.iter_content(chunk_size=self.CHUNK_SIZE):
                content = content + chunk

            if content_type is None and r.headers.get("content-type"):
                content_type = r.headers.get("content-type").split(";", 1)[0]

        except requests.exceptions.RequestException as error:
            msg = """Could not get content from %s because an
                                error occurred. %s""" % (
                views_url,
                error,
            )
            self._save_gather_error(msg, harvest_job)
            return None, None

        parser = LosdViewsParser()

        try:
            parser.parse(content, _format=content_type)
        except RDFParserException as e:
            self._save_gather_error(
                "Error parsing the views graph: {0}".format(e), harvest_job
            )
            return None, None

        results = ""

        for view_url in parser.views():
            # Pass this UriRef to the parent _get_content_and_type method,
            # get the content and concatenate it to existing content
            view, view_type = super(DCATRDFHarvester, self)._get_content_and_type(
                view_url, harvest_job
            )
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
