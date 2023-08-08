# Licensed to Elasticsearch B.V. under one or more contributor
# license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright
# ownership. Elasticsearch B.V. licenses this file to you under
# the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# 	http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import pytest

from functools import partial
from pathlib import Path
from shutil import copytree

from pytest_rally.process import run_command_with_return_code

pytest_plugins = ["pytester"]

@pytest.fixture(scope="module")
def resources(request):
    yield Path(request.fspath).parent.joinpath("resources")

@pytest.fixture(scope="module")
def repo(resources):
    yield Path(resources).joinpath("track-repo")

@pytest.fixture(scope="function", autouse=True)
def make_conftest(pytester, repo):
    conftest_str = """
    import pytest

    def pytest_addoption(parser):
        group = parser.getgroup("rally")
        group.addoption("--track-repository", action="store", default=None)
        group.addoption("--track-revision", action="store", default="main")
    """
    pytester.makeconftest(conftest_str)

@pytest.fixture(scope="function", autouse=True)
def temp_repo(pytester, repo):
    temp_repo = pytester.mkdir("track-repo")
    copytree(repo, temp_repo, dirs_exist_ok=True)
    prefix = f"git -C {temp_repo}"
    commands = ["init", "add .", "commit -am 'test'"]
    for command in commands:
        run_command_with_return_code(f"{prefix} {command}")
    yield temp_repo

@pytest.fixture(scope="function")
def example(pytester):
    yield pytester.copy_example("race.py")

@pytest.fixture(scope="function")
def run(pytester, temp_repo, example):
    yield partial(pytester.runpytest, "--debug-rally", f"--track-repository={temp_repo}", example)
