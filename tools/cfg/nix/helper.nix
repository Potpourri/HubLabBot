{
  getPinnedNixpkgs = {
    nixpkgsRef,
    overlayRef
  }: let
    nixpkgsVersion = builtins.fromJSON (builtins.readFile ./nixpkgs-version.json);
    overlayVersion = builtins.fromJSON (builtins.readFile ./overlay-version.json);
    potpourriDotfiles = builtins.fetchGit {
      inherit (overlayVersion) url rev;
      ref = overlayRef;
    };
    # my overlay with latest versions of dependencies
    potpourriOverlay = import (potpourriDotfiles + "/nixos/nixpkgs/overlays/potpourri-overlay.nix");
    pinnedPkgs = import (builtins.fetchGit {
      inherit (nixpkgsVersion) url rev;
      ref = nixpkgsRef;
    }) {
      overlays = [ potpourriOverlay ];
    };
  in
    pinnedPkgs;
}
