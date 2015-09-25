#-----------------------------------------------------------------------------
# Copyright (c) 2012 - 2015, Continuum Analytics, Inc. All rights reserved.
#
# Powered by the Bokeh Development Team.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------
""" Encapsulate implicit state that is useful for Bokeh plotting APIs.

Generating output for Bokeh plots requires coordinating several things:

:class:`Documents <bokeh.document>`
    Group together Bokeh models that may be shared between plots (e.g.,
    range or data source objects) into one common namespace.

:class:`Resources <bokeh.resources>`
    Control how JavaScript and CSS for the client library BokehJS are
    included and used in the generated output.

:class:`Sessions <bokeh.session>`
    Create and manage persistent connections to a Bokeh server.

It is certainly possible to handle the configuration of these objects
manually, and several examples of this can be found in ``examples/glyphs``.
When developing sophisticated applications, it may be necessary or
desirable to work at this level. However, for general use this would
quickly become burdensome. The ``bokeh.state`` module provides a ``State``
class that encapsulates these objects and ensures their proper configuration.

"""

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib imports
from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import os, time

# Third-party imports

# Bokeh imports
from .document import Document
from .resources import Resources
from .client import DEFAULT_SERVER_URL, DEFAULT_SESSION_ID, ClientSession, ClientConnection

#-----------------------------------------------------------------------------
# Globals and constants
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Local utilities
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------

class State(object):
    """ Manage state related to controlling Bokeh output.

    Attributes:
        document (:class:`bokeh.document.Document`): a default document to use

        file (dict) : default filename, resources, etc. for file output
            This dictionary has the following form::

                {
                    'filename'  : # filename to use when saving
                    'resources' : # resources configuration
                    'autosave'  : # whether to autosave
                    'title'     : # a title for the HTML document
                }

        notebook (bool) : whether to generate notebook output

        session (:class:`bokeh.session.Session`) : a default session for Bokeh server output

    """

    def __init__(self):
        self._connection = None # reset checks whether it's None
        self.reset()

    @property
    def document(self):
        return self._document

    @property
    def file(self):
        return self._file

    @property
    def notebook(self):
        return self._notebook

    @property
    def connection(self):
        return self._connection

    def _reset_with_doc(self, doc):
        self._document = doc
        self._file = None
        self._notebook = False
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        self._session = None

    def reset(self):
        ''' Deactivate all currently active output modes.

        Subsequent calls to show() will not render until a new output mode is
        activated.

        Returns:
            None

        '''
        self._reset_with_doc(Document())

    def output_document(self, doc):
        """ Output to a document.

        Args:
            doc (Document) : the document curdoc() will return
        """
        self._reset_with_doc(doc)

    def output_file(self, filename, title="Bokeh Plot", autosave=False, mode="inline", root_dir=None):
        """ Output to a static HTML file.

        Args:
            filename (str) : a filename for saving the HTML document

            title (str, optional) : a title for the HTML document

            autosave (bool, optional) : whether to automatically save (default: False)
                If True, then Bokeh plotting APIs may opt to automatically
                save the file more frequently (e.g., after any plotting
                command). If False, then the file is only saved upon calling
                :func:`show` or :func:`save`.

            mode (str, optional) : how to include BokehJS (default: ``'inline'``)
                One of: ``'inline'``, ``'cdn'``, ``'relative(-dev)'`` or
                ``'absolute(-dev)'``. See :class:`bokeh.resources.Resources` for more details.

            root_dir (str, optional) :  root directory to use for 'absolute' resources. (default: None)
            This value is ignored for other resource types, e.g. ``INLINE`` or
            ``CDN``.

        .. warning::
            This output file will be overwritten on every save, e.g., each time
            show() or save() is invoked, or any time a Bokeh plotting API
            causes a save, if ``autosave`` is True.

        """
        self._file = {
            'filename'  : filename,
            'resources' : Resources(mode=mode, root_dir=root_dir),
            'autosave'  : autosave,
            'title'     : title,
        }

        if os.path.isfile(filename):
            logger.info("Session output file '%s' already exists, will be overwritten." % filename)

    # TODO update output_notebook to match output_server
    def output_notebook(self, url=None, docname=None, session=None, name=None):
        """ Generate output in Jupyter/IPython notebook cells.

        Args:
            url (str, optional) : URL of the Bokeh server (default: "default")
                If "default", then ``session.DEFAULT_SERVER_URL`` is used.

            docname (str) : Name of document to push on Bokeh server
                Any existing documents with the same name will be overwritten.

            session (Session, optional) : An explicit session to use (default: None)
                If None, a new default session is created.

            name (str, optional) : A name for the session
                If None, the server URL is used as the name

        Returns:
            None

        """
        self._notebook = True

        if session or url or name:
            if docname is None:
                docname = "IPython Session at %s" % time.ctime()
            self.output_server(docname, url=url, session=session, name=name)

    def output_server(self, sessionid=DEFAULT_SESSION_ID, url="default", clear=True):
        """ Sync curdoc() to a Bokeh server.

        Args:
            sessionid (str) : Name of session to push on Bokeh server
                Any existing session with the same name will be overwritten.
                Use None to generate a random session ID.

            url (str, optional) : URL of the Bokeh server (default: "default")
                If "default" use the default localhost URL.

            clear (bool, optional) : Whether to clear the document (default: True)
                If True, an existing server document will be cleared of any
                existing objects.

        Returns:
            None

        .. warning::
            Calling this function will replace any existing document in the named session.

        """
        if url == "default":
            url = DEFAULT_SERVER_URL

        self._connection = ClientConnection(url=url)
        self._session = ClientSession(self._connection, sessionid)
        self._document = self._session.document

        if clear:
            self._document.clear()
