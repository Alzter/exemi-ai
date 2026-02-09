let
  pkgs = import <nixpkgs> {
    config = {
      allowUnfree = true;
    };
  };
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    yarn
];
}
