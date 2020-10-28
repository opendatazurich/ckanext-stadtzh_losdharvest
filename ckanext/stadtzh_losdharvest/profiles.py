# coding=utf-8

import rdflib
from rdflib import URIRef, BNode, Literal
from rdflib.namespace import Namespace, RDFS, RDF, SKOS

from datetime import datetime

from ckantoolkit import config

import re

from ckanext.dcat.profiles import RDFProfile, SchemaOrgProfile
from ckanext.dcat.utils import resource_uri, publisher_uri_from_dataset_dict
from ckan.lib.munge import munge_tag

import logging
log = logging.getLogger(__name__)

BASE = Namespace('<https://ld.stadt-zuerich.ch/>')
QUDT = Namespace('<http://qudt.org/schema/qudt#>')
VOID = Namespace('<http://rdfs.org/ns/void#>')
OWL = Namespace('<http://www.w3.org/2002/07/owl#>')
XSD = Namespace('<http://www.w3.org/2001/XMLSchema#>')
DCTERMS = Namespace('<http://purl.org/dc/terms/>')
FOAF = Namespace('<http://xmlns.com/foaf/0.1/>')
WV = Namespace('<http://vocab.org/waiver/terms/norms>')
SD = Namespace('<http://www.w3.org/ns/sparql-service-description#>')
DCAT = Namespace('<http://www.w3.org/ns/dcat#>')
SCHEMA = Namespace('<http://schema.org/>')
TIME = Namespace('<http://www.w3.org/2006/time#>')
DOAP = Namespace('<http://usefulinc.com/ns/doap#>')
DUV = Namespace('<http://www.w3.org/ns/duv#>')
WD = Namespace('<http://www.wikidata.org/entity/>')
CUBE = Namespace('<http://ns.bergnet.org/cube/>')

namespaces = {
    'base': BASE,
    'qudt': QUDT,
    'void': VOID,
    'rdf': RDF,
    'rdfs': RDFS,
    'owl': OWL,
    'xsd': XSD,
    'dcterms': DCTERMS,
    'foaf': FOAF,
    'wv': WV,
    'sd': SD,
    'dcat': DCAT,
    'schema': SCHEMA,
    'time': TIME,
    'doap': DOAP,
    'duv': DUV,
    'wd': WD,
    'cube': CUBE,
    'skos': SKOS
}

slug_id_pattern = re.compile('[^/]+(?=/$|$)')


class StadtzhLosdDcatProfile(RDFProfile):
    '''
    An RDF profile for the LOSD Harvester
    '''

    def parse_dataset(self, dataset_dict, dataset_ref):  # noqa
        log.debug("Parsing dataset '%r'" % dataset_ref)

        # TODO: transform this later into a profile that
        #       finds the correct values by transformations

        # manually setting the one dataset that we have so far
        dataset_dict['title'] = "Luftqualitaet Schweiz (Jahreswerte)"
        dataset_dict['name'] = "luftqualitaet-schweiz-jahreswerte"
        dataset_dict['data_publisher'] = "Stadt Zürich"
        dataset_dict['url'] = 'http://example.com'
        dataset_dict['extras'] = []
        dataset_dict['resources'] = []

        resource_dict = {
            'url': 'http://example.com',
            'licence_id': "NonCommercialAllowed-CommercialAllowed-ReferenceNotRequired",
        }
        dataset_dict['resources'].append(resource_dict)
        return dataset_dict
