#!/usr/bin/env bash
cd /tmp || exit

curl -L -O "https://github.com/AikidoSec/firewall-php/releases/download/v${AIKIDO_VERSION}/aikido-php-firewall.$(uname -i).deb"
dpkg -i -E "./aikido-php-firewall.$(uname -i).deb"
