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

import functools
import inspect
import logging
import os
import re

from string import Template

from pytest_rally import process

RALLY_HOME = os.getenv("RALLY_HOME", os.path.expanduser("~"))
RALLY_CONFIG_DIR = os.path.join(RALLY_HOME, ".rally")
CONFIG_NAME = "pytest"

def format_cli_opt(opt, val):
    opt = re.sub("_", "-", opt)
    if val is True:
        return f'--{opt}'
    elif isinstance(val, dict):
        val = ",".join([f"{k}:{v}" for k, v in val.items()])
    return f'--{opt}="{val}"'

def command_for_func(func, **kwargs):
    command = " ".join(re.split("_", func.__name__))
    opts = [format_cli_opt(k, v) for k, v in kwargs.items() if v]
    return f'esrally {command} {" ".join(opts)}'

def add_default_options(f):
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        opts = ["track_repository", "track_revision"]
        kwargs.update({o: getattr(self, o) for o in opts if kwargs.get(o) is None})
        return f(self, *args, **kwargs)
    return wrapper

def generate_command_line(f):
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        sig = inspect.signature(f).bind(self, *args, **kwargs)
        sig.apply_defaults()
        cmdline = kwargs.get("cmdline")
        if cmdline is None:
            kwargs["cmdline"] = command_for_func(f, **sig.kwargs)
        elif not cmdline.startswith("esrally"):
            raise AssertionError(f"Command must begin with 'esrally': [{cmdline}]")
        return f(self, *args, **kwargs)
    return wrapper

class Rally():
    def __init__(self,
                 track_repository=None,
                 track_revision=None,
                 config_dir=RALLY_CONFIG_DIR,
                 config_name=CONFIG_NAME,
                 debug=False):
        self.revision = None
        self.track_repository= track_repository
        self.track_revision = track_revision
        self.config_dir = config_dir
        self.config_name = config_name
        self.config_template = os.path.join(os.path.dirname(__file__), "resources", f"{config_name}.ini")
        self.config_location = os.path.join(config_dir, f"rally-{config_name}.ini")
        self.debug = debug
        self.logger = logging.getLogger(__name__)

    def install_config_file(self):
        self.logger.info("Writing Rally config to [%s]", self.config_location)
        with open(self.config_location, "wt", encoding="utf-8") as target:
            with open(self.config_template, "rt", encoding="utf-8") as src:
                contents = src.read()
                target.write(Template(contents).substitute(CONFIG_DIR=self.config_dir, TRACK_REPO=self.track_repository))

    def delete_config_file(self):
        self.logger.info("Removing Rally config from [%s]", self.config_location)
        os.remove(self.config_location)

    def set_revision(self):
        self.revision = process.run_command_with_output(f"esrally --version").rstrip()
        self.logger.info("Rally revision: [%s]", self.revision)

    def configure(self):
        self.set_revision()
        self.install_config_file()

    @add_default_options
    @generate_command_line
    def list_tracks(self,
                    *,
                    track_repository=None,
                    track_revision=None,
                    configuration_name=CONFIG_NAME,
                    cmdline=None):
        self.logger.info("Running command: [%s]", cmdline)
        return process.run_command_with_output(cmdline)

    @add_default_options
    @generate_command_line
    def race(self,
             *,
             track=None,
             challenge=None,
             track_repository=None,
             track_revision=None,
             client_options=None,
             configuration_name=CONFIG_NAME,
             elasticsearch_plugins=None,
             enable_assertions=True,
             enable_driver_profiling=False,
             exclude_tasks=None,
             include_tasks=None,
             kill_running_processes=True,
             on_error="abort",
             pipeline="benchmark-only",
             plugin_params=None,
             preserve_install=False,
             report_file=None,
             report_format=None,
             report_numbers_align=None,
             show_in_report=None,
             target_hosts="127.0.0.1:19200",
             telemetry=None,
             telemetry_params=None,
             test_mode=True,
             track_params=None,
             user_tag=None,
             cmdline=None):
        self.logger.info("Running command: [%s]", cmdline)
        if not self.debug:
            return process.run_command_with_return_code(cmdline)

    def all_tracks_and_challenges(self):
        ret = []
        # The first 13 lines are the Rally banner and table formatting
        # The last 4 are blank or informational
        raw = self.list_tracks()
        track_list = raw.split("\n")[12:-5]
        for track_str in track_list:
            track_name, *_, challenge_str = track_str.split()
            challenges = challenge_str.split(",")
            ret.append((track_name, challenges))
        return ret
