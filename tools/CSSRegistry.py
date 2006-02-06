from DateTime import DateTime
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.CMFCore.utils import getToolByName

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.ResourceRegistries import config
from Products.ResourceRegistries import permissions
from Products.ResourceRegistries.interfaces import ICSSRegistry
from Products.ResourceRegistries.tools.BaseRegistry import BaseRegistryTool
from Products.ResourceRegistries.tools.BaseRegistry import Resource

import re

class Stylesheet(Resource):
    security = ClassSecurityInfo()

    def __init__(self, id, **kwargs):
        Resource.__init__(self, id, **kwargs)
        self._data['media'] = kwargs.get('media', '')
        self._data['rel'] = kwargs.get('rel', 'stylesheet')
        self._data['title'] = kwargs.get('title', '')
        self._data['rendering'] = kwargs.get('rendering', 'import')

    security.declarePublic('getMedia')
    def getMedia(self):
        result = self._data['media']
        if result == "":
            result = None
        return result

    security.declareProtected(permissions.ManagePortal, 'setMedia')
    def setMedia(self, media):
        self._data['media'] = media

    security.declarePublic('getRel')
    def getRel(self):
        return self._data['rel']

    security.declareProtected(permissions.ManagePortal, 'setRel')
    def setRel(self, rel):
        self._data['rel'] = rel

    security.declarePublic('getTitle')
    def getTitle(self):
        result = self._data['title']
        if result == "":
            result = None
        return result

    security.declareProtected(permissions.ManagePortal, 'setTitle')
    def setTitle(self, title):
        self._data['title'] = title

    security.declarePublic('getRendering')
    def getRendering(self):
        return self._data['rendering']

    security.declareProtected(permissions.ManagePortal, 'setRendering')
    def setRendering(self, rendering):
        self._data['rendering'] = rendering

InitializeClass(Stylesheet)


class CSSRegistryTool(BaseRegistryTool):
    """A Plone registry for managing the linking to css files."""

    id = config.CSSTOOLNAME
    meta_type = config.CSSTOOLTYPE
    title = 'CSS Registry'

    security = ClassSecurityInfo()

    __implements__ = (BaseRegistryTool.__implements__, ICSSRegistry,)

    #
    # ZMI stuff
    #

    manage_cssForm = PageTemplateFile('www/cssconfig', config.GLOBALS)
    manage_cssComposition = PageTemplateFile('www/csscomposition', config.GLOBALS)

    manage_options = (
        {
            'label': 'CSS Registry',
            'action': 'manage_cssForm',
        },
        {
            'label': 'Merged CSS Composition',
            'action': 'manage_cssComposition',
        },
    ) + BaseRegistryTool.manage_options

    attributes_to_compare = ('getExpression', 'getCookable', 'getCacheable',
                             'getRel', 'getRendering', 'getSkinsBlacklist')
    filename_base = 'ploneStyles'
    filename_appendix = '.css'
    merged_output_prefix = ''
    cache_duration = config.CSS_CACHE_DURATION
    resource_class = Stylesheet

    #
    # Private Methods
    #

    security.declarePrivate('storeResource')
    def storeResource(self, resource):
        """Store a resource."""
        self.validateId(resource.getId(), self.getResources())
        resources = list(self.getResources())
        if len(resources) and resources[-1].getId() == 'ploneCustom.css':
            # ploneCustom.css should be the last item
            resources.insert(-1, resource)
        else:
            resources.append(resource)
        self.resources = tuple(resources)
        self.cookResources()

    security.declarePrivate('clearStylesheets')
    def clearStylesheets(self):
        self.clearResources()

    security.declarePrivate('compareResources')
    def compareResources(self, sheet1, sheet2 ):
        """Check if two resources are compatible."""
        for attr in self.attributes_to_compare:
            if getattr(sheet1, attr)() != getattr(sheet2, attr)():
                return False
            if 'alternate' in sheet1.getRel():
                return False
                # this part needs a test
        return True

    security.declarePrivate('finalizeResourceMerging')
    def finalizeResourceMerging(self, resource, previtem):
        """Finalize the resource merging with the previous item."""
        if previtem.getMedia() != resource.getMedia():
            previtem.setMedia(None)

    def _compressCSS(self, content):
        # currently unused code for CSS compression
        # strip whitespace
        content = '\n'.join([x.strip() for x in content.split('\n')])
        
        # remove comment contents
        s1 = re.compile('/\*.*?\*/', re.DOTALL)
        content = s1.sub('/**/', content)
        
        # remove lines with only comments
        s2 = re.compile('^/\*\*/$', re.MULTILINE)
        content = s2.sub('', content)
        
        #remove multiple newlines
        s3 = re.compile('\n+')
        content = s3.sub('\n', content)

        return content

    security.declarePrivate('finalizeContent')
    def finalizeContent(self, resource, content):
        """Finalize the resource content."""
        m = resource.getMedia()
        if m:
            content = '@media %s {\n%s\n}\n' % (m, content)

        #return self._compressCSS(content)
        return content

    #
    # ZMI Methods
    #

    security.declareProtected(permissions.ManagePortal, 'manage_addStylesheet')
    def manage_addStylesheet(self, id, expression='', media='',
                             rel='stylesheet', title='', rendering='import',
                             enabled=False, cookable=True, skinsblacklist='',
                             REQUEST=None):
        """Register a stylesheet from a TTW request."""
        self.registerStylesheet(id, expression, media, rel, title,
                                rendering, enabled, cookable, skinsblacklist)
        if REQUEST:
            REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected(permissions.ManagePortal, 'manage_saveStylesheets')
    def manage_saveStylesheets(self, REQUEST=None):
        """Save stylesheets from the ZMI.

        Updates the whole sequence. For editing and reordering.
        """
        debugmode = REQUEST.get('debugmode',False)
        self.setDebugMode(debugmode)
        records = REQUEST.get('stylesheets')
        records.sort(lambda a, b: a.sort - b.sort)
        self.resources = ()
        stylesheets = []
        for r in records:
            stylesheet = Stylesheet(r.get('id'),
                                    expression=r.get('expression', ''),
                                    media=r.get('media', ''),
                                    rel=r.get('rel', 'stylesheet'),
                                    title=r.get('title', ''),
                                    rendering=r.get('rendering', 'import'),
                                    enabled=r.get('enabled', False),
                                    cookable=r.get('cookable', False),
                                    cacheable=r.get('cacheable', False),
                                    skinsblacklist=r.get('skinsblacklist', '')
                                    )
            stylesheets.append(stylesheet)
        self.resources = tuple(stylesheets)
        self.cookResources()
        if REQUEST:
            REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected(permissions.ManagePortal, 'manage_removeStylesheet')
    def manage_removeStylesheet(self, id, REQUEST=None):
        """Remove stylesheet from the ZMI."""
        self.unregisterResource(id)
        if REQUEST:
            REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    #
    # Protected Methods
    #

    security.declareProtected(permissions.ManagePortal, 'registerStylesheet')
    def registerStylesheet(self, id, expression='', media='',
                                 rel='stylesheet', title='',
                                 rendering='import',  enabled=1,
                                 cookable=True, skinsblacklist=''):
        """Register a stylesheet."""
        stylesheet = Stylesheet(id,
                                expression=expression,
                                media=media,
                                rel=rel,
                                title=title,
                                rendering=rendering,
                                enabled=enabled,
                                cookable=cookable,
                                skinsblacklist=skinsblacklist)
        self.storeResource(stylesheet)

    security.declareProtected(permissions.ManagePortal, 'getRenderingOptions')
    def getRenderingOptions(self):
        """Rendering methods for use in ZMI forms."""
        return config.CSS_RENDER_METHODS

    security.declareProtected(permissions.View, 'getContentType')
    def getContentType(self):
        """Return the registry content type."""
        return 'text/css'


InitializeClass(CSSRegistryTool)
