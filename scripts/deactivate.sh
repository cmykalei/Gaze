#!/bin/bash
# file:     scripts/deactivate.sh
# brief:    Bash script shuts down Conda environment.

# Unaliase the temporary commands.
printf "Removing aliases...\n"
unalias gaze
unalias gest
unalias deactivate

# Deactivate's twice to exit "base" env.
printf "Deactivating Conda environment...\n"
conda deactivate
conda deactivate
