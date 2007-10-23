
"""Makefile for the 'komododoc' project.

${common_task_list}

See `mk -h' for options.
"""

import os
from os.path import join, dirname, normpath, abspath, isabs, exists, \
                    splitext, basename
import re
import sys
from pprint import pprint

from mklib import Task, Configuration, Alias, include
from mklib import sh
from mklib.common import MkError

sys.path.insert(0, join(_mk_makefile_.dir, "support"))
from buildsupport import paths_from_path_patterns, \
                         app_filter_html_path_inplace, \
                         app_filter_xml_path_inplace, _KomodoDocTask, \
                         ManifestParser, independentize_html_path
import preprocess
import api2html



include("support/checktasks.py", ns="check")


class cfg(Configuration):
    pass


class mozhelp(_KomodoDocTask):
    """Make a mozhelp tree (for adding chrome://komododoc/ to a Komodo
    build).
    
    TODO: Use TaskGroup for this when ready.
    TODO: mk: The following should be more easily representable as
          simple CopyTask and PreprocessTask subclasses. One issue is
          then how to depend on these easily without having to list them.
    """
    def deps(self):
        yield "htdocs"
        yield "mozhelp/*.*"

    @property
    def locale_dir(self):
        return join(self.cfg.chrome_dir, "komododoc", "locale",
                    self.cfg.lang)

    def results(self):
        yield join(self.cfg.chrome_dir, "komododoc.manifest")

        yield join(self.cfg.chrome_dir, "komododoc", "content",
                   "helpOverlay.xul")
        yield join(self.locale_dir, "help_help.xhtml")
        yield join(self.locale_dir, "help-toc.rdf")
        yield join(self.locale_dir, "aux_search.rdf")
        yield join(self.locale_dir, "komodohelp.rdf")

        # Just a landmark in the htdoc files for now.
        yield join(self.locale_dir, "top.html")
        
    def make(self):
        # komododoc.manifest
        defines = {"LANG": self.cfg.lang}
        src = join("mozhelp", "chrome.manifest")
        dst = join(self.cfg.chrome_dir, "komododoc.manifest")
        sh.mkdir(dirname(dst), log=self.log)
        self.log.info("preprocess %s %s", src, dst)
        preprocess.preprocess(src, dst, defines, contentType="Text",
                              substitute=True)

        # content
        content_dir = join(self.cfg.chrome_dir, "komododoc", "content")
        sh.mkdir(content_dir, log=self.log)
        sh.cp(join("mozhelp", "helpOverlay.xul"), dstdir=content_dir,
              log=self.log.info)

        # locale
        sh.mkdir(self.locale_dir, log=self.log)
        sh.cp(join("mozhelp", "help_help.xhtml"), dstdir=self.locale_dir,
              log=self.log.info)
        sh.cp(join("mozhelp", "komodohelp.rdf"), dstdir=self.locale_dir,
              log=self.log.info)
        sh.cp(join(self.htdocs_dir, "*"), dstdir=self.locale_dir,
              recursive=True, log=self.log.info)

        junk = [join(self.locale_dir, "komodo-js-api.toc"),
                join(self.locale_dir, "manifest.ini")]
        for path in junk:
            if exists(path):
                sh.rm(path, log=self.log)

        help_toc_rdf = join(self.locale_dir, "help-toc.rdf")
        try:
            sh.run("python support/tocxml2helptocrdf.py %s > %s"
                   % (join(self.locale_dir, "toc.xml"), help_toc_rdf),
                   self.log.info)
        except:
            if exists(help_toc_rdf):
                sh.rm(help_toc_rdf)
            raise


class dmgset(_KomodoDocTask):
    """A doc set for use in the root of a Mac OS X DMG package.
    
    Komodo DMGs will want the following doc files in the root:
        install.html
        relnotes.html
        license.txt
    with the associated CSS/image files hidden in '.foo' dirs.
    
    Which release notes HTML file do we use? We abort if
    `self.cfg.filters' don't disambiguate.
    """
    @property
    def dmgset_dir(self):
        return join(self.cfg.build_dir, "dmg")
    
    def deps(self):
        yield "doc_files"
    def results(self):
        yield join(self.dmgset_dir, "install.html")
        yield join(self.dmgset_dir, "relnotes.html")
        yield join(self.dmgset_dir, "license.txt")
        yield join(self.dmgset_dir, ".css", "screen.css")
        yield join(self.dmgset_dir, ".css", "aspn.css")

    def make(self):
        # Determine which release notes document to use.
        filters = self.cfg.filters or []
        if "snapdragon" in filters and "ide" not in filters:
            relnotes_src_path = join(self.htdocs_dir, "releases",
                                     "snapdragon.html")
        elif "ide" in filters and "snapdragon" not in filters:
            relnotes_src_path = join(self.htdocs_dir, "releases",
                                     "ide.html")
        else:
            raise MkError("Ambiguity in which `releases/*.html' to use "
                "for `relnotes.html'. This target can only be used when "
                "filtering for a specific Komodo flavor (see --filter "
                "configure.py option).")

        # CSS
        css_dir = join(self.dmgset_dir, ".css")
        sh.mkdir(css_dir, log=self.log)
        sh.cp(join(self.htdocs_dir, "css", "screen.css"),
              dstdir=css_dir, log=self.log.info)
        sh.cp(join(self.htdocs_dir, "css", "aspn.css"),
              dstdir=css_dir, log=self.log.info)
        
        # License text.
        sh.cp(self.cfg.license_text_path,
              join(self.dmgset_dir, "license.txt"),
              log=self.log.info)

        # Release notes and install notes.
        # These are more difficult, because we need to update some of
        # the links in these files.
        manifest = [
            #(relnotes_src_path,
            (join(self.htdocs_dir, "releases", "ide-4.2.html"), #XXX
             join(self.dmgset_dir, "relnotes.html")),
            (join(self.htdocs_dir, "readme.html"),
             join(self.dmgset_dir, "install.html")),
        ]
        
        # - Bunch 'o imports.
        for src, dst in manifest:
            independentize_html_path(src, dst, css_dir=".css",
                                     log=self.log)


class htdocs(Alias):
    """Make base doc set into $build_dir/htdocs
    
    This is a minimal build of the docs that could be used for static
    HTTP display. It forms the basis of other doc sets (e.g. a mozhelp
    chrome package, a .chm build).
    """
    def deps(self):
        yield "doc_files"
        yield "toc"
        if self.cfg.komodo_cix_path:
            yield "api_doc"


class toc(_KomodoDocTask):
    """Process toc.xml into the build area."""
    def deps(self):
        yield join(self.cfg.lang, "toc.xml")
        if self.cfg.komodo_cix_path:
            yield "api_doc"

    def results(self):
        yield join(self.htdocs_dir, "toc.xml")

    def make(self):
        src = self.deps[0].relpath
        dst = self.results[0].relpath
        if self.cfg.komodo_cix_path:
            defines = {
                "KOMODO_JS_API_TOC": abspath(join(self.htdocs_dir,
                                                  "komodo-js-api.toc")),
            }
        else:
            defines = {}
        self.log.info("preprocess %s %s", src, dst)
        preprocess.preprocess(src, dst, defines)
        app_filter_xml_path_inplace(dst, self.cfg.filters,
                                    log=self.log.info)


class api_doc(_KomodoDocTask):
    """Build the Komodo JS API doc."""
    def deps(self):
        yield self.cfg.komodo_cix_path
    def results(self):
        yield join(self.htdocs_dir, "komodo-js-api.html")
        yield join(self.htdocs_dir, "komodo-js-api.toc")
    def make(self):
        api2html.api2html(self.cfg.komodo_cix_path,
                          self.results[0].relpath,
                          toc_path=self.results[1].relpath,
                          css_paths=["css/aspn.css", "css/api.css"],
                          title="Komodo JavaScript API Reference",
                          log=self.log.info)

class clean_api_doc(_KomodoDocTask):
    def make(self):
        tasks = self.makefile.master.tasks.get("api_doc")
        assert len(tasks) == 1
        for result in tasks[0].results:
            print result

class doc_files(_KomodoDocTask):
    """Build the doc set."""
    def manifest(self):
        """Generate the doc set manifest."""
        mn = ManifestParser()
        mn.read(join(self.dir, self.cfg.lang, "manifest.ini"))
        
        if self.cfg.filters:
            sections = ["all"] + list(self.cfg.filters)
        else:
            sections = mn.sections()

        dst_already = set()
        for section in sections:
            if not mn.has_section(section):
                continue
            for dst, src in mn.items(section):
                dst = normpath(dst)
                if dst in dst_already:
                    continue
                if not src:
                    src = dst
                else:
                    src = normpath(src)
                yield src, dst
                dst_already.add(dst)

    def deps(self):
        for src, dst in self.manifest():
            yield join(self.dir, self.cfg.lang, src)
    def results(self):
        for src, dst in self.manifest():
            yield join(self.htdocs_dir, dst)

    def make(self):
        htdocs_dir = self.htdocs_dir
        self.log.info("build '%s' docs into '%s'", self.cfg.lang,
                      htdocs_dir)
        defines = {
            'LICENSE_TEXT_PATH': self.cfg.license_text_path,
        }
        
        for src, dst in self.manifest():
            src = normpath(join(self.dir, self.cfg.lang, src))
            dst = normpath(join(htdocs_dir, dst))
            if not exists(dirname(dst)):
                self.log.info("mkdir `%s'", dirname(dst))
                os.makedirs(dirname(dst))
            ext = splitext(src)[1]
            if ext in (".html", ".txt"):
                self.log.info("preprocess %s %s", src, dst)
                preprocess.preprocess(src, dst, defines, substitute=True)
                if ext == ".html":
                    app_filter_html_path_inplace(dst, self.cfg.filters,
                                                 log=self.log.info)
            else:
                sh.cp(src, dst, log=self.log.info)



class clean(_KomodoDocTask):
    """Remove the build dir."""
    def make(self):
        if exists(self.cfg.build_dir):
            sh.rm(self.cfg.build_dir, self.log)

class distclean(_KomodoDocTask):
    """Remove all build/configure products."""
    deps = ["clean"]
    def make(self):
        if exists("config.py"):
            sh.rm("config.py", self.log)
        

class todo(Task):
    """Print out todo's and xxx's in the docs area."""
    def make(self):
        excludes = [".svn", "*.pyc", "TO""DO.txt",
                    "*.png", "*.gif", "build", "preprocess.py",
                    "externals"]
        for path in paths_from_path_patterns(['.'], excludes=excludes):
            self._dump_pattern_in_path("TO\DO\\|XX\X", normpath(path))

        path = join(self.dir, "TO""DO.txt")
        todos = re.compile("^- ", re.M).findall(open(path, 'r').read())
        print "(plus %d TO""DOs from TO""DO.txt)" % len(todos)

    def _dump_pattern_in_path(self, pattern, path):
        os.system('grep -nH "%s" "%s"' % (pattern, path))


