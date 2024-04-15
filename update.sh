#!/bin/bash

# The path to the rapture_website directory within the git repository
DIRECTORY='rapture_website'

# Change to the git repository root
cd "$(dirname "$0")"

# Ensure we are in the root of a git repository
if [ ! -d ".git" ]; then
    echo "Error: .git directory is missing. Please run this script from the root of a git repository."
    exit 1
fi

# Stash any changes in the working directory
git stash push -- "${DIRECTORY}"

# Pull the latest changes for the repository
git pull

# Update just the rapture_website directory
git checkout HEAD -- "${DIRECTORY}"

# Apply the stashed changes, if any
git stash pop

# Any other commands necessary to restart or reconfigure the server go here

echo "The rapture_website directory has been updated successfully."

# Exit the script
exit 0
