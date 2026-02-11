let
  pkgs = import <nixpkgs> {
    config = {
      allowUnfree = true;
    };
  };
in
pkgs.mkShell {
  buildInputs = with pkgs; [
  
  openssl_oqs
#   ollama

  (python312.withPackages (p: with p; [
    python-dotenv # .env file for secret reading
    python-multipart # Needed for FastAPI OAuth2

    # Cloud Hosting:
#     python-openstackclient
#     python-designateclient

    # Jupyter:
#     ipykernel
#     jupyter

    # Data Science:
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
#    instructor
    langchain
    langchain-ollama
#    litellm
    
    # Backend:
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
#   shellHook = ''
#     export OLLAMA_HOST=0.0.0.0:11434
#   '';
}
