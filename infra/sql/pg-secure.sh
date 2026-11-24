#!/bin/sh
set -eu
# A configuração hostnossl aparece PRIMEIRO: conexões remotas sem TLS são rejeitadas.
file="${PGDATA}/pg_hba.conf"
printf 'hostnossl all all 0.0.0.0/0 reject\nhostnossl all all ::/0 reject\n' | cat - "$file" > "${file}.secured"
cat "${file}.secured" > "$file"
rm -f "${file}.secured"
