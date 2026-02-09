let
  pkgs = import <nixpkgs> {
    config = {
      allowUnfree = true;
    };
  };
in
pkgs.mkShell {
  buildInputs = with pkgs; [

  (python312.withPackages (p: with p; [
    python-dotenv # .env file for secret reading
    python-multipart # Needed for FastAPI OAuth2

    # Jupyter:
    ipykernel
    jupyter

    # Data Science:
    pip
    numpy
    pandas
    scipy
    tqdm
    tzlocal
    matplotlib

    # ML:
    huggingface-hub
    langchain

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
}
