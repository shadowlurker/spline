import ast
import itertools
from StringIO import StringIO
from mako.template import Template
import mako.ext.babelplugin

_args = "message plural n context comment".split()

def extract_python(fileobj, keywords, comment_tags, options):
    return extract_from_string(fileobj.read(), keywords, comment_tags, options)

def extract_mako(fileobj, keywords, comment_tags, options):
    template = Template(
            fileobj.read(),
            input_encoding='utf-8',
            output_encoding='utf-8',
        )
    # We need line numbers that correspond to the mako file.
    # Mako does this by including "# SOURCE LINE xxx" comments in the file;
    # use these to build a line number map
    linenomap = [0]
    lineno = 0
    for line in template.code.splitlines():
        emptystring, sep, number = line.strip().partition("# SOURCE LINE ")
        if not emptystring and sep:
            try:
                lineno = int(number)
            except ValueError:
                pass
        linenomap.append(lineno)
    # Finally, do the actual extracting
    fileobj = StringIO(template.code)
    messages = extract_python(fileobj, keywords, comment_tags, options)
    for lineno, funcname, message, comments in messages:
        yield linenomap[lineno], funcname, message, comments

def extract_from_string(string, keywords, comment_tags, options):
    tree = compile(
            string,
            filename="<input>",
            mode='exec',
            flags=ast.PyCF_ONLY_AST,
            dont_inherit=True,
        )
    return from_ast(tree, keywords, options, [])

def from_ast(node, keywords, options, comments):
    if isinstance(node, ast.Call):
        funcname = get_funcname(node.func)
        if funcname in keywords:
            params = {}
            for name, param in itertools.chain(
                    zip(_args, node.args),
                    ((k.arg, k.value) for k in node.keywords),
                ):
                if isinstance(param, ast.Str):
                    params[name] = param
                else:
                    # not a literal string: we don't care about it,
                    # but still want to know if it's there
                    params[name] = None
            message = getstring(params.get('message'))
            context = getstring(params.get('context'))
            comment = getstring(params.get('comment'))
            if message:
                if context:
                    message = context + '|' + message
                if 'plural' in params:
                    message = (message, getstring(params.get('plural')))
                    # Cheat the function name; the extractor uses it to
                    # distinguish between singular/plural messages
                    function = 'ungettext'
                else:
                    function = 'ugettext'
                actual_comments = comments
                if comment:
                    try:
                        actual_comments += comment.splitlines()
                    except AttributeError:
                        actual_comments += comment
                yield node.lineno, function, message, comments
        elif funcname == 'connect':
            for arg in node.args:
                if isinstance(arg, ast.Str):
                    url = getstring(arg)
                    if url.startswith('/'):
                        for part in url.split('/'):
                            if part and '{' not in part and '*' not in part:
                                part = 'url|' + part
                                yield node.lineno, 'ugettext', part, []
    child_comments = []
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        child_comments.append('Py2Format')
    if isinstance(node, ast.Attribute) and node.attr == 'format':
        child_comments.append('Py3Format')
    for child in ast.iter_child_nodes(node):
        for result in from_ast(child, keywords, options, child_comments):
            yield result

def get_funcname(node):
    if isinstance(node, ast.Name):
        # gettext(...)
        return node.id
    elif isinstance(node, ast.Attribute):
        # someobject.gettext(...)
        # We only care about the attribute name
        return node.attr
    else:
        # something like (lst[0])(...)
        return None

def getstring(maybenode):
    if maybenode is None:
        return None
    else:
        return maybenode.s
