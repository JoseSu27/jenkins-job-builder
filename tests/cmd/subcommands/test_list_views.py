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

from collections import namedtuple

import pytest


ViewsScenario = namedtuple("ViewsScenario", "name views globs found")

views_scenarios = [
    ViewsScenario("single", views=["view1"], globs=[], found=["view1"]),
    ViewsScenario(
        "multiple", views=["view1", "view2"], globs=[], found=["view1", "view2"]
    ),
    ViewsScenario(
        "multiple_with_folder",
        views=["folder1", "folder1/view1", "folder1/view2"],
        globs=[],
        found=["folder1", "folder1/view1", "folder1/view2"],
    ),
    ViewsScenario(
        "multiple_with_glob",
        views=["view1", "view2", "view3"],
        globs=["view[1-2]"],
        found=["view1", "view2"],
    ),
    ViewsScenario(
        "multiple_with_multi_glob",
        views=["view1", "view2", "view3", "view4"],
        globs=["view1", "view[24]"],
        found=["view1", "view2", "view4"],
    ),
]


@pytest.mark.parametrize(
    "scenario",
    [pytest.param(s, id=s.name) for s in views_scenarios],
)
def test_from_jenkins_tests(
    capsys, mocker, default_config_file, execute_jenkins_jobs, scenario
):
    def get_views():
        return [{"name": name} for name in scenario.views]

    mocker.patch("jenkins_jobs.builder.JenkinsManager.get_views", side_effect=get_views)

    args = ["--conf", default_config_file, "list-views"] + scenario.globs
    execute_jenkins_jobs(args)

    expected_out = "\n".join(scenario.found)
    captured = capsys.readouterr()
    assert captured.out.rstrip() == expected_out


YamlScenario = namedtuple("YamlScnenario", "name globs found")

yaml_scenarios = [
    YamlScenario("all", globs=[], found=["bam001", "bar001", "bar002", "baz001"]),
    YamlScenario(
        "some",
        globs=["*am*", "*002", "bar001"],
        found=["bam001", "bar001", "bar002"],
    ),
]


@pytest.mark.parametrize(
    "scenario",
    [pytest.param(s, id=s.name) for s in yaml_scenarios],
)
def test_from_yaml_tests(
    capsys, fixtures_dir, default_config_file, execute_jenkins_jobs, scenario
):
    path = fixtures_dir / "cmd-003.yaml"

    execute_jenkins_jobs(
        ["--conf", default_config_file, "list-views", "-p", str(path)] + scenario.globs
    )

    expected_out = "\n".join(scenario.found)
    captured = capsys.readouterr()
    assert captured.out.rstrip() == expected_out
