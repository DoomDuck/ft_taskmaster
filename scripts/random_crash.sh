#!/usr/bin/env bash

if [[ $(($RANDOM % 3)) == 0 ]]; then
    sleep infinity
fi

exit 1
