# coding=utf-8

import logging

import rdflib
from ckanext.dcat.profiles import RDFProfile
from rdflib.namespace import RDF, RDFS, SKOS, Namespace

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


class StadtzhLosdDcatProfile(RDFProfile):
    """
    An RDF profile for the LOSD Harvester
    """

    publishers = []

    def __init__(self, graph, compatibility_mode=False):
        super(StadtzhLosdDcatProfile, self).__init__(graph, compatibility_mode)

        self.publishers = self._get_publishers()

    def parse_dataset(self, dataset_dict, dataset_ref):
        log.debug("Parsing dataset '%r'" % dataset_ref)

        dataset_dict["extras"] = []
        dataset_dict["resources"] = []

        # Basic fields
        for key, predicate in (
            ("title", SCHEMA.name),
            ("notes", SCHEMA.description),
            ("identifier", SCHEMA.identifier),
            ("dateFirstPublished", SCHEMA.dateCreated),
            ("dateLastUpdated", SCHEMA.dateModified),
        ):
            value = self._object_value(dataset_ref, predicate)
            if value:
                dataset_dict[key] = value

        dataset_dict["maintainer"] = "Open Data Zürich"
        dataset_dict["maintainer_email"] = "opendata@zuerich.ch"

        publisher_obj = self._object_value(dataset_ref, SCHEMA.publisher)
        publisher = self.publishers[publisher_obj]
        dataset_dict["author"] = dataset_dict["url"] = (
            publisher["name"] or publisher["uri"]
        )

        # Tags
        keywords = self._object_value_list(dataset_ref, DCAT.keyword) or []
        tags = [{"name": tag} for tag in keywords]
        dataset_dict["tags"] = tags

        resource_dict = {
            "url": "http://example.com",
            "licence_id": "NonCommercialAllowed-CommercialAllowed-ReferenceNotRequired",
        }
        dataset_dict["resources"].append(resource_dict)

        return dataset_dict

    def _get_publishers(self):
        """
        Get data on all publishers defined in the graph.
        """
        publishers = {}
        publisher_objects = [
            SCHEMA.GovernmentOrganization,
            SCHEMA.Corporation,
            FOAF.GovernmentOrganization,
        ]

        for obj in publisher_objects:
            for publisher in self.g.subjects(RDF.type, obj):
                uri = (
                    unicode(publisher)
                    if isinstance(publisher, rdflib.term.URIRef)
                    else ""
                )
                name = self._object_value(publisher, SCHEMA.name)
                url = self._object_value(
                    publisher, FOAF.homepage
                ) or self._object_value(publisher, SCHEMA.url)

                publishers[uri] = {"uri": uri, "name": name, "url": url}

        return publishers
