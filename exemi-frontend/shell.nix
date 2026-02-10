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

  (python312.withPackages (p: with p; [
    certbot
    certbot-nginx
  ]))
];
}
