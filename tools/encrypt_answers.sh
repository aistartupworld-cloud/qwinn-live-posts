#!/usr/bin/env bash
# Encrypt an answer key {"YYYY-MM-DD HH": "A", ...} to answers/<name>.dat/.key
# using answers/key.pub. Only the draw workflow can decrypt it.
# Usage: tools/encrypt_answers.sh answers.json batch-2026-11-05
set -euo pipefail
cd "$(dirname "$0")/.."
src=$1; name=$2; k=$(mktemp)
openssl rand -hex 32 > "$k"
openssl enc -aes-256-cbc -pbkdf2 -salt -in "$src" -out "answers/$name.dat" -pass "file:$k"
openssl pkeyutl -encrypt -pubin -inkey answers/key.pub -pkeyopt rsa_padding_mode:oaep -in "$k" -out "answers/$name.key"
rm -f "$k"; echo "wrote answers/$name.dat and .key"
