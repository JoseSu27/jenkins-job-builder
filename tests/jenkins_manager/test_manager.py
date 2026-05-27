# vim: set fileencoding=utf-8 :
#
#  - Copyright 2014 Guido Günther <agx@sigxcpu.org>
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

from unittest import mock

import pytest
import requests

from jenkins_jobs.config import JJBConfig
import jenkins_jobs.builder


_plugins_info = {}
_plugins_info["plugin1"] = {"longName": "", "shortName": "", "version": ""}


@pytest.fixture
def jjb_config():
    config = JJBConfig()
    config.validate()
    return config


def test_plugins_list(jjb_config):
    jjb_config.builder["plugins_info"] = _plugins_info

    builder = jenkins_jobs.builder.JenkinsManager(jjb_config)
    assert builder.plugins_list == _plugins_info


def test_plugins_list_from_jenkins(mocker, jjb_config):
    mocker.patch.object(
        jenkins_jobs.builder.jenkins.Jenkins, "get_plugins", return_value=_plugins_info
    )
    # Trigger fetching the plugins from jenkins when accessing the property
    jjb_config.builder["plugins_info"] = None
    builder = jenkins_jobs.builder.JenkinsManager(jjb_config)
    assert list(builder.plugins_list) == list(_plugins_info.values())


def test_delete_old_managed_jobs(mocker, jjb_config):
    jjb_config.builder["plugins_info"] = None
    builder = jenkins_jobs.builder.JenkinsManager(jjb_config)

    patches = mocker.patch.multiple(
        "jenkins_jobs.builder.JenkinsManager",
        get_jobs=mock.DEFAULT,
        is_job=mock.DEFAULT,
        is_managed_job=mock.DEFAULT,
        delete_job=mock.DEFAULT,
    )
    patches["get_jobs"].return_value = [
        {"fullname": "job1"},
        {"fullname": "job2"},
    ]
    patches["is_managed_job"].side_effect = [True, True]
    patches["is_job"].side_effect = [True, True]

    builder.delete_old_managed_jobs()
    assert patches["delete_job"].call_count == 2


def test_delete_old_managed_views(mocker, jjb_config):
    jjb_config.builder["plugins_info"] = None
    builder = jenkins_jobs.builder.JenkinsManager(jjb_config)

    patches = mocker.patch.multiple(
        "jenkins_jobs.builder.JenkinsManager",
        get_views=mock.DEFAULT,
        is_view=mock.DEFAULT,
        is_managed_view=mock.DEFAULT,
        delete_view=mock.DEFAULT,
    )
    patches["get_views"].return_value = [
        {"name": "view-1"},
        {"name": "view-2"},
    ]
    patches["is_managed_view"].side_effect = [True, True]
    patches["is_view"].side_effect = [True, True]

    builder.delete_old_managed_views()
    assert patches["delete_view"].call_count == 2


@pytest.mark.parametrize("error_string", ["Connection refused", "Forbidden"])
def test_get_plugins_info_error(mocker, jjb_config, error_string):
    builder = jenkins_jobs.builder.JenkinsManager(jjb_config)
    exception = jenkins_jobs.builder.jenkins.JenkinsException(error_string)
    mocker.patch.object(builder.jenkins, "get_plugins", side_effect=exception)
    plugins_info = builder.get_plugins_info()
    assert [_plugins_info["plugin1"]] == plugins_info


def test_delete_old_managed_jobs_with_concurrent_http_404(mocker, jjb_config):
    jjb_config.builder["plugins_info"] = None
    builder = jenkins_jobs.builder.JenkinsManager(jjb_config)

    pr_job_name = "my-pipeline/PR-123"
    patches = mocker.patch.multiple(
        "jenkins_jobs.builder.JenkinsManager",
        get_jobs=mock.DEFAULT,
        is_job=mock.DEFAULT,
        delete_job=mock.DEFAULT,
    )
    patches["get_jobs"].return_value = [
        {"fullname": "my-pipeline"},
        {"fullname": pr_job_name},
    ]
    patches["is_job"].return_value = True

    # After is_job() but before get_job_config(), the child job (PR, etc.) is
    # deleted by Jenkins concurrent scanning.
    def _get_job_config_side_effect(job_name):
        if job_name == pr_job_name:
            response = requests.Response()
            response.status_code = 404
            response.url = (
                "https://jenkins.example/job/my-pipeline/" "job/PR-123/config.xml"
            )
            raise requests.exceptions.HTTPError(
                "404 Client Error: Not found for url: " + response.url,
                response=response,
            )
        return (
            '<?xml version="1.0"?><org.jenkinsci.plugins.workflow.multibranch'
            ".WorkflowMultiBranchProject>"
            "<description>Managed by JJB</description>"
            "</org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject>"
        )

    mocker.patch.object(
        builder.jenkins, "get_job_config", side_effect=_get_job_config_side_effect
    )

    result = builder.delete_old_managed_jobs(keep=["my-pipeline"])
    assert result == 0
