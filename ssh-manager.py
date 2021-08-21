#!/opt/homebrew/bin/python3.9
import base64
import os
import getpass
import pathlib
import shlex
import subprocess
from typing import Any

import click
from cryptography.fernet import Fernet

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
    if (term_env := os.getenv("TERM")) and \
       term_env.lower() in {"screen", "tmux"} and \
       os.getenv("TMUX"):
        shell = "tmux split-window"
    else:
        shell = "open " + os.getenv("SHELL", "/bin/sh -c ")

    ctx.obj = {"db": db, "shell": shell}


@cli.command("db-init", help="Initialize database")
@click.pass_obj
def db_init(obj):
    db = obj["db"]
    db.init_db()


@cli.command("db-reset", help="Reset the database - delete all previous data")
@click.pass_obj
def db_reset(obj):
    prompt_text = click.style("This is a destructive operation! "
                              "Are you sure you want to reset the database?",
                              fg="red")
    if click.confirm(prompt_text):
        db = obj["db"]
        db.reset_db()
        click.echo(
            click.style("Database has been successfully reset! ♻️",
                        fg="green"))
    else:
        raise click.Abort(click.style("OK! Nothing has been deleted 🙂",
                                      fg="yellow"))


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


@cli.command("add", help="Add a new SSH connection")
@click.argument("name")
@click.option("--host",
              help="Host address for this connection",
              prompt=True)
@click.option("--username",
              help="User to connect to on remote host",
              prompt=True)
def add_ssh(username, host, name):
    profile = Profile.get_by(name=USERNAME)
    password = None
    if click.confirm(click.style(
            "Does this SSH login need a password to connect to?",
            fg="cyan", bold=True)):
        password = click.prompt("Password for this SSH connection")
        if password:
            click.echo(click.style("Got it!", fg="green"))
        else:
            click.echo("No password supplied.")
            raise click.Abort()

    fernet = authenticate_user_and_get_fernet(profile)
    if password:
        encrypted_password = fernet.encrypt(password.encode()).decode()
    else:
        encrypted_password = None

    login = Login.new(username=username,
                      host=host,
                      name=name,
                      password=encrypted_password,
                      profile_id=profile.id)
    click.echo(f"✅ Created new SSH login with id: {login.id}")


@cli.command("ssh", help="Connect to a SSH")
@click.option("--name",
              help="Nickname for the SSH machine you want to log into")
@click.pass_obj
def ssh(obj: dict[str, Any], name: str):
    profile = Profile.get_by(name=USERNAME)
    login = Login.get_by(name=name)

    if profile.name != USERNAME:
        click.echo(
                click.style(
                    f"You need to be logged in as {profile.name}"
                    " to access this login", fg="red", bold=True))
        raise click.Abort("Authentication failed!")

    decrypted_password = None
    if login.password:
        fernet = authenticate_user_and_get_fernet(profile)
        decrypted_password = fernet.decrypt(login.password.encode()).decode()

    click.echo(f"ssh {login.username}@{login.host}")
    shell = obj["shell"]
    if decrypted_password is None:
        click.echo(f"{shell} \'ssh {login.username}@{login.host}\'")
        args = shlex.split(
                f"{shell} \'ssh {login.username}@{login.host}\'")
        p = subprocess.Popen(args)
    else:
        p = click.launch(f"{shell} \'sshpass -p \\'{decrypted_password}\\' "
                         f"ssh {login.username}@{login.password}\'")

    click.echo(f"SSH process ended with exit code: {p.returncode}")


def authenticate_user_and_get_fernet(profile):
    password = click.prompt(f"Master password for {profile.name}",
                            prompt_suffix=":🔑 ",
                            hide_input=True)

    if profile.check_password(password):
        click.echo(click.style(
            "Authenticated successfully! ✅", fg="green", bold=True))
        key = get_key_from_password(password)
        fernet = Fernet(key)
        return fernet
    else:
        click.echo(click.style(
            "Authentication failed ❌", fg="red", bold=True))
        raise click.Abort()


def get_key_from_password(password):
    # fernet key needs to be urlsafe base64 encoding of a length-32 bytes
    str_key = "".join(password[i % len(password)] for i in range(32))
    return base64.urlsafe_b64encode(str_key.encode())


if __name__ == "__main__":
    cli()
