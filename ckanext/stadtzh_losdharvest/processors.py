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
        return self.g.objects(predicate=SCHEMA.name)[0]


    def identifier(self):
        return self.g.objects(predicate=SCHEMA.identifier)
