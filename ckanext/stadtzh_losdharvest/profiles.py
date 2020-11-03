# coding=utf-8

import logging
import isodate
from datetime import datetime

import rdflib
from ckanext.dcat.profiles import RDFProfile
from rdflib.namespace import RDF, RDFS, SKOS, Namespace
from rdflib import URIRef, BNode, Literal
from ckan.lib.munge import munge_title_to_name
from ckanext.stadtzhharvest.utils import stadtzhharvest_find_or_create_organization

log = logging.getLogger(__name__)

BASE = Namespace("https://ld.stadt-zuerich.ch/")
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
CUBE = Namespace("http://ns.bergnet.org/cube/")

namespaces = {
    "base": BASE,
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

license_cd_for_license = {
    rdflib.term.URIRef(u'http://creativecommons.org/licenses/by/3.0/'): 'cc_zero'
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
            ("notes", SCHEMA.description),
            ("sparqlEndpoint", VOID.sparqlEndpoint),
        ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                dataset_dict[key] = value

        # Date fields
        for key, predicate in (
            ("dateFirstPublished", SCHEMA.dateCreated),
            ("dateLastUpdated", SCHEMA.dateModified),
        ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                dataset_dict[key] = self._clean_datetime(value)

        dataset_dict["maintainer"] = "Open Data Zürich"
        dataset_dict["maintainer_email"] = "opendata@zuerich.ch"
        dataset_dict['name'] = munge_title_to_name(dataset_dict['title'])

        # publishers
        dataset_dict["author"] = self._get_publisher_for_dataset(dataset_ref)[0]

        # Tags
        dataset_dict["tags"] = self._get_tags(dataset_ref)

        # license
        dataset_dict["license_url"] = 'http://creativecommons.org/licenses/by/3.0/'
        dataset_dict["license_title"] = 'CC-BY 3.0'
        
        # Resources
        dataset_dict["resources"] = \
            self._build_resources_dict(dataset_ref=dataset_ref,
                                       dataset_dict=dataset_dict)

        return dataset_dict

    def _get_publisher_for_dataset(self, dataset_ref):
        """
        Get publisher for a dataset.
        """
        publisher_refs = self._get_object_refs_for_subject_predicate(dataset_ref, SCHEMA.publisher)
        publishers = [self._object_value(ref, SCHEMA.name) for ref in publisher_refs]
        return publishers

    def _get_tags(self, dataset_ref):
        """get all tags for a dataset"""
        keyword_refs = self._get_keyword_refs_for_dataset_ref(dataset_ref)
        keywords = [self._get_value_from_literal_or_uri(ref) for ref in keyword_refs]
        tags = [{"name": tag} for tag in keywords]
        return tags

    def _get_keyword_refs_for_dataset_ref(self, dataset_ref):
        """get all keyword_refs for a dataset"""
        keyword_refs = []
        subjects = self._get_resource_refs_for_dataset_ref(dataset_ref)
        subjects.append(dataset_ref)
        for subject in subjects:
            keyword_refs.extend([k for k in self.g.objects(subject=subject, predicate=DCAT.keyword)])
        return keyword_refs

    def _get_license_code_for_dataset_ref(self, dataset_ref):
        """Get license for a dataset ref"""
        license_refs = []
        for resource_ref in self._get_resource_refs_for_dataset_ref(dataset_ref):
            license_ref = self._get_object_refs_for_subject_predicate(resource_ref, SCHEMA.license)
            if license_ref:
               license_refs.extend(license_ref)
        license = [self._get_value_from_literal_or_uri(ref) for ref in license_refs][0]
        license_code = license_cd_for_license[license]
        return license_code

    def _get_resource_refs_for_dataset_ref(self, dataset_ref):
        resource_refs = self._get_object_refs_for_subject_predicate(dataset_ref, DCAT.distribution)
        resource_refs.extend(self._get_object_refs_for_subject_predicate(dataset_ref, SCHEMA.hasPart))
        return resource_refs

    def _build_resources_dict(self, dataset_ref, dataset_dict):
        """
        get resources for the dataset: dcat:distributions or cube:Cube
        """
        resource_list = []
        for resource_ref in self._get_object_refs_for_subject_predicate(dataset_ref, DCAT.distribution):
            resource_dict = {}
            for key, predicate in (
                    ("url", DCAT.downloadURL),
            ):
                value = self._object_value(resource_ref, predicate)
                if value:
                    resource_dict[key] = value
            for key, predicate in (
                    ("created", SCHEMA.dateCreated),
            ):
                value = self._object_value(resource_ref, predicate)
                if value:
                    resource_dict[key] = self._clean_datetime(value)
            if not resource_dict.get("name"):
                resource_dict['name'] = dataset_dict['name']
            resource_dict['url_type'] = 'upload'
            resource_list.append(resource_dict)

        for cube_ref in self._get_object_refs_for_subject_predicate(dataset_ref, SCHEMA.hasPart):
            resource_dict = {}
            for key, predicate in (
                    ("name", SCHEMA.name),
            ):
                value = self._object_value(cube_ref, predicate)
                if value:
                    resource_dict[key] = value
            resource_dict['url_type'] = 'api'
            resource_dict['url'] = dataset_dict['sparqlEndpoint']
            resource_list.append(resource_dict)

        return resource_list

    def _get_object_refs_for_subject_predicate(self, subject_ref, predicate):
        """get all objects refs for a subject and predicate combination"""
        return [o for o in self.g.objects(subject=subject_ref, predicate=predicate)]

    def _get_value_from_literal_or_uri(self, ref):
        """gets value from literal"""
        if isinstance(ref, Literal):
            return unicode(ref)
        elif isinstance(ref, URIRef):
            return ref
        else:
            return ''

    def _clean_datetime(self, value):
        try:
            datetime_value = isodate.parse_date(value)
            return datetime_value.strftime('%d.%m.%Y')
        except (ValueError, KeyError, TypeError, IndexError):
            return value
