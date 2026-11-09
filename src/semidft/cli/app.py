"""Main Typer application entry point for semidft."""

import typer

from semidft.cli.commands.calculation import calc_app
from semidft.cli.commands.doctor import run_doctor
from semidft.cli.commands.pseudo import pseudo_app
from semidft.cli.commands.results import results_app
from semidft.cli.commands.structure import structure_app
from semidft.cli.commands.workflow import workflow_app

app = typer.Typer(
    name="semidft",
    help="Research-oriented semiconductor DFT workflow toolkit using Quantum ESPRESSO.",
    no_args_is_help=True,
)

app.command(name="doctor")(run_doctor)
app.add_typer(structure_app, name="structure")
app.add_typer(pseudo_app, name="pseudo")
app.add_typer(calc_app, name="calc")
app.add_typer(workflow_app, name="workflow")
app.add_typer(results_app, name="results")
