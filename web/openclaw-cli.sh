#!/bin/bash
# Wrapper to call openclaw inside the gateway container
exec docker exec openclaw-gateway openclaw "$@"
