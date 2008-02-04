#!/usr/bin/env python

import os
from os.path import dirname, abspath, expanduser, join
import re
import sys
import logging
from glob import glob

try:
    from configurelib import main, ConfigVar, ConfigureError, Profile
except ImportError:
    # `mk' supports an option to help find the configurelib package.
    configurelib_path = os.popen("mk --configurelib-path").read().strip()
    sys.path.insert(0, configurelib_path)
    from configurelib import main, ConfigVar, ConfigureError, Profile
    del configurelib_path


log = logging.getLogger("configure")



#---- config vars

class BuildDir(ConfigVar):
    name = "build_dir"
    deps = ["filters", "lang"]

    def add_options(self, optparser):
        optparser.add_option("--build-dir",
            help="dir in which to build the docs (default is generally "
                 "reasonable)")

    def determine(self, config_var_from_name, options):
        if options.build_dir:
            self.value = options.build_dir
        else:
            filters = config_var_from_name["filters"].value or ["full"]
            lang = config_var_from_name["lang"].value
            bits = list(sorted(filters)) + [lang]
            self.value = join("build", "-".join(bits))


class ChromeDir(ConfigVar):
    """Directory into which to build the chrome for the 'mozhelp' target."""
    name = "chrome_dir"
    deps = ["build_dir"]

    def add_options(self, optparser):
        optparser.add_option("--chrome-dir",
            help="directory into which to build the chrome for the "
                 "'mozhelp' target (by default is under the `build_dir`)")

    def determine(self, config_var_from_name, options):
        if options.chrome_dir:
            self.value = options.chrome_dir
        else:
            build_dir = config_var_from_name["build_dir"].value
            self.value = join(build_dir, "mozhelp", "chrome")


class MinisetDir(ConfigVar):
    """Directory into which to build the 'miniset' target."""
    name = "miniset_dir"
    deps = ["build_dir"]

    def add_options(self, optparser):
        optparser.add_option("--miniset-dir",
            help="directory into which to build the mini doc set for the "
                 "'mozhelp' target (by default is under the `build_dir`)")

    def determine(self, config_var_from_name, options):
        if options.miniset_dir:
            self.value = options.miniset_dir
        else:
            build_dir = config_var_from_name["build_dir"].value
            self.value = join(build_dir, "miniset")

class ASPNHelpDir(ConfigVar):
    """Directory into which to build the 'aspnhelp' target."""
    name = "aspnhelp_dir"
    deps = ["build_dir"]

    def add_options(self, optparser):
        optparser.add_option("--aspnhelp-dir",
            help="directory into which to build the ASPN doc set for the "
                 "'aspnhelp' target (by default is under the `build_dir`)")

    def determine(self, config_var_from_name, options):
        if options.aspnhelp_dir:
            self.value = options.aspnhelp_dir
        else:
            build_dir = config_var_from_name["build_dir"].value
            self.value = join(build_dir, "aspnhelp")


class Lang(ConfigVar):
    name = "lang"

    def available_langs(self):
        dir = dirname(__file__)
        return [basename(p) for p in glob(join(dir, "??-??"))]

    def add_options(self, optparser):
        optparser.add_option("-l", "--lang", default="en-US",
            help="dir in which to build the docs (default is 'en-US')")

    def determine(self, config_var_from_name, options):
        self.value = options.lang


class Filters(ConfigVar):
    """Filter strings for limiting the doc set to parts relevant to
    the given Komodo applications.
    
    By default no filtering is done (empty filter list). If the
    '-f|--filter' option is used, then it is a list of app name strings
    to *include*. Filter strings are the set of Komodo app names:
    
        ide
        edit
        snapdragon
    """
    name = "filters"
    known_values = ["ide", "edit", "snapdragon"]
    
    def add_options(self, optparser):
        optparser.add_option("-F", "--filter",
            dest="filters", action="append",
            help="specify one or more Komodo app names to include in "
                 "the doc build (typical values: '%s')"
                 % ("', '".join(self.known_values)))

    def determine(self, config_var_from_name, options):
        if options.filters:
            self.value = set()
            for s in options.filters:
                self.value.update( re.compile("[,;: ]+").split(s) )
        else:
            self.value = None


class LicenseTextPath(ConfigVar):
    """Path to license text to include in lic_copy.html file.
    
    By default the MPL 1.1 is used.
    """
    name = "license_text_path"
    
    def add_options(self, optparser):
        optparser.add_option("--license-text-path", metavar="PATH",
            help="path to a file holding the license text for this "
                 "Komodo app build")

    def determine(self, config_var_from_name, options):
        if options.license_text_path:
            self.value = options.license_text_path
        self.value = abspath(join("support", "LICENSE.mpl.txt"))


class KomodoCixPath(ConfigVar):
    """Path to a komodo.cix Code Intelligence API catalog describing
    the Komodo JS API.
    
    If `--komodo-cix-path' is not specified, then this doc page will
    not be included in the docs.
    """
    name = "komodo_cix_path"
    
    def add_options(self, optparser):
        optparser.add_option("--komodo-cix-path", metavar="PATH",
            help="path to API catalog describing the Komodo JS API")

    def determine(self, config_var_from_name, options):
        self.value = options.komodo_cix_path


config_vars = [
    BuildDir(),
    ChromeDir(),
    MinisetDir(),
    ASPNHelpDir(),
    Filters(),
    Lang(),
    LicenseTextPath(),
    KomodoCixPath(),
]


#---- mainline

if __name__ == "__main__":
    main(config_vars, project_name="komododoc")

