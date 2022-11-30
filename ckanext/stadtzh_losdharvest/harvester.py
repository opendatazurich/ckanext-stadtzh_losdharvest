# coding: utf-8

import json
import uuid
import logging

import ckan.plugins as p
import ckan.model as model
import requests

import ckan.lib.plugins as lib_plugins

from ckanext.dcat.harvesters.rdf import DCATRDFHarvester
from ckanext.dcat.interfaces import IDCATRDFHarvester
from ckanext.dcat.processors import RDFParserException
from ckanext.harvest.model import HarvestObject, HarvestObjectExtra
from ckanext.harvest.logic.schema import unicode_safe
from ckanext.stadtzh_losdharvest.processors import LosdViewsParser

log = logging.getLogger(__name__)


class StadtzhLosdHarvester(DCATRDFHarvester):
    """
    LOSD harvester for the City of Zürich
    """

    p.implements(IDCATRDFHarvester, inherit=True)

    harvest_job = None

    def info(self):
        return {
            "name": "stadtzh_losdharvest",
            "title": "LOSD Harvester for the City of Zurich",
            "description": "Harvester for the LOSD Portal of the City of Zurich",  # noqa
        }

    def validate_config(self, source_config):
        source_config_obj = json.loads(source_config)

        if "rdf_format" not in source_config_obj:
            source_config_obj["rdf_format"] = "text/turtle"
            source_config = json.dumps(source_config_obj)

        return super(StadtzhLosdHarvester, self).validate_config(source_config)

    def update_session(self, session):
        session.headers.update({"Accept": "text/turtle"})
        return session

    def import_stage(self, harvest_object):

        log.debug('In StadtzhHarvester import_stage')

        if harvest_object.content is None:
            self._save_object_error('Empty content for object {0}'.format(harvest_object.id),
                                    harvest_object, 'Import')
            return False

        try:
            dataset = json.loads(harvest_object.content)
        except ValueError:
            self._save_object_error('Could not parse content for object {0}'.format(harvest_object.id),
                                    harvest_object, 'Import')
            return False

        status = self._get_object_extra(harvest_object, 'status')
        if status == 'delete':
            # Delete package
            context = {'model': model, 'session': model.Session,
                       'user': self._get_user_name(), 'ignore_auth': True}

            p.toolkit.get_action('package_delete')(context, {'id': harvest_object.package_id})
            log.info('Deleted package {0} with guid {1}'.format(harvest_object.package_id,
                                                                harvest_object.guid))
            return True

        # Get the last harvested object (if any)
        previous_object = model.Session.query(HarvestObject) \
            .filter(HarvestObject.guid==harvest_object.guid) \
            .filter(HarvestObject.current==True) \
            .first()

        # Flag previous object as not current anymore
        if previous_object:
            previous_object.current = False
            previous_object.add()

        # Flag this object as the current one
        harvest_object.current = True
        harvest_object.add()

        context = {
            'user': self._get_user_name(),
            'return_id_only': True,
            'ignore_auth': True,
        }

        dataset = self.modify_package_dict(dataset, {}, harvest_object)

        # Check if a dataset with the same guid exists
        existing_dataset = self._get_existing_dataset(harvest_object.guid)

        try:
            package_plugin = lib_plugins.lookup_package_plugin(dataset.get('type', None))
            if existing_dataset:
                package_schema = package_plugin.update_package_schema()
                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    package_schema = harvester.update_package_schema_for_update(package_schema)
                context['schema'] = package_schema

                # Don't change the dataset name even if the title has
                dataset['name'] = existing_dataset['name']
                dataset['id'] = existing_dataset['id']

                harvester_tmp_dict = {}

                # check if resources already exist based on their URI
                existing_resources =  existing_dataset.get('resources')
                resource_mapping = {r.get('uri'): r.get('id') for r in existing_resources if r.get('uri')}
                for resource in dataset.get('resources'):
                    res_uri = resource.get('uri')
                    if res_uri and res_uri in resource_mapping:
                        resource['id'] = resource_mapping[res_uri]

                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    harvester.before_update(harvest_object, dataset, harvester_tmp_dict)

                try:
                    if dataset:
                        # Save reference to the package on the object
                        harvest_object.package_id = dataset['id']
                        harvest_object.add()

                        p.toolkit.get_action('package_update')(context, dataset)
                    else:
                        log.info('Ignoring dataset %s' % existing_dataset['name'])
                        return 'unchanged'
                except p.toolkit.ValidationError as e:
                    self._save_object_error('Update validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                    return False

                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    err = harvester.after_update(harvest_object, dataset, harvester_tmp_dict)

                    if err:
                        self._save_object_error('RDFHarvester plugin error: %s' % err, harvest_object, 'Import')
                        return False

                log.info('Updated dataset %s' % dataset['name'])

            else:
                package_schema = package_plugin.create_package_schema()
                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    package_schema = harvester.update_package_schema_for_create(package_schema)
                context['schema'] = package_schema

                # We need to explicitly provide a package ID
                dataset['id'] = str(uuid.uuid4())
                package_schema['id'] = [unicode_safe]

                harvester_tmp_dict = {}

                name = dataset['name']
                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    harvester.before_create(harvest_object, dataset, harvester_tmp_dict)

                try:
                    if dataset:
                        # Save reference to the package on the object
                        harvest_object.package_id = dataset['id']
                        harvest_object.add()

                        # Defer constraints and flush so the dataset can be indexed with
                        # the harvest object id (on the after_show hook from the harvester
                        # plugin)
                        model.Session.execute('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
                        model.Session.flush()

                        p.toolkit.get_action('package_create')(context, dataset)
                    else:
                        log.info('Ignoring dataset %s' % name)
                        return 'unchanged'
                except p.toolkit.ValidationError as e:
                    self._save_object_error('Create validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                    return False

                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    err = harvester.after_create(harvest_object, dataset, harvester_tmp_dict)

                    if err:
                        self._save_object_error('RDFHarvester plugin error: %s' % err, harvest_object, 'Import')
                        return False

                log.info('Created dataset %s' % dataset['name'])

        except Exception as e:
            self._save_object_error('Error importing dataset %s: %r / %s' % (dataset.get('name', ''), e, traceback.format_exc()), harvest_object, 'Import')
            return False

        finally:
            model.Session.commit()

        return True

    def _get_content_and_type(self, views_url, harvest_job, page=1,
                              content_type=None):
        """
        Overwritten from parent method because our source url goes to a
        list of links to views. We need to get all those links out first,
        and then get their content and concatenate it together.
        """
        if not views_url.lower().startswith('http'):
            self._save_gather_error('Could not get content for this views_url',
                                    harvest_job)
            return None, None

        try:
            if page > 1:
                views_url = views_url + '&' if '?' in views_url else views_url + '?'  # noqa
                views_url = views_url + 'page={0}'.format(page)

            log.debug('Getting file %s', views_url)

            session = requests.Session()
            self.update_session(session)
            r = session.get(views_url, stream=True)

            content = ''
            for chunk in r.iter_content(chunk_size=self.CHUNK_SIZE):
                content = content + chunk

            if content_type is None and r.headers.get('content-type'):
                content_type = r.headers.get('content-type').split(";", 1)[0]

        except requests.exceptions.RequestException as error:
            msg = '''Could not get content from %s because an
                                error occurred. %s''' % (views_url, error)
            self._save_gather_error(msg, harvest_job)
            return None, None

        parser = LosdViewsParser()

        try:
            parser.parse(content, _format=content_type)
        except RDFParserException as e:
            self._save_gather_error('Error parsing the views graph: {0}'
                                    .format(e), harvest_job)
            return None, None

        results = ''

        for view_url in parser.views():
            # Pass this UriRef to the parent _get_content_and_type method,
            # get the content and concatenate it to existing content
            view, view_type = super(DCATRDFHarvester, self)._get_content_and_type(  # noqa
                view_url, harvest_job)
            # log.warning(view)
            results += view

        return results, content_type

    def _get_guid(self, dataset_dict, source_url=None):
        """
        Overwritten from DCATRDFHarvester to return the given dataset
        name, or None if the dataset has no name.
        """
        if dataset_dict.get("name"):
            return dataset_dict["name"]

        return None
