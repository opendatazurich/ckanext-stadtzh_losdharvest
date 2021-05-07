# coding=utf-8
import logging

from rdflib.namespace import Namespace

from ckanext.dcat.processors import RDFParser

log = logging.getLogger(__name__)

SCHEMA = Namespace("http://schema.org/")


class LosdViewsParser(RDFParser):
    """
    Parses the page that lists views to import.
    """
    def views(self):
        '''
        Generator that returns all DCAT datasets on the graph

        Yields rdflib.term.URIRef objects that can be used on graph lookups
        and queries
        '''
        for obj in self.g.objects(predicate=SCHEMA.dataset):
            yield obj


class LosdCodeParser(RDFParser):
    """Parses the data from a url like
    https://ld.stadt-zuerich.ch/statistics/code/{id}
    """
    def name(self):
        for obj in self.g.objects(predicate=SCHEMA.name):
            yield obj

    def identifier(self):
        for obj in self.g.objects(predicate=SCHEMA.identifier):
            yield obj

    def description(self):
        for obj in self.g.objects(predicate=SCHEMA.description):
            yield obj


class LosdPublisherParser(RDFParser):
    """Parses the data from a url like
    https://ld.stadt-zuerich.ch/org/SSZ
    """
    def name(self):
        for obj in self.g.objects(predicate=SCHEMA.name):
            yield obj


class LosdDatasetParser(RDFParser):
    """Parses the data from a url like
    https://ld.integ.stadt-zuerich.ch/statistics/view/D000002
    """
    def description(self):
        for obj in self.g.objects(predicate=SCHEMA.description):
            yield obj

    def keyword(self):
        for obj in self.g.objects(predicate=SCHEMA.keywords):
            yield obj

    def time_range(self):
        for obj in self.g.objects(predicate=SCHEMA.temporalCoverage):
            yield obj
