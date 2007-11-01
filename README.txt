README for the Komodo Documentation project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The komododoc project exists to provide quality documentation for
Komodo-based apps/products. It includes the HTML sources for user
documentation for use by all Komodo apps and support for building the doc
set and necessary pieces for displaying these docs in the app and online.

Currently user documentation for a Komodo application (e.g. Komodo IDE,
Komodo Edit, Komodo Snapdragon) is provided in two forms:

- Viewable/browsable/searchable in the Mozilla Help viewer that is
  included in a Komodo build. This is the help window the user gets when
  pressing F1 or selecting help in Komodo.
- In a standalone HTML documentation set (typically published to a
  website).


Getting the Source
==================

If you are reading this, you probably already have it, but for the record:
The Komodo doc sources are kept in a Subversion repository hosted at the
openkomodo.com site. Read-only public access is available via:

    svn co http://svn.openkomodo.com/repos/komododoc/trunk komododoc

Read/write developer access is available via:

    svn co https://svn.openkomodo.com/repos/komododoc/trunk komododoc


How it works
============

Also known as the "Why a separate project?" section. The Open Komodo
source tree is huge and building a full Open Komodo build is not for
the faint of heart. Having a separate project for the Komodo docs
allows for an lower barrier to entry for working with and contributing
the Komodo docs. Typical Komodo app builds will use this source tree (and
use the "mozhelp" build target, see below) but you can do a full Komodo
doc build without bothering with a full Komodo tree.

The komododoc project includes documentation for all apps built using
the Open Komodo framework. Currently this includes Komodo Snapdragon
(code name), Komodo IDE and Komodo Edit. Keeping docs for all Komodo apps
in one repository will help ensure that all Komodo projects best benefit
from shared work on their docs. Time spent on documenting software is
precious -- we want to make sure it is best used.

The build system here provides simple mechanisms for
including/excluding/marking only those parts of the docs that are relevant
for a particular Komodo flavor. How this works in described below.



How to build it
===============

0. First you need the "mk" build tool:

        svn co http://svn.openkomodo.com/repos/mk/trunk mk

   Then put the 'mk/bin' directory on your PATH:
   
        export PATH=`pwd`/mk/bin:$PATH     # on Linux/Mac OS X
        set PATH=...\mk\bin;%PATH%         # on Windows

   'mk' is a build tool that is meant to act like GNU make. Hence, general
   usage is:
   
        mk [TARGETS...]

1. Configure how you want to build the docs. This is done via the
   "configure.py" script (which is used like a typical autoconf
   "configure" script):
   
        ./configure.py [OPTIONS...]

   By default it will configure to do a complete doc build (i.e. docs
   relevant to all Komodo flavours will be included) for the en-US
   language (the default, and currently the only, translation).

        ./configure.py

   For the curious, this creates a "config.py" that is used to control
   what gets built and how.

2. Make any of the desired targets with the "mk" tool. The most common
   target is "mozhelp" that builds the necessary bits for adding docs
   to a full Komodo build:
   
        mk mozhelp


To make changes, you need only make your edits to the files in the "en-US"
directory and re-run `mk mozhelp` to update everything.



Contributing: Editing/Typos
===========================

<http://bugs.activestate.com/enter_bug.cgi?product=OpenKomodo&component=Documentation>

TODO


Contributing: Translations
==========================

TODO

