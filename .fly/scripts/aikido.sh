#!/usr/bin/env bash
cd /tmp || exit

curl -L -O "https://github.com/AikidoSec/firewall-php/releases/download/v1.4.11/aikido-php-firewall.$(uname -i).deb"
dpkg -i -E "./aikido-php-firewall.$(uname -i).deb"
