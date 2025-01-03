#!/usr/bin/env bash

if [ `umask` != "0765" ]; then
    echo "umask should be 0765"
    exit 1
fi
