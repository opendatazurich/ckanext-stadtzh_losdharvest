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
                f"Not harvesting dataset {dataset.get('name', '').upper()} because it "
                f"has no value for dcterms:issued"
            )
            return False
        try:
            datetime_obj = datetime.datetime.strptime(date_str, "%d.%m.%Y")
            if datetime_obj > datetime.datetime.now():
                log.info(
                    f"Not harvesting dataset {dataset.get('name', '').upper()} because "
                    f"its dcterms:issued date is in "
                    f"the future: {date_str}"
                )
            return datetime_obj < datetime.datetime.now()
        except (ValueError, TypeError):
            # If the date_str doesn't have the expected format %d.%m.%Y, it means we
            # got a weird value from the source and couldn't convert it.
            log.warning(
                f"Value of DCT.issued in dataset {dataset.get('name', '').upper()} "
                f"should be an ISO 8601 date string. Instead we got: {date_str}"
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

            log.debug(f"Getting file {views_url}")

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

    def _read_datasets_from_db(self, guid):
        """
        Overwritten from DCATHarvester as the guid disappears from package_extras
        when the dataset is updated outside the harvesting context.
        """
        datasets = super()._read_datasets_from_db(guid)
        if not datasets:
            log.info(
                f"Checking for datasets with id=guid, as the given guid {guid} was not "
                f"found in package_extras but we might have a package with that id."
            )
            datasets = (
                model.Session.query(model.Package.id)
                .filter(model.Package.name == guid)
                .filter(model.Package.state == "active")
                .all()
            )
        return datasets
