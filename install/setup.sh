#!/usr/bin/env sh

sudo nix-channel --add https://nixos.org/channels/nixos-unstable unstable
sudo nix-channel --update

sudo ln -s /home/nash/.state/nix/profile/bin/gh /usr/bin/gh

cd ~

git clone https://github.com/nash-pillai/config.git .config
mkdir -p .local/scripts
git clone https://github.com/nash-pillai/scripts.git .local/scripts

# Create directories
mkdir -p ~/Documents/ ~/Documents/Public/ ~/Tmp/
mkdir -p ~/Media/Music/ ~/Media/Pictures/ ~/Media/Videos/ ~/Media/Screenshots/
xdg-user-dirs-update

config_links=(1Password 'Badlion Client' cef_user_data Element Insomnia mozc BambuStudio Bitwarden chromium discord docker launcher obsidian heroic libreoffice vivaldi Slack)
home_links=('minecraft' 'floorp' 'ssh' 'thunderbird')
for dir in "${config_links[@]}"; do
    mkdir -p ~/.data/$dir
    ln -sfT ../.data/$dir .config/$dir
done
for dir in "${home_links[@]}"; do
    mkdir -p ~/.data/$dir
done
mkdir -p ~/.data/gnupg
chmod 700 ~/.data/gnupg

sudo mkdir -p /Media/Wallpapers/ /Media/Code/
sudo chown -R nash:users /Media/
git clone https://github.com/nash-pillai/wallpapers.git /Media/Wallpapers/
git clone https://github.com/nash-pillai/notes.git ~/Documents/Notes/

# Links
ln -s .config/zsh/.zshenv .zshenv
ln -s .config/cups .cups
ln -s .data/minecraft .minecraft
ln -s .data/floorp .floorp
ln -s .data/ssh .ssh
ln -s .data/thunderbird .thunderbird
# ln -fs .config/floorp/chrome .data/floorp/*.default/chrome

cd /Media/Code

git clone --depth 1 https://github.com/hlissner/doom-emacs emacs
doom install

git clone https://github.com/nash-pillai/stapplet.git
git clone https://github.com/nash-pillai/stapplet-new.git
