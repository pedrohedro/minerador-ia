#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cc -O3 -fPIC -shared -Wno-deprecated-declarations \
  minerador/native_hash.c -o minerador/_native_hash.so -lcrypto
printf 'Scanner nativo criado em minerador/_native_hash.so\n'
