let
  inherit (import ./helper.nix) getPinnedNixpkgs;
  inherit (import ./const.nix) myNixpkgsRef myOverlayRef;
  pinnedPkgs = getPinnedNixpkgs {
    nixpkgsRef = myNixpkgsRef;
    overlayRef = myOverlayRef;
  };
in

{ pkgs ? pinnedPkgs }:

with pkgs;

let
  hublabbot = callPackage ./default.nix { };
in

dockerTools.buildImage {
  name = "potpourri/hublabbot";
  tag = "dev";
  contents = [
    runtimeShellPackage
    hublabbot
  ];
  config = {
    EntryPoint = [ "/bin/hublabbot" ];
    WorkingDir = "/opt/hublabbot/";
    User = "1000";
    Env = [
      "SSL_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt"
      "PYTHONUNBUFFERED=1"
    ];
  };
}
