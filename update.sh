#!/usr/bin/env bash

git switch main
git pull
git fetch upstream
git merge upstream/main           # ou git rebase upstream/main
git push origin main
