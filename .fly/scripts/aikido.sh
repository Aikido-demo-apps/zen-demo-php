#!/usr/bin/env bash
cd /tmp || exit

curl -L -O "https://github.com/AikidoSec/firewall-php/releases/download/v1.5.25/aikido-php-firewall.$(uname -m).deb"
dpkg -i -E "./aikido-php-firewall.$(uname -m).deb"
