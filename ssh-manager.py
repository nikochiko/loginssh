import os
import getpass
import pathlib

import click

from database import Database
from models import Profile, Login


USERNAME = getpass.getuser()  # current user's login name on host machine
CONFIG_DIR = pathlib.Path(os.getenv("HOME")) / ".config" / "ssh-manager"

if (_db_path := os.getenv("DB_PATH")):
    DB_PATH = pathlib.Path(_db_path)
else:
    DB_PATH = CONFIG_DIR / "db_1.sqlite"
    os.environ["DB_PATH"] = str(DB_PATH)


@click.group()
@click.pass_context
def cli(ctx):
    db = Database(DB_PATH)
    ctx.obj = {"db": db}


@cli.command("db-init", help="Initialize database")
@click.pass_obj
def db_init(obj):
    db = obj["db"]
    db.init_db()


@cli.command("init-profile", help="Initialize profile")
def init_profile():
    profile_name = click.prompt("Profile name",
                                default=USERNAME,
                                prompt_suffix=":🧑‍💻 ")
    profile_password = click.prompt("Master password",
                                    prompt_suffix=":🔑 ",
                                    hide_input=True,
                                    confirmation_prompt=True)
    profile = Profile.new_profile(name=profile_name, password=profile_password)

    click.echo(f"✅ New profile created with id: {profile.id}")


@cli.command("add")
@click.option("--name",
              help="Nickname for the SSH Connection (e.g. aws-company-1)",
              prompt="Name for this SSH connection")
@click.option("--host",
              help="Host address for this connection",
              prompt=True)
@click.option("--username",
              help="User to connect to on remote host",
              prompt=True)
def add_ssh(username, host, name):
    profile = Profile.get_by(name=USERNAME)[0]
    login = Login.new(
            username=username, host=host, name=name, profile_id=profile.id)
    click.echo(f"✅ Created new SSH login with id: {login.id}")


if __name__ == "__main__":
    cli()
