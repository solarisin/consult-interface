import os
import sys

import click

CONTEXT_SETTINGS = dict(auto_envvar_prefix="COMPLEX")


class Environment:
    def __init__(self) -> None:
        self.verbose = False
        self.home = os.getcwd()

    def log(self, msg: str, *args: object) -> None:
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr)

    def vlog(self, msg: str, *args: object) -> None:
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)


pass_environment = click.make_pass_decorator(Environment, ensure=True)
cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "commands"))


class ComplexCLI(click.Group):
    def list_commands(self, ctx: click.Context) -> list[str]:
        rv: list[str] = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith(".py") and filename.startswith("cmd_"):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        try:
            mod = __import__(f"consult_interface.cli.commands.cmd_{cmd_name}", None, None, ["cli"])
        except ImportError as e:
            print("ImportError:" + str(e))
            return None
        command: click.Command = mod.cli
        return command


@click.command(cls=ComplexCLI, context_settings=CONTEXT_SETTINGS)
@click.option(
    "--home",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Changes the folder to operate on.",
)
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode.")
@pass_environment
def cli(ctx: Environment, verbose: bool, home: str | None) -> None:
    """A complex command line interface."""
    ctx.verbose = verbose
    if home is not None:
        ctx.home = home
