let
  pkgs = import <nixpkgs> {
    config = {
#       enableCuda = true;
      allowUnfree = true;
    };

    # Override PyTorch to use a pre-compiled version (torch-bin)
#     overlays = [
#     (
#       final: prev: rec {
#         python312 = prev.python312.override {
#           self = python312;
#           packageOverrides = final_: prev_: {
#             torch = final_.torch-bin.overrideAttrs(torch-binFinalAttrs: torch-binPrevAttrs: {
#               passthru = torch-binPrevAttrs.passthru // {
#                 cudaPackages = pkgs.cudaPackages;
#                 rocmSupport = true; # No idea what this is or if it works, ostensibly some newfangled GPU acceleration technology
#                 cudaSupport = true; # This is pain
#               };
#             });
#             torchvision = final_.torchvision-bin;
#             torchaudio = final_.torchaudio-bin;
#           };
#         };
#       }
#     )];
  };
in
pkgs.mkShell {
  buildInputs = with pkgs; [
  
  nodejs
  yarn
  vite
  openssl_oqs

  (python312.withPackages (p: with p; [
    python-dotenv # .env file for secret reading
    python-multipart # Needed for FastAPI OAuth2

    # Jupyter:
    ipykernel
    jupyter

    # Data science:
    pip
    numpy
    pandas
    scipy
    tqdm
    tzlocal
    matplotlib

    # ML:
#     smolagents
#     torch
#     torchvision
#     torchaudio
#     transformers
    huggingface-hub
    
    fastapi
    fastapi-cli
    pyjwt
    pwdlib
    llama-cpp-python
    sqlmodel
    sqlalchemy
    mariadb
    cryptography
  ]))
  ];
}
