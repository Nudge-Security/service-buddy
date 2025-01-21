import logging
from collections import OrderedDict

from service_buddy_too.ci.build_creator import BuildCreator
from service_buddy_too.util.command_util import invoke_process
from cryptography.fernet import Fernet

class BambooBuildCreator(BuildCreator):

    def __init__(self):
        super().__init__()
        self.build_system_url = 'url'
        self.key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.key)
    def options(self):
        opt_dict = OrderedDict()
        opt_dict[self.build_system_url] = "URL of bamboo server"
        opt_dict['user'] = "Username for authentication when creating builds"
        opt_dict['password'] = "Password for authentication when creating builds"
        return opt_dict

    def init(self, default_config: dict, build_templates: dict, template_directory: str,
             user: str = None, password: str = None):
        super(BambooBuildCreator, self).init( default_config, build_templates, template_directory)
        # use bamboo-url as backup
        self.url = default_config.get(self.build_system_url, default_config.get('bamboo-url', None))
        self.build_templates = build_templates
        if user and password:
            encrypted_password = self.cipher_suite.encrypt(password.encode())
            with open('.credentials', 'w') as cred_file:
                cred_file.writelines('username={}\n'.format(user))
                cred_file.writelines('password={}\n'.format(encrypted_password.decode()))
                cred_file.flush()

    def create_project(self, service_definition):
        logging.info("Creating bamboo build")
        if service_definition.get_service_type() not in self.build_templates:
            raise Exception(
                "Build template not found for service type {}".format(service_definition.get_service_type()))

        build_template = self.build_templates.get(service_definition.get_service_type())['type']
        args = [
            'java',
            '-Dbamboo.specs.log.level=DEBUG',
            '-jar',
            'bamboo-plan-1.0-SNAPSHOT.jar',
            '--build-template', build_template,
            '--bamboo-url', self.url,
            '--application', service_definition.get_app(),
            '--role', service_definition.get_role()
        ]

        res = invoke_process(args)
        if res > 0:
            raise Exception("Error creating bamboo build")
        else:
            logging.info("Done creating bamboo build")

    @classmethod
    def get_type(cls):
        return "bamboo"
