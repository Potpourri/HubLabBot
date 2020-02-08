# This derivation can work either lorri or nix-shell
# → https://github.com/target/lorri

let
  inherit (import ./helper.nix) getPinnedNixpkgs;
  inherit (import ./const.nix) myNixpkgsUrl myNixpkgsRef myOverlayUrl myOverlayRef;
  # Look here for information about pinning Nixpkgs
  # → https://nixos.wiki/wiki/FAQ/Pinning_Nixpkgs
  pinnedPkgs = getPinnedNixpkgs {
    nixpkgsRef = myNixpkgsRef;
    overlayRef = myOverlayRef;
  };
in

# This allows overriding pkgs by passing `--arg pkgs ...`
{ pkgs ? pinnedPkgs }:

with pkgs;

stdenv.mkDerivation rec {
  name = "HubLabBot-shell";
  phases = [ "nobuildPhase" ];

  buildInputs = [
    # develop dependencies:
    mypy
    python37Packages.flake8
    python3Packages.flake8-mypy
    python3Packages.flake8-tabs
    python3Packages.flake8-docstrings
    pdoc3
    jscpd
    cspell
    # runtime dependencies:
    python37
    python37Packages.pyramid
    python37Packages.pygit2
    python37Packages.PyGithub
    python37Packages.python-gitlab
    # optional dependencies:
    # -
    # other developing tools:
    cacert #WORKAROUND: https://github.com/target/lorri/issues/98
    git
    conform
    update-pinned-nixpkgs
  ];

  HUBLABBOT_VERSION = (callPackage ./default.nix { }).version;
  PROJECT_ROOT = toString ../../..;
  MY_NIXPKGS_URL = myNixpkgsUrl;
  MY_NIXPKGS_REF = myNixpkgsRef;
  MY_OVERLAY_URL = myOverlayUrl;
  MY_OVERLAY_REF = myOverlayRef;

  shellHook = ''
    PATH+=":$PROJECT_ROOT/tools"
  '';

  nobuildPhase = ''
    echo
    echo "This derivation is not meant to be built, aborting"
    echo
    exit 1
  '';
}
