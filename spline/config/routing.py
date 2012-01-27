"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
import os

from routes import Mapper, url_for
from routes.util import controller_scan as dir_controller_scan
from pylons.i18n.translation import get_lang

from spline.lib.plugin.load import run_hooks
from spline.i18n import Translator

class I18nMapper(Mapper):
    def connect(self, *args, **kwargs):
        translator_class = kwargs.pop('i18n_class', None)
        super(I18nMapper, self).connect(*args, **kwargs)
        for lang in Translator.available_languages():
            try:
                name, url = args
            except ValueError:
                name = None
                (url, ) = args
            if translator_class:
                url_parts = ['', lang]
                _ = translator_class(languages=[lang])
                for part in url.split('/'):
                    if not part:
                        pass
                    elif '{' not in part and '*' not in part:
                        url_parts.append(_(part, context='url').encode('utf-8'))
                    else:
                        url_parts.append(part)
                translated_url = '/'.join(url_parts)
            else:
                if url == '/':
                    url = ''
                translated_url = '/' + lang + url
            kwargs['_lang'] = lang
            if name:
                name = lang + '!!' + name
            super(I18nMapper, self).connect(name, translated_url, **kwargs)

    def generate(self, route=None, *args, **kwargs):
        try:
            lang = get_lang()[0]
        except TypeError:
            lang = None
        else:
            kwargs.setdefault('_lang', lang)
        if route and lang and '!!' not in route.name:
            return url_for(kwargs['_lang'] + '!!' + route.name, *args, **kwargs)
        else:
            return super(I18nMapper, self).generate(*args, **kwargs)

def controller_scan(config, directory):
    """Looks for a controller in the plugin list, defaulting to the usual
    Routes directory scan if it isn't found."""

    controllers = config['spline.plugins.controllers'].keys()
    controllers.extend(dir_controller_scan(directory))
    return controllers

def make_map(config, content_dirs=[]):
    """Create, configure and return the routes Mapper"""
    map = I18nMapper(
        controller_scan=lambda directory: controller_scan(config, directory),
        directory=config['pylons.paths']['controllers'],
        always_scan=config['debug'])
    map.minimization = False

    # Content files get explicitly mapped so we don't have to pull any cheap
    # tricks like looking for them in a 404 handler.  We do them first so
    # controllers can't be clobbered by bad choices of filenames
    for content_dir in content_dirs:
        for root, dirs, files in os.walk(content_dir):
            for name in files:
                localpath = os.path.join(root, name)
                webpath, ext = os.path.splitext(localpath)

                # Skip over hidden files.
                # For now, also require a .html extension.
                if webpath[0] == '.' or ext != '.html':
                    continue

                # Use the full path as a route name so url() can easily route
                # to a static page
                map.connect('/' + os.path.relpath(webpath, content_dir),
                            '/' + os.path.relpath(webpath, content_dir),
                            controller='main', action='content', path=localpath)

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    map.connect('/css', controller='main', action='css')
    map.connect('/cron', controller='main', action='cron')

    # Allow plugins to map routes without the below defaults clobbering them
    run_hooks('routes_mapping', config=config, map=map)

    map.connect('/', controller='main', action='index')

    return map
