#!/usr/bin/env bash

while :; do
  git pull
  git submodule update --init --recursive
  python main.py 231
done
