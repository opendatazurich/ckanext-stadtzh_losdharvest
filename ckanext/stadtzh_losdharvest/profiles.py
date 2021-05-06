# coding=utf-8

import logging

import isodate
import json
import rdflib
from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS, Namespace

from ckan.lib.munge import munge_tag, munge_title_to_name
from ckanext.dcat.profiles import RDFProfile
from ckanext.stadtzhharvest.utils import \
    stadtzhharvest_find_or_create_organization

from processors import LosdCodeParser, LosdPublisherParser, LosdDatasetParser
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
                dataset_dict[key] = self._format_datetime_as_string(value)
        dataset_dict["maintainer"] = "Open Data Zürich"
        dataset_dict["maintainer_email"] = "opendata@zuerich.ch"
        dataset_dict["name"] = munge_title_to_name(dataset_dict["title"])

        # publishers
        publishers = self._get_publishers_for_dataset_ref(dataset_ref)
        if publishers:
            dataset_dict["author"] = publishers[0]

        # Tags, notes and timeRange come from the dataset, referenced
        # from the view by SCHEMA.isBasedOn
        dataset_dict["notes"], dataset_dict["tags"], dataset_dict["timeRange"] =\
            self._get_based_on_fields(dataset_ref)

        # license
        dataset_dict["license_id"] = self._get_license_code_for_dataset_ref(
            dataset_ref
        )

        # rights
        dataset_dict["legalInformation"] = self._get_rights_for_dataset_ref(
            dataset_ref
        )

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
            publishers.append(parser.name().next())

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

            notes = parser.description().next()
            time_range = parser.time_range().next()

            for keyword in parser.keyword():
                tags.append(keyword)
            tags = self._process_tags(tags)

        return notes, tags, time_range

    def _process_tags(self, keyword_refs):
        """Process keyword refs to a list of dicts"""
        keywords = [
            self._get_value_from_literal_or_uri(ref) for ref in keyword_refs
        ]
        tags = [{"name": munge_tag(tag)} for tag in keywords]
        return tags

    def _get_license_code_for_dataset_ref(self, dataset_ref):
        """Get license for a dataset ref"""
        license_refs = []
        for resource_ref in self._get_resource_refs_for_dataset_ref(
            dataset_ref
        ):
            license_ref = self._get_object_refs_for_subject_predicate(
                resource_ref, SCHEMA.license
            )
            if license_ref:
                license_refs.extend(license_ref)
        if license_refs:
            license_ref = license_refs[0]
            license = self._get_value_from_literal_or_uri(license_ref)
            try:
                license_code = LICENSE_MAPPING_FOR_LOSD[license]
                return license_code
            except KeyError:
                return ""
        return ""

    def _json_encode_attributes(self, properties):
        # todo: Uncomment these lines once the LOSD source includes descriptions for attributes.
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
        """Get rights statement for a dataset ref"""
        refs = self._get_object_refs_for_subject_predicate(
            dataset_ref, DCTERMS.rights
        )
        if refs:
            dataset_rights_ref = refs[0]
            rights_statement_refs = \
                self._get_object_refs_for_subject_predicate(
                    dataset_rights_ref, SCHEMA.name
                )
            if rights_statement_refs:
                rights_statement_ref = rights_statement_refs[0]
                rights_statement = self._get_value_from_literal_or_uri(
                    rights_statement_ref
                )
                return rights_statement
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
                    ("format", rdflib.term.URIRef(u'http://purl.org/dc/terms/format')),
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
                # Todo: remove this line once we are using the custom solr config locally
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
