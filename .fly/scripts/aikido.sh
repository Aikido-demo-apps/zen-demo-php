#!/usr/bin/env bash
cd /tmp || exit

curl -L -O https://github.com/AikidoSec/firewall-php/releases/download/v1.0.117/aikido-php-firewall.x86_64.deb
dpkg -i -E ./aikido-php-firewall.x86_64.deb
