#!/usr/bin/env bash
# Instala Bitcoin Core 32.1 como nó mainnet podado em Debian 13 ou Ubuntu x86_64.
# Execute no ThinkPad, depois de instalar Linux. Não particiona nem formata discos.
set -euo pipefail
umask 077

BITCOIN_VERSION=32.1
ARCHIVE="bitcoin-${BITCOIN_VERSION}-x86_64-linux-gnu.tar.gz"
SHA256=61545c17c3120fb7412f896d248b11993af04ec8817aad3649c55b2afb044963
URL="https://bitcoincore.org/bin/bitcoin-core-${BITCOIN_VERSION}/${ARCHIVE}"
CONFIG_DIR=/etc/bitcoin
DATA_DIR=/var/lib/bitcoind
SERVICE=/etc/systemd/system/bitcoind.service
PRUNE_MIB=102400

die() { printf 'Erro: %s\n' "$*" >&2; exit 1; }

[[ ${EUID} -eq 0 ]] || die "Execute com sudo: sudo bash $0"
[[ $(uname -m) == x86_64 ]] || die 'Este instalador exige CPU x86_64.'
[[ -r /etc/os-release ]] || die 'Não foi possível identificar o sistema.'
# shellcheck disable=SC1091
source /etc/os-release
if [[ ${ID:-} == debian ]]; then
    [[ ${VERSION_ID:-} == 13 ]] || die 'Este instalador exige Debian 13 ou Ubuntu.'
elif [[ ${ID:-} != ubuntu ]]; then
    die 'Este instalador exige Debian 13 ou Ubuntu.'
fi
command -v apt-get >/dev/null && command -v systemctl >/dev/null || \
    die 'Este instalador exige apt-get e systemd.'
[[ ! -e ${SERVICE} && ! -e ${CONFIG_DIR}/bitcoin.conf ]] || die 'Nó já configurado. Não sobrescrevi serviço nem credenciais.'
[[ ! -e /usr/local/bin/bitcoind ]] || die '/usr/local/bin/bitcoind já existe. Verifique antes de substituir.'

OPERATOR=${SUDO_USER:-root}
OPERATOR_HOME=$(getent passwd "${OPERATOR}" | cut -d: -f6)
[[ -n ${OPERATOR_HOME} && -d ${OPERATOR_HOME} ]] || die 'Não encontrei a pasta do usuário operador.'
CREDENTIALS="${OPERATOR_HOME}/bitcoin-rpc-credentials.txt"
[[ ! -e ${CREDENTIALS} ]] || die "Arquivo ${CREDENTIALS} já existe. Não o sobrescrevi."

printf 'Instalando dependências...\n'
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl python3 openssh-server

WORK_DIR=$(mktemp -d)
trap 'rm -rf "${WORK_DIR}"' EXIT
printf 'Baixando Bitcoin Core %s e verificando SHA-256...\n' "${BITCOIN_VERSION}"
curl --proto '=https' --tlsv1.2 -fL --retry 3 --output "${WORK_DIR}/${ARCHIVE}" "${URL}"
printf '%s  %s\n' "${SHA256}" "${WORK_DIR}/${ARCHIVE}" | sha256sum --check --status || die 'SHA-256 não confere. Instalação cancelada.'
tar -xzf "${WORK_DIR}/${ARCHIVE}" -C "${WORK_DIR}" "bitcoin-${BITCOIN_VERSION}/bin/bitcoind" "bitcoin-${BITCOIN_VERSION}/bin/bitcoin-cli"

if ! id bitcoin >/dev/null 2>&1; then
    useradd --system --home-dir "${DATA_DIR}" --shell /usr/sbin/nologin bitcoin
fi
install -d -o bitcoin -g bitcoin -m 0700 "${DATA_DIR}"
install -d -o root -g bitcoin -m 0750 "${CONFIG_DIR}"
install -o root -g root -m 0755 "${WORK_DIR}/bitcoin-${BITCOIN_VERSION}/bin/bitcoind" /usr/local/bin/bitcoind
install -o root -g root -m 0755 "${WORK_DIR}/bitcoin-${BITCOIN_VERSION}/bin/bitcoin-cli" /usr/local/bin/bitcoin-cli

# Mesmo algoritmo usado pelo share/rpcauth/rpcauth.py oficial do Bitcoin Core.
AUTH_DATA=$(python3 - <<'PY'
import hmac
from secrets import token_hex, token_urlsafe

salt = token_hex(16)
password = token_urlsafe(32)
digest = hmac.new(salt.encode(), password.encode(), 'SHA256').hexdigest()
print(f'{salt}${digest} {password}')
PY
)
read -r AUTH_HASH RPC_PASSWORD <<< "${AUTH_DATA}"
unset AUTH_DATA

cat > "${CONFIG_DIR}/bitcoin.conf" <<EOF
# Nó mainnet dedicado. RPC acessível somente no próprio ThinkPad.
server=1
disablewallet=1
prune=${PRUNE_MIB}
txindex=0
listen=0
rpcbind=127.0.0.1
rpcallowip=127.0.0.1
rpcport=8332
rpcauth=minerador:${AUTH_HASH}
EOF
chown root:bitcoin "${CONFIG_DIR}/bitcoin.conf"
chmod 0640 "${CONFIG_DIR}/bitcoin.conf"

cat > "${CREDENTIALS}" <<EOF
Bitcoin Core RPC - dados para preencher no Minerador IA no Mac
Modo: Mainnet com nó próprio
Host: 127.0.0.1
Porta: 18332
Usuário: minerador
Senha: ${RPC_PASSWORD}

Antes de conectar, mantenha este túnel aberto no Terminal do Mac:
ssh -N -L 127.0.0.1:18332:127.0.0.1:8332 ${OPERATOR}@IP_DO_THINKPAD

Nunca publique este arquivo ou a senha no Git.
EOF
chown "${OPERATOR}:$(id -gn "${OPERATOR}")" "${CREDENTIALS}"
chmod 0600 "${CREDENTIALS}"
unset RPC_PASSWORD AUTH_HASH

cat > "${SERVICE}" <<'EOF'
[Unit]
Description=Bitcoin Core mainnet node (pruned)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=bitcoin
Group=bitcoin
ExecStart=/usr/local/bin/bitcoind -conf=/etc/bitcoin/bitcoin.conf -datadir=/var/lib/bitcoind -daemon=0
Restart=on-failure
RestartSec=10
TimeoutStopSec=600
LimitNOFILE=8192
NoNewPrivileges=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/lib/bitcoind

[Install]
WantedBy=multi-user.target
EOF
chmod 0644 "${SERVICE}"
systemctl daemon-reload
systemctl enable --now ssh bitcoind

NODE_IP=$(hostname -I | awk '{print $1}')
printf '\nInstalação concluída. Nó: %s.\n' "${NODE_IP:-IP_DO_THINKPAD}"
printf 'Credenciais privadas: %s\n' "${CREDENTIALS}"
printf 'Estado: sudo systemctl status bitcoind\n'
printf 'Sincronização: sudo -u bitcoin bitcoin-cli -conf=%s/bitcoin.conf -datadir=%s getblockchaininfo\n' "${CONFIG_DIR}" "${DATA_DIR}"
printf 'A sincronização inicial pode levar dias. Espere initialblockdownload=false antes de minerar com este nó.\n'
