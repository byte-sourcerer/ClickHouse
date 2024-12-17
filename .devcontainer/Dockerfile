FROM mcr.microsoft.com/devcontainers/cpp:1-debian-12

RUN sudo apt-get update
RUN sudo apt-get upgrade

# install clangd
RUN sudo apt-get install -y clangd-19
RUN sudo update-alternatives --install /usr/bin/clangd clangd /usr/bin/clangd-19 100
