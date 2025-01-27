#!/usr/bin/env bash

if [ -z "${SHOULD_BE_SET+x}" ]; then
    echo "Variable SHOULD_BE_SET is not set !"
    exit 1
fi

