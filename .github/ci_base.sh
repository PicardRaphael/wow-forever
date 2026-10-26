#!/usr/bin/env bash
# Base de la sélection des tests de la CI, écrite pour $GITHUB_OUTPUT (`arg=--base=<rev>`, ou `arg=` : suite complète).
# Nuit et lancement à la main : aucune base. Pull request : la branche visée. Push sur main : le commit d'avant le
# push. Push d'une autre branche : origin/main.
set -eu
case "$EVENT" in
  pull_request) base="origin/$BASE_REF" ;;
  push)
    if [ "$REF" = "main" ]; then
      base="$BEFORE"
    else
      base="origin/main"
    fi
    ;;
  *) base="" ;;
esac
case "$base" in
  "" | *[!0-9a-zA-Z/._-]* | 0000000000000000000000000000000000000000) echo "arg=" ;;
  *) echo "arg=--base=$base" ;;
esac
