{pkgs}: {
  deps = [
    pkgs.docker
    pkgs.docker-client
    pkgs.docker-compose
    pkgs.pkg-config
    pkgs.coreutils
    pkgs.cacert
    pkgs.glibcLocales
    pkgs.jre
    pkgs.antlr
    pkgs.wireshark
    pkgs.tcpdump
    pkgs.sox
    pkgs.imagemagickBig
    pkgs.pgadmin4
  ];
}
