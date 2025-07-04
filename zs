#!/usr/bin/env sh

zellij ${1:-a -c $(zellij ls | fzf -1 -0)} $2
