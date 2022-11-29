# coding=utf-8

import json
import logging

import isodate
import rdflib
from ckan.lib.munge import munge_tag, munge_title_to_name
from markdownify import markdownify as md
from rdflib.namespace import RDF, RDFS, SKOS, Namespace

from ckanext.dcat.profiles import RDFProfile
from ckanext.stadtzh_losdharvest.processors import LosdParser
from ckanext.stadtzh_losdharvest.utils import get_content_and_type
from ckanext.stadtzhharvest.utils import (
    stadtzhharvest_find_or_create_organization, stadtzhharvest_get_group_names)

log = logging.getLogger(__name__)

BASE = Namespace("https://ld.stadt-zuerich.ch/schema/")
BASEINT = Namespace("https://ld.integ.stadt-zuerich.ch/schema/")
QUDT = Namespace("http://qudt.org/schema/qudt#")
VOID = Namespace("http://rdfs.org/ns/void#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
WV = Namespace("http://vocab.org/waiver/terms/norms")
SD = Namespace("http://www.w3.org/ns/sparql-service-description#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
SCHEMA = Namespace("http://schema.org/")
TIME = Namespace("http://www.w3.org/2006/time#")
DOAP = Namespace("http://usefulinc.com/ns/doap#")
DUV = Namespace("http://www.w3.org/ns/duv#")
WD = Namespace("http://www.wikidata.org/entity/")
CUBE = Namespace("https://cube.link/view/")

namespaces = {
    "base": BASE,
    "baseint": BASEINT,
    "qudt": QUDT,
    "void": VOID,
    "rdf": RDF,
    "rdfs": RDFS,
    "owl": OWL,
    "xsd": XSD,
    "dcterms": DCTERMS,
    "foaf": FOAF,
    "wv": WV,
    "sd": SD,
    "dcat": DCAT,
    "schema": SCHEMA,
    "time": TIME,
    "doap": DOAP,
    "duv": DUV,
    "wd": WD,
    "cube": CUBE,
    "skos": SKOS,
}

LICENSE_MAPPING_FOR_LOSD = {
    rdflib.term.URIRef(
        u"http://creativecommons.org/licenses/by/3.0/"
    ): "cc-by"
}


class StadtzhLosdDcatProfile(RDFProfile):
    """
    An RDF profile for the LOSD Harvester
    """

    def __init__(self, graph, compatibility_mode=False):
        super(StadtzhLosdDcatProfile, self).__init__(graph, compatibility_mode)

    def parse_dataset(self, dataset_dict, dataset_ref):
        log.debug("Parsing dataset '%r'" % dataset_ref)

        stadtzhharvest_find_or_create_organization(dataset_dict)
        dataset_dict["extras"] = []
        dataset_dict["resources"] = []

        # Basic fields
        for key, predicate in (
            ("title", SCHEMA.name),
            ("spatialRelationship", DCTERMS.spatial),
            ("sparqlEndpoint", VOID.sparqlEndpoint),
            ("updateInterval", DCTERMS.accrualPeriodicity),
            ("license_id", DCTERMS.license),
        ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                dataset_dict[key] = value

        dataset_dict["name"] = self._object_value(
            dataset_ref, SCHEMA.alternateName).lower()
        dataset_dict["notes"] = md(self._object_value(
            dataset_ref, SCHEMA.description))
        dataset_dict["sszBemerkungen"] = md(
            self._object_value_from_losd_predicate(
                dataset_ref, "usageNotes"
            )
        )
        dataset_dict["tags"] = [
            {"name": munge_tag(tag)} for tag in self._keywords(dataset_ref)]
        dataset_dict["groups"] = self._get_groups_for_dataset_ref(dataset_ref)

        dataset_dict["maintainer"] = "Open Data Zürich"
        dataset_dict["maintainer_email"] = "opendata@zuerich.ch"

        publishers = self._get_publisher_for_dataset_ref(dataset_ref)
        if publishers:
            dataset_dict["url"] = publishers[0]

        dataset_dict["legalInformation"] = self._get_rights_for_dataset_ref(
            dataset_ref
        )

        # Date fields
        for key, predicate in (
            ("dateFirstPublished", DCTERMS.issued),
            ("dateLastUpdated", DCTERMS.modified),
        ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                dataset_dict[key] = self._format_datetime_as_string(value)

        # Construct timeRange out of the dataset's startDate and endDate.
        time_range_parts = []
        start_date = self._object_value(dataset_ref, SCHEMA.startDate)
        if start_date:
            time_range_parts.append(
                self._format_datetime_as_string(start_date))
        time_range_parts.append('-')
        end_date = self._object_value(dataset_ref, SCHEMA.endDate)
        if end_date:
            time_range_parts.append(self._format_datetime_as_string(end_date))

        if start_date or end_date:
            dataset_dict['timeRange'] = ' '.join(time_range_parts)

        # Attributes
        dataset_dict['sszFields'] = json.dumps(
            self._get_attributes(dataset_ref))

        # Resources
        dataset_dict["resources"] = self._build_resources_dict(
            dataset_ref=dataset_ref, dataset_dict=dataset_dict
        )

        return dataset_dict

    def _get_publisher_for_dataset_ref(self, dataset_ref):
        """
        Get publisher for a dataset.
        """
        publishers = []
        publisher_ref = self._object_value(dataset_ref, DCTERMS.publisher)
        content, content_type = get_content_and_type(publisher_ref)
        parser = LosdParser()
        parser.parse(content, content_type)

        return parser.name()

    def _get_groups_for_dataset_ref(self, dataset_ref):
        groups = []
        group_titles = self._object_value_list(dataset_ref, DCAT.theme)
        for title in group_titles:
            name = munge_title_to_name(title)
            groups.append((name, title))
        return stadtzhharvest_get_group_names(groups)

    def _get_attributes(self, dataset_ref):
        """Get the attributes for the dataset out of the dimensions"""
        attributes = []
        for ref in self._objects_from_losd_predicate(
                dataset_ref, 'dataAttribute'
        ):
            speak_name = self._object(ref, SCHEMA.name)
            tech_name = self._object(ref, SCHEMA.alternateName)
            description = self._object(ref, SCHEMA.description)

            if tech_name is not None:
                attribute_name = '%s (technisch: %s)' % (speak_name, tech_name)
            else:
                attribute_name = speak_name

            attributes.append(
                (
                    attribute_name,
                    description
                )
            )

        return list(set(attributes))

    def _get_rights_for_dataset_ref(self, dataset_ref):
        """Get rights statement for a dataset ref
        """
        dataset_rights_ref = self._object(dataset_ref, BASE.legalFoundation)
        if not dataset_rights_ref:
            return ""

        try:
            content, content_type = get_content_and_type(dataset_rights_ref)
            parser = LosdParser()
            parser.parse(content, content_type)
            # TODO: get necessary data and return it
        except RuntimeError as e:
            log.warning(e)

        return ""

    def _build_resources_dict(self, dataset_ref, dataset_dict):
        """Get resources for the dataset.
        """
        resource_list = []
        for resource_ref in self.g.objects(dataset_ref, DCAT.distribution):
            resource_dict = {}
            # For some reason, DCTERMS.format does not work so we have to
            # use the explicit URIRef here.
            for key, predicate in (
                    ("url", DCAT.downloadURL),
                    ("format", rdflib.term.URIRef(
                        u'http://purl.org/dc/terms/format')),
                    ("mimetype", DCAT.mediaType),
            ):
                value = self._object_value(resource_ref, predicate)
                if value:
                    resource_dict[key] = value
            if not resource_dict.get("name"):
                resource_dict["name"] = dataset_dict["name"]

            if "csv" in resource_dict.get("mimetype", ""):
                resource_dict["url_type"] = "file"
                resource_dict["resource_type"] = "file"
            else:
                resource_dict["url_type"] = "api"
                resource_dict["resource_type"] = "api"

            resource_list.append(resource_dict)

        return resource_list

    def _objects_from_losd_predicate(self, ref, predicate_name):
        """Get the objects with this subject and predicate name, where
        the predicate is defined in either the SSZ LD namespace, or the INTEG
        SSZ LD namespace.
        """
        for o in self.g.objects(ref, BASE[predicate_name]):
            yield o
        for o in self.g.objects(ref, BASEINT[predicate_name]):
            yield o

    def _object_value_from_losd_predicate(self, ref, predicate_name):
        """Get the object value with this subject and predicate name, where
        the predicate is defined in either the SSZ LD namespace, or the INTEG
        SSZ LD namespace.
        """
        value = self._object_value(ref, BASE[predicate_name]) or \
            self._object_value(ref, BASEINT[predicate_name])

        return value

    def _format_datetime_as_string(self, value):
        try:
            datetime_value = isodate.parse_date(value)
            return datetime_value.strftime('%d.%m.%Y')
        except (ValueError, KeyError, TypeError, IndexError):
            return value
