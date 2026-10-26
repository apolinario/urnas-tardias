#!/bin/bash
# Coleta completa sem supervisão: repete o crawler até uma passada terminar sem exceções de rede, servidor ou disco.
# uso: OUT_DIR=/pasta/da/coleta [RPS=12] [MAX_PASSADAS=10] bash coletar.sh [--refazer] [ufs...]
cd "$(dirname "$0")" || exit 1
[ -n "${OUT_DIR:-}" ] || { echo "defina OUT_DIR com a pasta da coleta" >&2; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
args=("$@")
for ((passada = 1; passada <= ${MAX_PASSADAS:-10}; passada++)); do
    # disco externo desconectado: espera voltar em vez de falhar
    until mkdir -p "$OUT_DIR" 2>/dev/null && [ -w "$OUT_DIR" ]; do
        echo "$(date +%T) aguardando $OUT_DIR"
        sleep 60
    done
    echo "$(date +%T) passada $passada de ${MAX_PASSADAS:-10}"
    if command -v caffeinate >/dev/null; then caffeinate -i python3 crawl.py "${args[@]}"; else python3 crawl.py "${args[@]}"; fi
    [ $? -eq 0 ] && { echo "$(date +%T) coleta completa"; exit 0; }
    # --refazer só vale na primeira passada; nas seguintes retoma o que ficou
    args=()
    for a in "$@"; do [ "$a" = "--refazer" ] || args+=("$a"); done
    sleep "${PAUSA:-60}"
done
echo "$(date +%T) ainda há pendências após ${MAX_PASSADAS:-10} passadas; rode de novo" >&2
exit 3
