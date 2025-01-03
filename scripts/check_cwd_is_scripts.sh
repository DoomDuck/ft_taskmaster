#!/usr/bin/env bash

if [ `basename "${PWD}"` != "scripts" ]; then
    echo "CWD is not scripts"
    exit 1
fi
