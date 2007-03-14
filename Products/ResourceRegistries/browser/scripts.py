from zope.component import getUtility

from Products.PythonScripts.standard import url_quote
from Products.Five.browser import BrowserView

from Products.ResourceRegistries.interfaces import IJSRegistry


class ScriptsView(BrowserView):
    """ Information for script rendering. """

    def registry(self):
        return getUtility(IJSRegistry)

    def skinname(self):
        return self.context.getCurrentSkinName()

    def scripts(self):
        registry = self.registry()
        registry_url = registry.absolute_url()

        scripts = registry.getEvaluatedResources(self.context)
        skinname = url_quote(self.skinname())
        result = []
        for script in scripts:
            inline = bool(script.getInline())
            if inline:
                content = registry.getInlineResource(script.getId(),
                                                     self.context)
                data = {'inline': inline,
                        'content': content}
            else:
                src = "%s/%s/%s" % (registry_url, skinname, script.getId())
                data = {'inline': inline,
                        'src': src}
            result.append(data)
        return result
