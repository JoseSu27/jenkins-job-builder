#!/usr/bin/env python
# Copyright (C) 2018 Sorin Sbarnea
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import logging
import sys

from jenkins_jobs.builder import JenkinsManager
import jenkins_jobs.cli.subcommand.base as base
import jenkins_jobs.utils as utils


def list_duplicates(seq):
    seen = set()
    return set(x for x in seq if x in seen or seen.add(x))


class ListViewsSubCommand(base.JobsSubCommand):
    def parse_args(self, subparser):
        list = subparser.add_parser("list-views", help="List views")

        self.parse_option_recursive_exclude(list)

        list.add_argument("names", help="name(s) of view(s)", nargs="*", default=None)
        list.add_argument(
            "-p", "--path", default=None, help="path to YAML file or directory"
        )

    def execute(self, options, jjb_config):
        views = self.get_views(jjb_config, options.path, options.names)

        logging.info("Matching views: %d", len(views))
        stdout = utils.wrap_stream(sys.stdout)

        for view in views:
            stdout.write((view + "\n").encode("utf-8"))

    def get_views(self, jjb_config, path_list, glob_list):
        if path_list:
            roots = self.load_roots(jjb_config, path_list)
            views = base.filter_matching(roots.generate_views(), glob_list)
            view_names = [v.name for v in views]
        else:
            jenkins = JenkinsManager(jjb_config)
            view_names = [
                v["name"]
                for v in jenkins.get_views()
                if not glob_list or base.matches(v["name"], glob_list)
            ]

        view_names = sorted(view_names)
        for duplicate in list_duplicates(view_names):
            logging.warning("Found duplicate view name '%s', likely bug.", duplicate)

        logging.debug("Builder.get_views: returning %r", view_names)

        return view_names
