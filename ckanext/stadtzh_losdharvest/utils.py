import logging

import requests

log = logging.getLogger(__name__)

MAX_FILE_SIZE = 1024 * 1024 * 50  # 50 Mb
CHUNK_SIZE = 1024
RDF_PROFILES_CONFIG_OPTION = 'ckanext.dcat.rdf.profiles'


def get_content_and_type(url, content_type=None):
    """
    Adapted from DCATHarvester._get_content_and_type, because we need to make
    requests while parsing the dataset, as well as when initially getting
    the data.

    :param url: a web url (starting with http) or a local path
    :param content_type: will be returned as type
    :return: a tuple containing the content and content-type
    """

    if not url.lower().startswith('http'):
        raise ValueError('Url should start with http: {}'.format(url))

    try:
        log.debug('Getting file %s', url)

        session = requests.Session()
        session.headers.update({"Accept": "text/turtle"})

        # first we try a HEAD request which may not be supported
        did_get = False
        r = session.head(url)
        if r.status_code == 405 or r.status_code == 400:
            r = session.get(url, stream=True)
            did_get = True
        r.raise_for_status()

        cl = r.headers.get('content-length')
        if cl and int(cl) > MAX_FILE_SIZE:
            msg = '''Remote file is too big. Allowed
                    file size: {allowed}, Content-Length: {actual}.'''.format(
                allowed=MAX_FILE_SIZE, actual=cl)
            raise RuntimeError(msg)

        if not did_get:
            r = session.get(url, stream=True)

        length = 0
        content = ''
        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
            content = content + chunk
            length += len(chunk)

            if length >= MAX_FILE_SIZE:
                raise RuntimeError('Remote file is too big.')

        if content_type is None and r.headers.get('content-type'):
            content_type = r.headers.get('content-type').split(";", 1)[0]

        return content, content_type

    except requests.exceptions.HTTPError, error:
        msg = 'Could not get content from %s. Server responded with %s %s' \
              % (url, error.response.status_code, error.response.reason)
        raise RuntimeError(msg)
    except requests.exceptions.ConnectionError, error:
        msg = '''Could not get content from %s because a
                                connection error occurred. %s''' % (url, error)
        raise RuntimeError(msg)
    except requests.exceptions.Timeout, error:
        msg = 'Could not get content from %s because the connection timed' \
              ' out.' % url
        raise RuntimeError(msg)
