# coding=utf-8
import logging

from rdflib.namespace import Namespace

from ckanext.dcat.processors import RDFParser

log = logging.getLogger(__name__)

SCHEMA = Namespace("https://schema.org/")


class LosdParser(RDFParser):
    """Basic parser for LOSD pages."""

    def name(self):
        """Returns the first object in the graph with the predicate
        SCHEMA.name.
        """
        for obj in self.g.objects(predicate=SCHEMA.name):
            return obj


class LosdViewsParser(LosdParser):
    """Parses the page that lists views to import."""

    def views(self):
        """
        Generator that returns all DCAT datasets on the graph

        Yields rdflib.term.URIRef objects that can be used on graph lookups
        and queries
        """
        for obj in self.g.objects(predicate=SCHEMA.dataset):
            yield obj
