try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import os
import logging
from argparse import Namespace
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from simplhdl.flow import FlowFactory, FlowBase
from simplhdl.resources.templates import vsg as templates
from simplhdl.utils import sh, CalledShError, generate_from_template
from simplhdl.pyedaa import VHDLSourceFile
from simplhdl.pyedaa.project import Project
from simplhdl.pyedaa.attributes import UsedIn

logger = logging.getLogger(__name__)


@FlowFactory.register('vhdl-style-guide')
class VsgFlow(FlowBase):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('vhdl-style-guide', help='VHDL Style Guide Flow')
        parser.add_argument(
            '--output-format',
            choices=[
                'vsg',
                'syntastic',
                'summary'
            ],
            default='vsg',
            help="Display output format"
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help="Fix style formatting (Note: this modifies the source)"
        )
        parser.add_argument(
            '-r', '--rules',
            action='store',
            help="Rule configuration file"
        )
        parser.add_argument(
            '-f', '--files',
            type=lambda p: Path(p).absolute(),
            nargs='+',
            default=[],
            help="Manually specify file list"
        )


    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = templates

    def setup(self):
        os.makedirs(self.builddir, exist_ok=True)

    def generate(self):
        templatedir = resources_files(self.templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)
        template = environment.get_template('files.json.j2')
        generate_from_template(template, self.builddir,
                               VHDLSourceFile=VHDLSourceFile,
                               project=self.project,
                               UsedIn=UsedIn)
        template = environment.get_template('rules.yml.j2')
        generate_from_template(template, self.builddir)

    def execute(self):
        command = ["vsg"]
        if self.args.rules:
            rules = self.args.rules
        elif os.getenv('SIMPLHDL_VSG_RULES'):
            rules = self.args.rules
        else:
            rules = 'rules.yml'

        if self.args.fix:
            command.append("--fix")
        else:
            command += f"-ap -of {self.args.output_format}".split()

        if self.args.files:
            if rules:
                command += f"-c {rules}".split()
            command += ['-f'] + self.args.files
        else:
            command += f"-c {rules} files.json".split()

        try:
            logger.debug(command)
            sh(command, cwd=self.builddir, output=True)
        except CalledShError as e:
            print(e)
            raise SystemError

    def run(self) -> None:
        self.setup()
        self.generate()
        self.execute()
