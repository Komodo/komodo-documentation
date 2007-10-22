#!/usr/bin/env python
"""Convert a toc.xml into a help-toc.rdf as used by a Mozilla Help
Browser for its Table of Contents.

Usage:
    python tocxml2helptocrdf.py .../toc.xml > .../help-toc.rdf
"""

import sys
from os.path import join, dirname, abspath, exists

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


_g_idlist = []



def add_rdf_description(rdf, node, about="urn:root"):
    """Add this thing:

      <rdf:Description about="urn:root">
        <nc:subheadings>
          <rdf:Seq>
            <rdf:li> <rdf:Description ID="welcome" nc:name="Help and Support Center" nc:link="welcome_help.xhtml"/> </rdf:li>
            ...
    """
    global _g_idlist
    if not node: # no children on this <node>
        return

    desc = ET.SubElement(rdf, "rdf:Description", about=about)
    desc.text = "\n  "; desc.tail = "\n\n"
    subheadings = ET.SubElement(desc, "nc:subheadings")
    subheadings.text = "\n    "; subheadings.tail = "\n"
    seq = ET.SubElement(subheadings, "rdf:Seq")
    seq.text = "\n      "; seq.tail = "\n  "
    for child in node:
        li = ET.SubElement(seq, "rdf:li")
        li.text = " "; li.tail = "\n      "
        id = child.get("id")
        if not id:
            id = child.get("name")
            id = id.lower().replace(' ', '_')
        assert id not in _g_idlist, \
            "duplicate id attribute %s" % id
        _g_idlist.append(id)
        child.set("IDREF", id)
        attrs = {"ID": id, "nc:name": child.get("name")}
        if child.get("link"):
            attrs["nc:link"] = child.get("link")
        lidesc = ET.SubElement(li, "rdf:Description", attrs)
        lidesc.tail = " "
    li.tail = "\n    "

    for child in node:
        add_rdf_description(rdf, child, about="#"+child.get("IDREF"))


if __name__ == "__main__":
    # Build up the rdf tree.
    toc_xml = ET.parse(sys.argv[1])
    rdf = ET.Element("rdf:RDF", {
        "xmlns:rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "xmlns:nc": "http://home.netscape.com/NC-rdf#",
    })
    rdf.text = "\n\n"
    add_rdf_description(rdf, toc_xml.getroot())

    # Write it to stdout.
    preamble = """<?xml version="1.0"?>
<!DOCTYPE rdf:RDF SYSTEM "chrome://branding/locale/brand.dtd" >
"""
    sys.stdout.write(preamble)
    ET.dump(rdf)
