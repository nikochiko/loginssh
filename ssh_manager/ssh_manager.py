import base64
import os
import getpass
import pathlib
import shlex
import subprocess
import shutil
from typing import Any

import click
from cryptography.fernet import Fernet

from .database import Database
from .models import Profile, Login

USERNAME = getpass.getuser()  # current user's login name on host machine
CONFIG_DIR = pathlib.Path(os.getenv("HOME")) / ".config" / "ssh-manager"

if (_db_path := os.getenv("DB_PATH")):
    DB_PATH = pathlib.Path(_db_path)
else:
    DB_PATH = CONFIG_DIR / "db_1.sqlite"
    os.environ["DB_PATH"] = str(DB_PATH)


def complete_login_names(ctx, param, incomplete):
    login_names = Login.get_names_by_profile_name(USERNAME)
    return [lname for lname in login_names if lname.startswith(incomplete)]


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
    prompt_text = click.style(
        "This is a destructive operation! "
        "Are you sure you want to reset the database?",
        fg="red")
    if click.confirm(prompt_text):
        db = obj["db"]
        db.reset_db()
        click.echo(
            click.style("Database has been successfully reset! ♻️",
                        fg="green"))
    else:
        raise click.Abort(
            click.style("OK! Nothing has been deleted 🙂", fg="yellow"))


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
@click.option("--host", help="Host address for this connection", prompt=True)
@click.option("--username",
              help="User to connect to on remote host",
              prompt=True)
def add_ssh(username, host, name):
    profile = Profile.get_by(name=USERNAME)
    password = None
    if click.confirm(
            click.style("Does this SSH login need a password to connect to?",
                        fg="cyan",
                        bold=True)):
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


@cli.command("login")
@click.argument("name", shell_complete=complete_login_names)
@click.pass_obj
def ssh(obj: dict[str, Any], name: str):
    """Login to the SSH aliased by NAME in a new TMUX/Screen/Terminal window"""
    profile = Profile.get_by(name=USERNAME)
    login = Login.get_by(name=name)

    if profile.name != USERNAME:
        click.echo(
            click.style(
                f"You need to be logged in as {profile.name}"
                " to access this login",
                fg="red",
                bold=True))
        raise click.Abort("Authentication failed!")

    decrypted_password = None
    if login.password:
        fernet = authenticate_user_and_get_fernet(profile)
        decrypted_password = fernet.decrypt(login.password.encode()).decode()

    click.echo(
        click.style(f"💫 Logging you in to {login.name} ({login.host})",
                    fg="cyan"))
    shell = obj["shell"]
    if decrypted_password is None:
        args = shlex.split(f"{shell} \'ssh {login.username}@{login.host}\'")
        p = subprocess.Popen(args)
    else:
        args = shlex.split(f"{shell} 'sshpass -p \"{decrypted_password}\" "
                           f"ssh {login.username}@{login.host}'")
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
    p.communicate()
    if p.returncode == 0:
        click.echo(
            click.style(f"✅ Logged you in to {login.name} as {login.username}",
                        fg="green"))
    else:
        click.echo(f"p.returncode: {p.returncode}")


@cli.command("list")
@click.pass_context
def list_logins(ctx):
    """List logins"""
    profile = Profile.get_by(name=USERNAME)
    logins = Login.filter_by(profile_id=profile.id)
    logins_str = pretty_print_logins(logins)
    if shutil.which("fzf") is not None:
        echo_command = f"echo '{logins_str}'"
        echo_args = shlex.split(echo_command)
        fzf_command = "fzf"
        fzf_args = shlex.split(fzf_command)
        echo_proc = subprocess.Popen(echo_args, stdout=subprocess.PIPE)
        proc = subprocess.Popen(fzf_args,
                                stdin=echo_proc.stdout,
                                stdout=subprocess.PIPE)
        echo_proc.stdout.close()
        stdout, stderr = proc.communicate()
        if not stdout:
            click.echo("No option selected")
        else:
            output = stdout.strip().decode()
            selected = output.split("\t")[0].strip()
            ctx.invoke(ssh, name=selected)
    else:
        click.echo_via_pager(logins_str)


def pretty_print_logins(logins: list[Login]) -> str:
    login_names = list(map(lambda l: l.name, logins))
    login_usernames = list(map(lambda l: l.username, logins))
    login_hosts = list(map(lambda l: l.host, logins))

    max_name_length = max(map(len, login_names + ["NAME"]))
    max_username_length = max(map(len, login_usernames + ["USERNAME"]))
    max_hostname_length = max(map(len, login_hosts + ["HOSTNAME"]))

    formatting_str = "{0:%d}\t{1:%d}\t{2:%d}" % (
        max_name_length, max_username_length, max_hostname_length)

    lines = []
    lines.append(formatting_str.format("NAME", "USERNAME", "HOSTNAME"))

    for login_name, login_username, login_host in zip(login_names,
                                                      login_usernames,
                                                      login_hosts):
        lines.append(
            formatting_str.format(login_name, login_username, login_host))

    return "\n".join(reversed(lines))


def authenticate_user_and_get_fernet(profile):
    password = click.prompt(f"Master password for {profile.name}",
                            prompt_suffix=":🔑 ",
                            hide_input=True)

    if profile.check_password(password):
        click.echo(
            click.style("Authenticated successfully! ✅", fg="green",
                        bold=True))
        key = get_key_from_password(password)
        fernet = Fernet(key)
        return fernet
    else:
        click.echo(click.style("Authentication failed ❌", fg="red", bold=True))
        raise click.Abort()


def get_key_from_password(password):
    # fernet key needs to be urlsafe base64 encoding of a length-32 bytes
    str_key = "".join(password[i % len(password)] for i in range(32))
    return base64.urlsafe_b64encode(str_key.encode())


# if __name__ == "__main__":
#    cli()
