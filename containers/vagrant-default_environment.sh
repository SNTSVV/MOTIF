#! /bin/bash

set -u
set -e

# Add the following setting in .bashrc
echo "alias ll='ls -alFh'" >> /home/vagrant/.profile
echo "alias la='ls -Ah'" >> /home/vagrant/.profile
echo "alias l='ls -CFh'" >> /home/vagrant/.profile
echo "alias ..='cd ..'" >> /home/vagrant/.profile


# Add the following setting in .vimrc
echo "set nu" >> /home/vagrant/.vimrc
echo "syntax on" >> /home/vagrant/.vimrc
echo "set autoindent" >> /home/vagrant/.vimrc
echo "set hlsearch" >> /home/vagrant/.vimrc
echo "set ts=4" >> /home/vagrant/.vimrc
echo "set laststatus=2" >> /home/vagrant/.vimrc
echo "set ruler \"\"" >> /home/vagrant/.vimrc

