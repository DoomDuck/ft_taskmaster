
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
          # Yaml with types
          pyyaml
          types-pyyaml
          
          # Structure check
          schema

          pytest # Testing
          flake8 # Linting
          mypy   # Typecheck
          black  # Formatter

          # Protobuf with types
          grpcio-tools
          types-protobuf
        ]))
      ];
    };
  };
}
