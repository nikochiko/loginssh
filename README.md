# logins.sh (LoginSSH)

Works with tmux and fzf. You don't need to do a separate configuration to enable it, if you are in tmux,
it will use tmux. If fzf binary is in path, it will use fzf to show the list of SSH connections, then
depending on the choice, it will open up the SSH connection into that instance.

Depends on sshpass when the instance has a password.

To add autocomplete features, run this:

```sh
# in zsh
# add this to ~/.zshrc
eval $(_LOGINSSH_COMPLETE=zsh_source loginssh)

# in bash
# add to ~/.bashrc
eval $(_LOGINSSH_COMPLETE=bash_source loginssh)

# in fish
# add this to ~/.config/fish/completions/loginssh.fish
eval (env _LOGINSSH_COMPLETE=fish_source loginssh)
```

## How to install?

From pip:
```sh
# requires python3.9
python3.9 -m pip install loginssh
```

For main branch,

1. `git clone https://github.com/nikochiko/loginssh && cd loginssh`
1. `pip3 install -e loginssh`

## Why did I do this?
I enjoyed making this.

I didn't have to write this. I could use something already available, but then
I wouldn't have gotten to also rewrite ORMs and password managers. Yes, hidden in this repository is a
mini ORM and a mini password manager. I also like to flex that I use my own tools.   

## Note

I won't be actively pushing code to this repo. I will keep using it for my personal use,
but most probably that won't be needing any more changes.

That being said, it will make me extremely happy if someone else is using it. If you are using it, you are
in no way compelled to suggest improvements, but that will also make me happy.

## Another note
(not affiliated to logins.sh in way... yet)
