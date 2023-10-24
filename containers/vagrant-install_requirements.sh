#! /bin/bash

set -u
set -e

error_exit()
{
    echo "ERROR: $1"
    exit 1
}

# XXX: We assume, for now, that MASS is already installed
TOPDIR=$(dirname $(readlink -f $0))

# Install system packages (case study dependencies)
if [ $(id -u) -eq 0 ]; then
    # already sudo
    apt-get update -y
    apt-get install -y python python3 python3-pip git vim gdb

    # Upgrade pip version
    pip3 install --upgrade pip
else
    sudo apt-get update -y
    sudo apt-get install -y python python3 python3-pip git vim gdb

    # Upgrade pip version
    sudo pip3 install --upgrade pip
fi

## install python requirements
#pip install -U -r $TOPDIR/requirements.txt



# install Rscript 4.2.xxx (latest version)
# sudo apt-get update -qq
# sudo apt-get install -y --no-install-recommends software-properties-common dirmngr
# sudo wget -qO- https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc | sudo tee -a /etc/apt/trusted.gpg.d/cran_ubuntu_key.asc
# sudo add-apt-repository "deb https://cloud.r-project.org/bin/linux/ubuntu $(lsb_release -cs)-cran40/"
# sudo apt-get install -y --no-install-recommends r-base

# install Rscript a specific version (currently, no "make" command in this ubuntu)
# sudo apt-get update
# sudo apt-get build-dep r-base-dev
#
# wget -c https://cran.r-project.org/src/base/R-4/R-4.0.4.tar.gz
# tar -xzf R-4.0.4.tar.gz
# cd R-4.0.4
# ./configure
# make -j9
# sudo make install