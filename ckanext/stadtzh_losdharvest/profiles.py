# coding=utf-8

import json
import logging

import isodate
import rdflib
from ckan.lib.munge import munge_tag
from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS, Namespace

from ckanext.dcat.profiles import RDFProfile
from ckanext.stadtzhharvest.utils import \
    stadtzhharvest_find_or_create_organization
from processors import (
    LosdCodeParser,
    LosdDatasetParser,
    LosdLegalFoundationParser,
    LosdPublisherParser)
from utils import get_content_and_type

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
CUBE = Namespace("https://cube.link/view/")

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
            ("sparqlEndpoint", VOID.sparqlEndpoint),
        ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                dataset_dict[key] = value

        dataset_dict["name"] = self._object_value(
            dataset_ref, SCHEMA.alternateName).lower()
        dataset_dict["notes"] = self._object_value(
            dataset_ref, SCHEMA.alternateName)  # todo: html->markdown

        # todo: groups: DCAT.theme
        # todo: tags: DCAT:keyword

        # Date fields
        for key, predicate in (
            ("dateFirstPublished", DCTERMS.issued),
            ("dateLastUpdated", DCTERMS.modified),
        ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                dataset_dict[key] = self._format_datetime_as_string(value)
        # todo: timeRange: SCHEMA.startDate + SCHEMA.endDate
        # todo: updateInterval: accrualPeriodicity

        dataset_dict["maintainer"] = "Open Data Zürich"
        dataset_dict["maintainer_email"] = "opendata@zuerich.ch"

        publishers = self._get_publishers_for_dataset_ref(dataset_ref)
        if publishers:
            dataset_dict["author"] = publishers[0]
            # todo: url: DCTERMS.publisher

        dataset_dict["license_id"] = self._get_license_code_for_dataset_ref(
            dataset_ref
        )
        dataset_dict["legalInformation"] = self._get_rights_for_dataset_ref(
            dataset_ref
        )
        # todo: spatialRelationship: DCTERMS.spatial
        # todo: sssBemerkungen: BASE.usageNotes

        # Attributes
        dataset_dict['sszFields'] = self._json_encode_attributes(
            self._get_attributes(dataset_ref))

        # Resources
        dataset_dict["resources"] = self._build_resources_dict(
            dataset_ref=dataset_ref, dataset_dict=dataset_dict
        )

        return dataset_dict

    def _get_publishers_for_dataset_ref(self, dataset_ref):
        """
        Get publishers for a dataset.
        """
        publishers = []
        publisher_refs = self._get_object_refs_for_subject_predicate(
            dataset_ref, SCHEMA.publisher
        )
        for ref in publisher_refs:
            content, content_type = get_content_and_type(ref)
            parser = LosdPublisherParser()
            parser.parse(content, content_type)
            for publisher in parser.name():
                publishers.append(publisher)

        return publishers

    def _get_based_on_fields(self, dataset_ref):
        notes = ''
        tags = []
        time_range = ''
        based_on_refs = self._get_object_refs_for_subject_predicate(
            dataset_ref, SCHEMA.isBasedOn
        )
        for ref in based_on_refs:
            content, content_type = get_content_and_type(ref)
            parser = LosdDatasetParser()
            parser.parse(content, content_type)

            for description in parser.description():
                notes = description
                break
            for tr in parser.time_range():
                time_range = tr
                break

            for keyword in parser.keyword():
                tags.append(keyword)
            tags = self._process_tags(tags)

        return {
            "notes": notes,
            "tags": tags,
            "timeRange": time_range
        }

    def _process_tags(self, keyword_refs):
        """Process keyword refs to a list of dicts"""
        keywords = [
            self._get_value_from_literal_or_uri(ref) for ref in keyword_refs
        ]
        tags = [{"name": munge_tag(tag)} for tag in keywords]
        return tags

    def _get_license_code_for_dataset_ref(self, dataset_ref):
        """Get license for a dataset ref"""
        license_refs = self._get_object_refs_for_subject_predicate(
            dataset_ref, DCTERMS.license
        )
        if license_refs:
            license = self._get_value_from_literal_or_uri(license_refs[0])
            return license
        return ""

    def _json_encode_attributes(self, properties):
        # todo: Uncomment these lines once the LOSD source includes
        # descriptions for attributes.
        # attributes = []
        # for key, value in properties:
        #     if value:
        #         attributes.append((key, value))

        return json.dumps(properties)

    def _get_attributes(self, dataset_ref):
        """Get the attributes for the dataset out of the dimensions"""
        attributes = []
        refs = self._get_object_refs_for_subject_predicate(
            dataset_ref, CUBE.dimension
        )
        for ref in refs:
            # Setting the predicate like this because `CUBE.as` produced
            # a Python error :(
            code_url = self._get_object_refs_for_subject_predicate(
                ref, rdflib.term.URIRef(u'https://cube.link/view/as'))

            try:
                content, content_type = get_content_and_type(code_url[0])
            except RuntimeError as e:
                log.info(e)
                continue

            parser = LosdCodeParser()
            parser.parse(content, content_type)

            name = ''
            for name in parser.name():
                speak_name = name
                break

            tech_name = ''
            for identifier in parser.identifier():
                tech_name = identifier
                break

            description = ''
            for desc in parser.description():
                description = desc
                break

            if tech_name != '':
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
        refs = self._get_object_refs_for_subject_predicate(
            dataset_ref, BASE.legalFoundation
        )
        if refs:
            dataset_rights_ref = refs[0]
            content, content_type = get_content_and_type(dataset_rights_ref)
            parser = LosdLegalFoundationParser()
            parser.parse(content, content_type)
            # TODO: get necessary data and return it
        return ""

    def _get_resource_refs_for_dataset_ref(self, dataset_ref):
        """return all resource refs for a dataset as a list"""
        resource_refs = self._get_object_refs_for_subject_predicate(
            dataset_ref, DCAT.distribution
        )
        resource_refs.extend(
            self._get_object_refs_for_subject_predicate(
                dataset_ref, SCHEMA.hasPart
            )
        )
        return resource_refs

    def _build_resources_dict(self, dataset_ref, dataset_dict):
        """
        get resources for the dataset: dcat:distributions or cube:Cube
        """
        resource_list = []
        for resource_ref in self._get_object_refs_for_subject_predicate(
            dataset_ref, DCAT.distribution
        ):
            resource_dict = {}
            # For some reason, DCTERMS.format does not work so we have to
            # use the explicit URIRef here.
            for key, predicate in (
                    ("url", DCAT.downloadURL),
                    ("format", rdflib.term.URIRef(u'http://purl.org/dc/terms/format')),  # noqa
                    ("mimetype", DCAT.mediaType),
            ):
                value = self._object_value(resource_ref, predicate)
                if value:
                    resource_dict[key] = value
            if not resource_dict.get("name"):
                resource_dict["name"] = dataset_dict["name"]

            if "csv" in resource_dict.get("mimetype"):
                resource_dict["url_type"] = "file"
                resource_dict["resource_type"] = "file"
            else:
                resource_dict["url_type"] = "api"
                # Todo: remove this line once we are using the custom solr
                # config locally
                # resource_dict["format"] = "CSV"
                resource_dict["resource_type"] = "api"

            resource_list.append(resource_dict)

        return resource_list

    def _get_object_refs_for_subject_predicate(self, subject_ref, predicate):
        """get all objects refs for a subject and predicate combination"""
        return [
            o for o in self.g.objects(subject=subject_ref, predicate=predicate)
        ]

    def _get_value_from_literal_or_uri(self, ref):
        """gets value from literal"""
        if isinstance(ref, Literal):
            return unicode(ref)
        elif isinstance(ref, URIRef):
            return ref
        else:
            return ""

    def _format_datetime_as_string(self, value):
        try:
            datetime_value = isodate.parse_date(value)
            return datetime_value.strftime('%d.%m.%Y')
        except (ValueError, KeyError, TypeError, IndexError):
            return value
