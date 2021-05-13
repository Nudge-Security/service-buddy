import logging

from atlassian.bitbucket import Cloud
from atlassian.bitbucket.cloud.workspaces import Workspace

from service_buddy_too.service.service import Service
from service_buddy_too.util.command_util import invoke_process


class BitbucketVCSProvider(object):

    @classmethod
    def get_type(cls):
        return 'bitbucket'

    def __init__(self):
        super(BitbucketVCSProvider, self).__init__()
        self.repo_root = ""
        self.dry_run = False
        self.workspace_name: str = None
        self.root_workspace: Workspace = None

    def init(self, user, password, repo_root, dry_run):
        self.dry_run = dry_run
        if user and password:
            client = Cloud(url="https://api.bitbucket.org/", username=user, password=password)
            self.root_workspace = client.workspaces.get(repo_root)
        else:
            logging.warning("VCS username and password not configured - assuming git executable has appropriate "
                            "authorization for repo checks")

        self.workspace_name = repo_root

    def find_repo(self, service_definition: Service):
        bitbucket_url = self._get_git_ssh_url(service_definition)
        if self.root_workspace:
            logging.info("bitbucket find_repo api: %r", bitbucket_url)
            exists = self.root_workspace.repositories.exists(service_definition.get_repository_name())
        else:
            logging.info("bitbucket find_repo git: %r", bitbucket_url)
            result = invoke_process(
                args=['git', 'ls-remote', bitbucket_url, '>', '/dev/null'], exec_dir=None, dry_run=self.dry_run
            )
            exists = result == 0
        if not exists:
            logging.info(f"Could not find repository -{service_definition.get_repository_name()}")
            bitbucket_url = None
        return bitbucket_url

    def _get_git_ssh_url(self, service_definition):
        bitbucket_url = f'ssh://git@bitbucket.org/{self.workspace_name}/{service_definition.get_repository_name()}'
        return bitbucket_url

    def create_repo(self, service_definition: Service):

        if self.dry_run:
            logging.error("Creating repo %r", str(service_definition.get_repository_name()))
        else:
            if self.root_workspace is None:
                raise Exception("VCS pass required for create repo operation")
            project = self.root_workspace.projects.exists(service_definition.get_app())
            if not project:
                logging.info(f"Creating project for {service_definition.get_app()}")
                # Have to make not private due to limitation in SDK
                project = self.root_workspace.projects.create(name=service_definition.get_app(),
                                                              key=service_definition.get_app(),
                                                              description=service_definition.get_app(),
                                                              is_private=False)
            # See I told you, there is a limitation in the SDK where you can not provide is_private
            # on creation, if you try ot create a public repo in a private project it fails
            repo = self.root_workspace.repositories.create(project_key=service_definition.get_app(),
                                                           repo_slug=service_definition.get_repository_name())
            repo.is_private = True
            repo.description = service_definition.get_description()
            repo.name = service_definition.get_fully_qualified_service_name()
        return self._get_git_ssh_url(service_definition)
