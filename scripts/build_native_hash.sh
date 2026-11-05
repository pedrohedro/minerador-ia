#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

CFLAGS=()
LDFLAGS=()

if [ "$(uname -s)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
  OPENSSL_PREFIX="$(brew --prefix openssl@3 2>/dev/null || brew --prefix openssl 2>/dev/null || true)"
  if [ -n "$OPENSSL_PREFIX" ]; then
    CFLAGS+=("-I${OPENSSL_PREFIX}/include")
    LDFLAGS+=("-L${OPENSSL_PREFIX}/lib")
  fi
fi

cc -O3 -fPIC -shared -Wno-deprecated-declarations \
  "${CFLAGS[@]}" "${LDFLAGS[@]}" \
  minerador/native_hash.c -o minerador/_native_hash.so -lcrypto
printf 'Scanner nativo criado em minerador/_native_hash.so\n'
