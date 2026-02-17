#!/usr/bin/env zsh

# Alt+Backspace: backward-kill-word treating dashes as word characters,
# unlike Ctrl+W which uses the default (oh-my-zsh) WORDCHARS without dashes.
_backward_kill_word_with_dashes() {
    local WORDCHARS="${WORDCHARS}-"
    zle backward-kill-word
}
zle -N _backward_kill_word_with_dashes
bindkey '^[^?' _backward_kill_word_with_dashes

# History search
autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search

[[ -n "$key[Up]"   ]] && bindkey -- "$key[Up]"   up-line-or-beginning-search
[[ -n "$key[Down]" ]] && bindkey -- "$key[Down]" down-line-or-beginning-search


# project navigation
_zsh_goto_project()
{
    goto_project
    zle reset-prompt
}
zle -N _zsh_goto_project
bindkey ^s _zsh_goto_project


# short git log
_zsh_git_log_short()
{
    git_log_pager_short
    zle reset-prompt
}
zle -N _zsh_git_log_short
bindkey ^k _zsh_git_log_short

# history fuzzy finder
_history_fuzzy_finder()
{
    history_fuzzy_finder
    zle reset-prompt
}
zle -N _history_fuzzy_finder
bindkey ^r _history_fuzzy_finder

_zsh_cli_fg() {
    fg
}
zle -N _zsh_cli_fg
bindkey ^z _zsh_cli_fg

# activate virtualenv
venv_sourced=0
_venv_activate()
{
    if [[ $venv_sourced -eq 0 ]]; then
        venv_sourced=1
        source ./.venv/bin/activate
    else
        venv_sourced=0
        deactivate
    fi
    zle reset-prompt
}
zle -N _venv_activate
bindkey ^v _venv_activate

# toggle right prompt (RPROMPT)
__rprompt_toggled=0
_toggle_rprompt() {
    # Save original RPROMPT once
    if [[ -z $__rprompt_saved ]]; then
        __rprompt_saved="$RPROMPT"
    fi

    if [[ $__rprompt_toggled -eq 0 ]]; then
        __rprompt_toggled=1
        RPROMPT=""
        RPS1=""
    else
        __rprompt_toggled=0
        RPROMPT="$__rprompt_saved"
        RPS1="$__rprompt_saved"
    fi
    zle reset-prompt
}
zle -N _toggle_rprompt
# Bind to Ctrl-Y
bindkey '^y' _toggle_rprompt
