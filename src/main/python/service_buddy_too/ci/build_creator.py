import logging
import os
from typing import Dict

from cookiecutter.main import cookiecutter

from service_buddy_too.codegenerator.cookie_cutter_creator import _make_cookie_safe
from service_buddy_too.service.service import Service
from service_buddy_too.util.command_util import invoke_process


class BuildCreator(object):

    @classmethod
    def get_type(cls):
        return None

    def __init__(self):
        self.dry_run: bool = False
        self.build_templates: Dict = {}
        self.build_configuration: Dict = {}
        self.template_directory: str = ""

    def init(self, dry_run: bool, default_config: dict, build_templates: dict, template_directory: str,
             user: str = None, password: str = None):
        self.dry_run = dry_run
        self.build_templates = build_templates
        self.template_directory = template_directory
        self.build_configuration = default_config.get('build-configuration', {})

    def create_project(self, service_definition: Service, app_dir: str):
        pass

    def options(self):
        pass


class FileBasedBuildCreator(BuildCreator):

    def create_build(self, service_dir: str, build_configuration: dict, service_definition: Service):
        if 'type' not in build_configuration or build_configuration['type'] == 'script':
            logging.info("Creating script build")
            return self._create_script_build(service_dir, build_configuration, service_definition)
        elif build_configuration['type'] == 'file':
            location = os.path.abspath(os.path.join(self.template_directory, build_configuration['location']))
        elif build_configuration['type'] == 'github':
            location = build_configuration['location']
        else:
            raise Exception(f"Unknown build configuration type - {build_configuration['type']} ",)
        extra_context = _make_cookie_safe(service_definition)
        # allow extra context in build config
        extra_context.update(_make_cookie_safe(build_configuration))
        # allow user to specify the directory in the github repo
        directory= build_configuration.get('directory', None)
        if self.dry_run:
            logging.error("Creating project from template {} ".format(location))
        else:
            return cookiecutter(location, no_input=True,
                                extra_context=extra_context,
                                output_dir=service_dir,
                                directory=directory)

    def _build_exists_action(self, service_dir: str, build_template: dict, service_definition: Service):
        pass

    def _get_build_file(self, service_dir: str) -> str:
        pass

    def create_project(self, service_definition: Service, app_dir: str):
        pass
        if service_definition.get_service_type() not in self.build_templates:
            raise Exception(
                "Build template not found for service type {}".format(service_definition.get_service_type()))
        else:
            build_type = self.build_templates.get(service_definition.get_service_type())['type']
        service_dir = service_definition.get_service_directory(app_dir=app_dir)
        build_template = self.build_configuration.get(build_type, None)
        if build_template:
            if os.path.exists(self._get_build_file(service_dir)):
                logging.warning(f"Build file already exists {self._get_build_file(service_dir)}" )
                self._build_exists_action(service_dir,build_template, service_definition)
                invoke_process(['git', 'checkout', os.path.basename(self._get_build_file(service_dir))],
                               exec_dir=service_dir, dry_run=self.dry_run)
                invoke_process(['git', 'commit', '-m', 'Build file - updated by service-buddy'],
                               exec_dir=service_dir,
                               dry_run=self.dry_run)
            else:
                self.create_build(service_dir, build_template, service_definition)
                invoke_process(['git', 'add', os.path.basename(self._get_build_file(service_dir))],
                               exec_dir=service_dir, dry_run=self.dry_run)
                invoke_process(['git', 'commit', '-m', 'Build file - generated by service-buddy'],
                               exec_dir=service_dir,
                               dry_run=self.dry_run)
        else:
            logging.warning("Could not locate build template"
                            " for build type - {}:{}".format(service_definition.get_service_type(),
                                                             build_type))

    def _create_script_build(self, service_dir: str, build_configuration: dict, service_definition: Service):
        raise Exception(f'Script build not supported for this build creator - {self.get_type()}' )
