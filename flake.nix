
{
  inputs = {
    nixpkgs.url = "nixpkgs/24.05";
  };
  outputs = { nixpkgs, ... } : let 
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
  in {
    devShells.${system}.default = pkgs.mkShell {
      name = "taskmaster";
      buildInputs = [
        (pkgs.python3.withPackages (p: with p; [
          pyyaml
          types-pyyaml

          pytest
          flake8
          mypy
          schema

          grpcio-tools
          types-protobuf
        ]))
      ];
    };
  };
}
