#!/usr/bin/env python
# Copyright (c) 2007 ActiveState Software Inc.
# See LICENSE.txt for license details.
# Authors:
#   Todd Whiteman (ToddW@ActiveState.com)
#   Trent Mick (adapted for independence from codeintel2 package)

r"""api2html -- Convert a Komodo API catalog to an HTML page."""

__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import isfile, isdir, exists, dirname, abspath, splitext, join
import sys
import re
from optparse import OptionParser
import logging

try:
    from xml.etree import cElementTree as ET
except ImportError:
    try:
        import cElementTree as ET
    except ImportError:
        from elementtree import ElementTree as ET



class Error(Exception):
    pass




#---- module API

def api2html(api_catalog_path, html_path=None,
             toc_path=None, css_paths=None, title=None,
             log=None):
    """Generate HTML output for the given API Catalog.
    
    Also optionally generate toc.xml output for this HTML file (if
    'toc_path' is given). Any paths given in "css_paths" will result
    in <style> imports in the generated HTML.
    """
    if log:
        out_str = html_path and html_path or "<stdout>"
        if toc_path:
            out_str += ", %s" % toc_path
        log("api2html %s -> %s", api_catalog_path, out_str)

    # Setup output streams
    if not html_path:
        html_stream = sys.stdout
        if toc_path:
            raise Error("cannot generate TOC output without an "
                        "HTML output file *name* (i.e. not stdout)")
        html_href = None
    else:
        html_stream = open(html_path, 'w')
        html_href = os.path.basename(html_path)
    toc_stream = toc_path and open(toc_path, 'w') or None

    try:
        # Get the tree to convert to HTML.
        if '#' in api_catalog_path:
            path, anchor = api_catalog_path.rsplit('#', 1)
        else:
            path = api_catalog_path
            anchor = None
        tree = ET.parse(path).getroot()
        assert tree.get("version") == "2.0"
        elem = _elem_from_tree_and_anchor(tree, anchor)
        
        # Convert to HTML.
        _generate_from_elem(elem, title, html_stream, html_href,
                            toc_stream, css_paths)
    finally:
        if html_stream != sys.stdout:
            html_stream.close()
        if toc_stream:
            toc_stream.close()
    


#---- internal HTML generation code

def _elemCompare(elem1, elem2):
    #return cmp(elem1.get("name"), elem2.get("name"))
    name1, name2 = elem1.get("name"), elem2.get("name")
    if name1:
        name1 = name1.lower()
    if name2:
        name2 = name2.lower()
    return cmp(name1, name2)

def _convertDocToHtml(html, elem, cls="doc"):
    doc = elem.get('doc')
    if doc:
        p = ET.SubElement(html, "p", {"class":cls})
        p.text = doc

def _convertArgumentToHtml(html, elem):
    elem_name = elem.get("name")
    elem_type = elem.get('ilk') or elem.tag
    para = ET.SubElement(html, "p")
    span = ET.SubElement(para, "span", {"class": elem_type})
    span.text = elem_name
    citdl = elem.get("citdl")
    if citdl:
        citdl_span = ET.SubElement(para, "span", {"class": "citdl"})
        citdl_span.text = " - %s" % (citdl, )
        _convertDocToHtml(html, elem, "doc_for_argument")

def _convertFunctionToHtml(html, elem):
    elem_name = elem.get("name")
    elem_type = elem.get('ilk') or elem.tag
    div = ET.SubElement(html, "div", {"class": "function"})
    span = ET.SubElement(div, "span", {"class": elem_type})
    codeElements = elem.get('attributes', "").split(" ")
    isCtor = False
    if "__ctor__" in codeElements:
        isCtor = True
        codeElements.remove("__ctor__")
    #else:
    #    codeElements.push("void")
    if not isCtor:
        #span.text = "%s %s %s" % (elem_type, " ".join(codeElements),
        #                          elem.get('signature') or elem_name + "()")
        span.text = "%s %s" % (" ".join(codeElements),
                               elem.get('signature') or elem_name + "()")
        _convertDocToHtml(div, elem)
    else:
        span.text = "%s" % (elem.get('signature') or elem_name + "()")

    function_arguments = [ x for x in elem if x.get("ilk") == "argument" and (x.get("citdl") or x.get("doc")) ]
    if function_arguments:
        arg_div = ET.SubElement(div, "div", {"class": "function_arguments"})
        arg_div.text = "Arguments"
        for arg_elem in function_arguments:
            #sys.stderr.write("function arg: %r\n" % (arg_elem))
            _convertArgumentToHtml(arg_div, arg_elem)
    returns = elem.get('returns')
    if returns:
        ret_div = ET.SubElement(div, "div", {"class": "function_returns"})
        ret_p = ET.SubElement(ret_div, "p")
        ret_p.text = "Returns - "
        span = ET.SubElement(ret_p, "span", {"class": "function_returns"})
        span.text = returns

def _convertVariableToHtml(html, elem):
    """Convert cix elements into html documentation elements

    Generally this will operate on blobs and variables with citdl="Object".
    """
    elem_name = elem.get("name")
    elem_type = elem.get('ilk') or elem.tag
    div = ET.SubElement(html, "div", {"class": "variable"})
    para = ET.SubElement(div, "p")
    span = ET.SubElement(para, "span", {"class": elem_type})
    span.text = elem_name
    citdl = elem.get("citdl")
    if citdl:
        citdl_span = ET.SubElement(para, "span", {"class": "variable_cidtl"})
        citdl_span.text = " - %s" % (citdl, )
    _convertDocToHtml(div, elem)

def _convertClassToHtml(html, elem):
    html = ET.SubElement(html, "div", {"class": "class"})
    span = ET.SubElement(html, "span", {"class": "class"})
    span.text = "class %s" % (elem.get("name"))
    _convertDocToHtml(html, elem)
    variables = sorted([ x for x in elem if x.tag == "variable" ], _elemCompare)
    functions = sorted([ x for x in elem if x.get("ilk") == "function" ], _elemCompare)
    constructors = [ x for x in functions if "__ctor__" in x.get("attributes", "").split(" ") ]
    if constructors:
        h3 = ET.SubElement(html, "h3", {"class": "class"})
        h3.text = "Constructor"
        div = ET.SubElement(html, "div", {"class": "class_variables"})
        for ctor_elem in constructors:
            functions.remove(ctor_elem)
            _convertFunctionToHtml(div, ctor_elem)
            ET.SubElement(div, "hr", {"class": "constructor_separator"})
    if variables:
        h3 = ET.SubElement(html, "h3", {"class": "class"})
        h3.text = "Class variables"
        div = ET.SubElement(html, "div", {"class": "class_variables"})
        for var_elem in variables:
            _convertVariableToHtml(div, var_elem)
            ET.SubElement(div, "hr", {"class": "variable_separator"})
    if functions:
        h3 = ET.SubElement(html, "h3", {"class": "class"})
        h3.text = "Class functions"
        div = ET.SubElement(html, "div", {"class": "class_functions"})
        for var_elem in functions:
            _convertFunctionToHtml(div, var_elem)
            ET.SubElement(div, "hr", {"class": "function_separator"})

def _convertScopeToHtml(html, scope, namespace, ns_elems):
    name = scope.get('name')
    if namespace:
        namespace += ".%s" % (name)
    else:
        namespace = name
    #sys.stderr.write("namespace: %s\n" % (namespace, ))
    a_href = ET.SubElement(html, "a", name=namespace)
    # This is to fix a bug where firefox displays all elements with the same
    # css style as set in "a", like underline etc...
    a_href.text = " "

    div = ET.SubElement(html, "div", {"name": namespace, "class": "namespace"})
    ns_elems.append((namespace, div))
    h2 = ET.SubElement(div, "h2", {"name": namespace, "class": "namespace"})
    h2.text = namespace
    _convertDocToHtml(div, scope, "doc_for_namespace")

    variables = set([ x for x in scope if x.tag == "variable" ])
    functions = set([ x for x in scope if x.get("ilk") == "function" ])
    classes = set([ x for x in scope if x.get("ilk") == "class" ])
    subscopes = set([ x for x in variables if x.get("citdl") == "Object" ])
    variables.difference_update(subscopes)

    if variables:
        h3 = ET.SubElement(div, "h3")
        h3.text = "Variables"
        for elem in sorted(variables, _elemCompare):
            _convertVariableToHtml(div, elem)
            ET.SubElement(div, "hr", {"class": "variable_separator"})
    if functions:
        h3 = ET.SubElement(div, "h3")
        h3.text = "Functions"
        for elem in sorted(functions, _elemCompare):
            _convertFunctionToHtml(div, elem)
            ET.SubElement(div, "hr", {"class": "function_separator"})
    if classes:
        h3 = ET.SubElement(div, "h3")
        h3.text = "Classes"
        for elem in sorted(classes, _elemCompare):
            _convertClassToHtml(div, elem)
            ET.SubElement(div, "hr", {"class": "class_separator"})
    for elem in sorted(subscopes, _elemCompare):
        _convertScopeToHtml(div, elem, namespace, ns_elems)


# Taken from codeintel2.tree, modified to ensure it keeps all
# existing text and tail data. Since this is used on generated
# xml content, there is no need to worry about existing newlines
# and whitespace, as there will be none existing at this point.
def _pretty_tree_from_tree(tree, indent_width=2):
    """Add appropriate .tail and .text values to the given tree so that
    it will have a pretty serialization.

    Presumption: This is a CIX 2.0 tree.
    """
    INDENT = ' '*indent_width

    def _prettify(elem, indent_level=0):
        if elem: # i.e. elem has child elements
            elem.text = '\n' + INDENT*(indent_level+1) + (elem.text or "")
            for child in elem:
                _prettify(child, indent_level+1)
            elem[-1].tail = (elem[-1].tail or "") + '\n' + INDENT*indent_level
            elem.tail = (elem.tail or "") + '\n' + INDENT*indent_level
        else:
            #elem.text = None
            elem.tail = (elem.tail or "") + '\n' + INDENT*indent_level

    _prettify(tree)
    return tree

def _remove_priv_elems(elem):
    """Remove all the private cix elements."""
    parent_map = dict((c, p) for p in elem.getiterator() for c in p)
    for node in list(elem.getiterator()):
        attributes = node.get("attributes", "").split(" ")
        if "private" in attributes or "__hidden__" in attributes:
            # Remove it
            parentnode = parent_map.get(node)
            if parentnode is not None:
                parentnode.remove(node)

def _generate_from_elem(elem, title, html_stream, html_href,
                        toc_stream, css_paths):
    # Header.
    html = ET.Element("html")
    head = ET.SubElement(html, "head")
    if title:
        ET.SubElement(head, "title").text = title
    for css_path in css_paths:
        ET.SubElement(head, "link", rel="stylesheet", type="text/css",
                      href=css_path)
    body = ET.SubElement(html, "body")
    body_div = ET.SubElement(body, "div", {"id": "body"})

    # Content.
    ns_elems = []
    _remove_priv_elems(elem) # b/c they are not externally visible
    if elem.tag == "file":
        for child in elem:
            for subchild in child:
                _convertScopeToHtml(body_div, subchild, "", ns_elems)
    else:
        _convertScopeToHtml(body_div, elem, "", ns_elems)

    # Footer.
    footer_div = ET.SubElement(body, "div", {"id": "footer"})
    _pretty_tree_from_tree(html)

    # Write the HTML.
    tree = ET.ElementTree(html)
    xhtml_header = '<?xml version="1.0"?>\n' \
                   '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" ' \
                   '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'
    html_stream.write(xhtml_header)
    tree.write(html_stream)

    # Write the TOC XML output.
    if toc_stream:
        toc = ET.Element("node", name=title, link=html_href)
        for ns, elem in ns_elems:
            sub_node = ET.SubElement(toc, "node", name=ns,
                                     link="%s#%s" % (html_href, ns))

        _pretty_tree_from_tree(toc)
        tree = ET.ElementTree(toc)
        tree.write(toc_stream)




#---- internal support stuff

def _blobs_from_tree(tree):
    for file_elem in tree:
        for blob in file_elem:
            yield blob

def _elem_from_tree_and_anchor(tree, anchor):
    if anchor is None:
        assert tree.tag == "codeintel"
        return tree.getchildren()[0]

    # Lookup the anchor in the codeintel CIX tree.
    lpath = re.split(r'\.|::', anchor)
    for elem in _blobs_from_tree(tree):
        # Generally have 3 types of codeintel trees:
        # 1. single-lang file: one <file>, one <blob>
        # 2. multi-lang file: one <file>, one or two <blob>'s
        # 3. CIX stdlib/catalog file: possibly multiple
        #    <file>'s, likely multiple <blob>'s
        # Allow the first token to be the blob name or lang.
        # (This can sometimes be weird, but seems the most
        # convenient solution.)
        if lpath[0] in (elem.get("name"), elem.get("lang")):
            remaining_lpath = lpath[1:]
        else:
            remaining_lpath = lpath
        for name in remaining_lpath:
            try:
                elem = elem.names[name]
            except KeyError:
                elem = None
                break # try next lang blob
        if elem is not None:
            return elem
    else:
        raise Error("could not find `%s' definition (or blob) in `%s'"
                    % (anchor, path))



#---- mainline

def main(argv):
    usage = "usage: %prog [options] API_CATALOG_PATH"""
    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--css", dest="css_paths",
                      action="append",
                      help="add css reference file for styling"
                           " (can be used more than once)")
    parser.add_option("-o", "--html-path",
                      help="path for generated html output, defaults to stdout")
    parser.add_option("-t", "--toc-path",
                      help="path for generated toc xml file")
    parser.add_option("--title",
                      help="title text for the HTML file (and top TOC node)")
    opts, args = parser.parse_args()
    if len(args) != 1:
        parser.print_usage()
        return 1
    api_catalog_path = args[0]

    api2html(api_catalog_path, html_path=opts.html_path,
             toc_path=opts.toc_path, css_paths=opts.css_paths,
             title=opts.title)
    return 0


if __name__ == "__main__":
    logging.basicConfig()
    sys.exit(main(sys.argv))
