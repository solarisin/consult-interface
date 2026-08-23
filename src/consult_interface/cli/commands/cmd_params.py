import click

from consult_interface.cli.cli import Environment, pass_environment


@click.command("params", short_help="Work with ECU parameters via CONSULT.")
@click.argument("path", required=False, type=click.Path(resolve_path=True))
@pass_environment
def cli(ctx: Environment, path: str | None) -> None:
    if path is None:
        path = ctx.home
    ctx.log(f"Started param command, passed in {click.format_filename(path)}")
