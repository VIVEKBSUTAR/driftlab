"""
Defines the Typer command-line interface as thin wrappers over the core modules.
"""

import typer

app = typer.Typer()

@app.command()
def run():
    print("Running DriftLab CLI")

if __name__ == "__main__":
    app()
