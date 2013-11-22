
"""Support functionality for the Komodo doc build."""

import os
from os.path import abspath, dirname, exists, join, normpath
import posixpath
import sys
from ConfigParser import SafeConfigParser
from urlparse import urlparse

from mklib import Task

try:
    from xml.etree import cElementTree as ET
except ImportError:
    try:
        import cElementTree as ET
    except ImportError:
        try:
            from elementtree import ElementTree as ET
        except ImportError:
            # Use our local limited pure-python ElementTree.
            etree_dir = join(dirname(dirname(abspath(__file__))),
                             "externals", "elementtree")
            sys.path.insert(0, etree_dir)
            from elementtree import ElementTree as ET
            sys.path.remove(etree_dir)

html5lib_dir = join(dirname(dirname(abspath(__file__))),
                    "externals", "html5lib")
six_dir = None
if not exists(html5lib_dir):
    # Try getting it from Komodo's contrib directory
    html5lib_dir = normpath(join(dirname(abspath(__file__)), "..", "..", "..",
                                 "..", "..", "contrib", "html5lib"))
    six_dir = normpath(join(dirname(html5lib_dir), "six"))
    sys.path.insert(0, six_dir)
sys.path.insert(0, html5lib_dir)

try:
    import html5lib
    from html5lib import treebuilders, treewalkers
    from html5lib.serializer.htmlserializer import HTMLSerializer
finally:
    sys.path.remove(html5lib_dir)
    if six_dir:
        sys.path.remove(six_dir)


class ManifestParser(SafeConfigParser):
    def optionxform(self, optionstr):
        """Revert annoying base behaviour of ConfigParser to *lowercase*
        everything. Jeesh.
        """
        return optionstr


class _KomodoDocTask(Task):
    # Base class for many Makefile.py tasks
    @property
    def htdocs_dir(self):
        return join(self.cfg.build_dir, "htdocs")


def app_filter_html_path_inplace(path, filters, log=None):
    """Filter the given HTML file (in-place) based on "app-*" class
    attributes.
    
    For example, the HTML might contain something like:
        <div class="app-ide">
            ...ide info...
        </div>
        <div class="app-edit">
            ...edit info...
        </div>
    If there are no filters, then the HTML is not changed. If the filters
    include "ide" but not "edit", then the ide div remains and the
    edit div is removed.
    """
    if not filters:
        return
    if log:
        log("app-filter `%s'", path)

    # Parse the HTML file.
    treebuilder = treebuilders.getTreeBuilder("etree", ET)
    p = html5lib.HTMLParser(tree=treebuilder)
    f = open(path)
    tree = p.parse(f)
    f.close()

    # Filter out the unwanted elements.
    filtered = False
    assert isinstance(filters, set)
    for elem in tree.getiterator():
        indeces_to_drop = []
        for i, child in enumerate(elem.getchildren()):
            if _should_drop_elem(child, filters, "class", "app-"):
                indeces_to_drop.insert(0, i)
                filtered = True
                if log:
                    tag_str = "<%s" % child.tag
                    if child.attrib:
                        for n,v in child.attrib.items():
                            tag_str += ' %s="%s"' % (n, v)
                    tag_str += ">"
                    if len(tag_str) > 50:
                        tag_str = tag_str[:47] + '...'
                    log("... filter out %s", tag_str)
        for idx in indeces_to_drop:
            del elem[idx]

    # Write out any changes.
    if filtered:
        walker = treewalkers.getTreeWalker("etree", ET)
        stream = walker(tree)
        s = HTMLSerializer()
        outputter = s.serialize(stream)
        content = ''.join(list(outputter))
        f = open(path, 'w')
        f.write("""<!DOCTYPE html>
""")
        try:
            f.write(content)
        finally:
            f.close()


def app_filter_xml_path_inplace(path, filters, log=None):
    """Filter the given XML file (in-place) based on "*" flags
    attributes.
    
    For example, the HTML might contain something like:
        <sometag flags="ide">
            ...ide info...
        </sometag>
        <sometag flags="app-edit">
            ...edit info...
        </sometag>
    If there are no filters, then the XML is not changed. If the filters
    include "ide" but not "edit", then the ide tag remains and the
    edit tag is removed.
    """
    if not filters:
        return
    if log:
        log("app-filter `%s'", path)

    # Parse the XML file.
    f = open(path)
    tree = ET.parse(f)
    f.close()
    
    # Filter out the unwanted elements.
    filtered = False
    assert isinstance(filters, set)
    for elem in tree.getiterator():
        indeces_to_drop = []
        for i, child in enumerate(elem.getchildren()):
            if _should_drop_elem(child, filters, "flags", None):
                indeces_to_drop.insert(0, i)
                filtered = True
                if log:
                    tag_str = "<%s" % child.tag
                    if child.attrib:
                        for n,v in child.attrib.items():
                            tag_str += ' %s="%s"' % (n, v)
                    tag_str += ">"
                    if len(tag_str) > 50:
                        tag_str = tag_str[:47] + '...'
                    log("... filter out %s", tag_str)
        for idx in indeces_to_drop:
            del elem[idx]

    # Write out any changes.
    if filtered:
        content = ET.tostring(tree.getroot())
        f = open(path, 'w')
        try:
            f.write(content)
        finally:
            f.close()


def _should_drop_elem(elem, filters, attrname, prefix):
    # Used by app_filter_{xml|html}_inplace().
    markers = [c for c in elem.get(attrname, "").split()
               if not prefix or c.startswith(prefix)]
    if markers:
        flags = set()
        for marker in markers:
            if prefix:
                marker = marker[len(prefix):]
            flags.update( marker.split('-') )
        matches = filters.intersection(flags)
        if not matches:
            return True
    return False


def independentize_html_path(src, dst, css_dir=None, log=None):
    """Process the `src' HTML path to `dst' making it independent.
    
    - favicon links are removed
    - CSS references are updated (if `css_dir' is given), else removed.
    - Relative links are de-linkified.
    """
    if log:
        log.info("independentize %s %s", src, dst)

    # Parse the HTML file.
    treebuilder = treebuilders.getTreeBuilder("etree", ET)
    p = html5lib.HTMLParser(tree=treebuilder)
    f = open(src)
    tree = p.parse(f)
    f.close()

    # - Drop favicon links.
    # - Update or drop CSS links.
    head = tree.find("head")
    for link in head.getchildren()[:]:
        if link.tag != "link":
            continue
        rel = link.get("rel", "").split()
        if "icon" in rel: # this is a favicon link
            if log:
                log.debug("%s: remove <link rel='%s'/>", dst,
                          link.get("rel"))
            head.remove(link)
        if "stylesheet" in rel: # this is a css ref
            if css_dir:  # update the css dir
                href = link.get("href")
                href = posixpath.join(css_dir, posixpath.basename(href))
                link.set("href", href)
                if log:
                    log.debug("%s: update to <link href='%s'/>", dst, href)
            else:
                if log:
                    log.debug("%s: remove <link href='%s'/>", dst,
                              link.get("href"))
                head.remove(link)

    # De-linkify local references within the full docset.
    # TODO: Eventually would like to normalize these to point
    # to online version of the docs.
    body = tree.find("body")
    for elem in body.getiterator():
        if elem.tag != "a":
            continue
        if not elem.get("href"):
            continue
        href = elem.get("href")
        scheme, netloc, path, params, query, fragment = urlparse(href)
        if scheme or netloc: # externals href
            continue
        if path:
            if log:
                log.debug("%s: de-linkify <a href='%s'>", dst, href)
            elem.tag = "span"  # de-linkify
    
    # Write out massaged doc.
    walker = treewalkers.getTreeWalker("etree", ET)
    stream = walker(tree)
    s = HTMLSerializer()
    outputter = s.serialize(stream)
    content = ''.join(list(outputter))
    f = open(dst, 'w')
    try:
        f.write(content)
    finally:
        f.close()



# Recipe: paths_from_path_patterns (0.3.7)
def _should_include_path(path, includes, excludes):
    """Return True iff the given path should be included."""
    from os.path import basename
    from fnmatch import fnmatch

    base = basename(path)
    if includes:
        for include in includes:
            if fnmatch(base, include):
                try:
                    log.debug("include `%s' (matches `%s')", path, include)
                except (NameError, AttributeError):
                    pass
                break
        else:
            try:
                log.debug("exclude `%s' (matches no includes)", path)
            except (NameError, AttributeError):
                pass
            return False
    for exclude in excludes:
        if fnmatch(base, exclude):
            try:
                log.debug("exclude `%s' (matches `%s')", path, exclude)
            except (NameError, AttributeError):
                pass
            return False
    return True

_NOT_SPECIFIED = ("NOT", "SPECIFIED")
def paths_from_path_patterns(path_patterns, files=True, dirs="never",
                             recursive=True, includes=[], excludes=[],
                             on_error=_NOT_SPECIFIED):
    """paths_from_path_patterns([<path-patterns>, ...]) -> file paths

    Generate a list of paths (files and/or dirs) represented by the given path
    patterns.

        "path_patterns" is a list of paths optionally using the '*', '?' and
            '[seq]' glob patterns.
        "files" is boolean (default True) indicating if file paths
            should be yielded
        "dirs" is string indicating under what conditions dirs are
            yielded. It must be one of:
              never             (default) never yield dirs
              always            yield all dirs matching given patterns
              if-not-recursive  only yield dirs for invocations when
                                recursive=False
            See use cases below for more details.
        "recursive" is boolean (default True) indicating if paths should
            be recursively yielded under given dirs.
        "includes" is a list of file patterns to include in recursive
            searches.
        "excludes" is a list of file and dir patterns to exclude.
            (Note: This is slightly different than GNU grep's --exclude
            option which only excludes *files*.  I.e. you cannot exclude
            a ".svn" dir.)
        "on_error" is an error callback called when a given path pattern
            matches nothing:
                on_error(PATH_PATTERN)
            If not specified, the default is look for a "log" global and
            call:
                log.error("`%s': No such file or directory")
            Specify None to do nothing.

    Typically this is useful for a command-line tool that takes a list
    of paths as arguments. (For Unix-heads: the shell on Windows does
    NOT expand glob chars, that is left to the app.)

    Use case #1: like `grep -r`
      {files=True, dirs='never', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield nothing
        script PATH*    # yield all files matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #2: like `file -r` (if it had a recursive option)
      {files=True, dirs='if-not-recursive', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #3: kind of like `find .`
      {files=True, dirs='always', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files and dirs recursively under DIR
                        # (including DIR)
        script -r PATH* # yield files and dirs matching PATH* and recursively
                        # under dirs; if none, call on_error(PATH*)
                        # callback
    """
    from os.path import basename, exists, isdir, join
    from glob import glob

    assert not isinstance(path_patterns, basestring), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    GLOB_CHARS = '*?['

    for path_pattern in path_patterns:
        # Determine the set of paths matching this path_pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in path_pattern:
                paths = glob(path_pattern)
                break
        else:
            paths = exists(path_pattern) and [path_pattern] or []
        if not paths:
            if on_error is None:
                pass
            elif on_error is _NOT_SPECIFIED:
                try:
                    log.error("`%s': No such file or directory", path_pattern)
                except (NameError, AttributeError):
                    pass
            else:
                on_error(path_pattern)

        for path in paths:
            if isdir(path):
                # 'includes' SHOULD affect whether a dir is yielded.
                if (dirs == "always"
                    or (dirs == "if-not-recursive" and not recursive)
                   ) and _should_include_path(path, includes, excludes):
                    yield path

                # However, if recursive, 'includes' should NOT affect
                # whether a dir is recursed into. Otherwise you could
                # not:
                #   script -r --include="*.py" DIR
                if recursive and _should_include_path(path, [], excludes):
                    for dirpath, dirnames, filenames in os.walk(path):
                        dir_indeces_to_remove = []
                        for i, dirname in enumerate(dirnames):
                            d = join(dirpath, dirname)
                            if dirs == "always" \
                               and _should_include_path(d, includes, excludes):
                                yield d
                            if not _should_include_path(d, [], excludes):
                                dir_indeces_to_remove.append(i)
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path



