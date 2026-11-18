#!/bin/bash
# Prepara a VM na primeira inicialização: Docker, Compose, jq e swap.
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y docker.io docker-compose-v2 jq curl unattended-upgrades
systemctl enable --now docker

# 2 GB de swap: folga de memória
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# atualizações de segurança automáticas do sistema operacional
dpkg-reconfigure -f noninteractive unattended-upgrades

install -d -m 700 /opt/alertabairro
touch /var/lib/alertabairro-pronto
