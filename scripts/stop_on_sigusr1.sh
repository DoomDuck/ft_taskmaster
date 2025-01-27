#!/usr/bin/env bash

function on_sigusr1() {
    echo "Received SIGUSR1"
    exit 0
}

trap on_sigusr1 SIGUSR1

# Hook only get called when the command stops
# So this cannot be `sleep infinity`
while [ true ]; do
    sleep 10 & wait $!
done
