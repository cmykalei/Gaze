#!/bin/bash
# file:         scripts/activate.sh
# brief:        Activates the Conda environment with the command "activate"
printf "Entering Conda environment...\n"

# Detect current shell for the correct conda hook.
_shell="bash"
if [ -n "$ZSH_VERSION" ]; then
  _shell="zsh"
elif [ -n "$BASH_VERSION" ]; then
  _shell="bash"
elif [ -n "$KSH_VERSION" ]; then
  _shell="bash"
fi

# Initialize conda in this shell session.
if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.${_shell} hook)"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  . "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  . "$HOME/anaconda3/etc/profile.d/conda.sh"
else
  printf "Conda not found. Ensure Conda is installed and available in PATH.\n" >&2
  # shellcheck disable=SC2317
  return 1 2>/dev/null || exit 1
fi

# Activate the target environment.
if ! conda activate gaze 2>/dev/null; then
  printf "Failed to activate 'gaze'. Available environments:\n" >&2
  conda info --envs >&2
  printf "Create it with 'conda env create -f environment.yml' or adjust the name.\n" >&2
  # shellcheck disable=SC2317
  return 1 2>/dev/null || exit 1
fi

# Set temporary aliases to use as commands.
printf "Setting up alias commands for this project...\n"

# Note: We can't use functions here, for reasons.
#       So aliases were the next best thing—just remember
#       to close the env properly!
# Important: These won't work in an IDE hitting PLAY.
printf "Use 'gaze' to start eye gaze.\n"
printf "Use 'gest' to start gestures.\n"
alias gaze="python scripts/gaze.py"
alias gest="python scripts/gesture.py"

# For example, using the deactivate script here.
printf "Use 'deactivate' to leave the environment.\n"
alias deactivate="source scripts/deactivate.sh"
