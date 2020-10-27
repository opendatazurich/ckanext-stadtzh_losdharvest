from __future__ import print_function

from builtins import object
import xml

import rdflib
import rdflib.parser
from rdflib.namespace import Namespace, RDF

HYDRA = Namespace('http://www.w3.org/ns/hydra/core#')
DCAT = Namespace("http://www.w3.org/ns/dcat#")


class RDFProcessor(object):

    def __init__(self, profiles=None, compatibility_mode=False):
        '''
        Creates a parser or serializer instance
        '''
        self.g = rdflib.Graph()

    def parse(self, data, _format=None):
        '''
        Parses and RDF graph serialization and into the class graph

        It calls the rdflib parse function with the provided data and format.

        Data is a string with the serialized RDF graph (eg RDF/XML, N3
        ... ). By default RF/XML is expected. The optional parameter _format
        can be used to tell rdflib otherwise.

        It raises a ``RDFParserException`` if there was some error during
        the parsing.

        Returns nothing.
        '''
        try:
            self.g.parse(data=data, format=_format)
        # Apparently there is no single way of catching exceptions from all
        # rdflib parsers at once, so if you use a new one and the parsing
        # exceptions are not cached, add them here.
        # PluginException indicates that an unknown format was passed.
        except (SyntaxError, xml.sax.SAXParseException,
                rdflib.plugin.PluginException, TypeError) as e:

            raise Exception(e)

    def datasets(self):
        '''
        Generator that returns CKAN datasets parsed from the RDF graph
        '''
        for dataset_ref in self._datasets():
            dataset_dict = {}
            yield dataset_dict
