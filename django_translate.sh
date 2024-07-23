#!/usr/bin/bash

cd "$HOME/work/dev/auto_translate_for_django/"
poetry run ./auto_translate.py $@
cd - > /dev/null