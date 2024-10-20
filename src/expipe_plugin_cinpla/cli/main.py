# -*- coding: utf-8 -*-
import click
from expipe.cliutils.plugin import IPlugin

from .process import attach_to_process
from .register import attach_to_register


class CinplaPlugin(IPlugin):
    def attach_to_cli(self, cli):
        @cli.group(short_help="Tools for registering.")
        @click.help_option("-h", "--help")
        @click.pass_context
        def register(ctx):
            pass

        @cli.group(short_help="Tools for processing.")
        @click.help_option("-h", "--help")
        @click.pass_context
        def process(ctx):
            pass

        attach_to_register(register)
        attach_to_process(process)
