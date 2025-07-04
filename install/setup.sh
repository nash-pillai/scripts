#!/usr/bin/env sh

cd ~

# Links
ln -s .config/zsh/.zshenv .zshenv
ln -s .data/audacity-data .audacity-data
ln -s .config/cups .cups
ln -s .data/eocvsim .eocvsim
ln -s .data/googleearth .googleearth
ln -s .data/minecraft .minecraft
ln -s .data/floorp .mozilla
ln -s .data/ssh .ssh
ln -s .data/thunderbird .thunderbird

mkdir -p ~/.local/Apps/ ~/Documents/ ~/Tmp/
mkdir -p ~/Media/Music/ ~/Media/Pictures/ ~/Media/Videos/ ~/Media/Screenshots/

chmod +x ~/.local/Apps/*
ln -sr ~/.local/Apps/* ~/.local/bin

exit

cd /Media/Code

git clone --depth 1 https://github.com/hlissner/doom-emacs emacs
doom install

git clone https://github.com/nash-pillai/tedi.git
