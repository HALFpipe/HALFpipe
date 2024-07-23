{
  description = "A basic flake with a shell";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    esbonio.url = "github:swyddfa/esbonio";
    esbonio.inputs.nixpkgs.follows = "nixpkgs";
    esbonio.inputs.utils.follows = "flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, esbonio }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        esbonio-overlay =
          import "${esbonio}/lib/esbonio/nix/esbonio-overlay.nix";
        overlays = [ esbonio-overlay ];
        pkgs = import nixpkgs {
          inherit system overlays;
          config.allowUnfree = true;
        };

        stackprinter = pkgs.python3Packages.buildPythonPackage rec {
          pname = "stackprinter";
          version = "0.2.11";
          src = pkgs.python3.pkgs.fetchPypi {
            inherit pname version;
            sha256 = "sha256-q72PT4kvJKW9NwEZr0nD40CLC/BM1NKOmfgcTngadns=";
          };
          propagatedBuildInputs = [ ];
          doCheck = false;
        };

        python = (pkgs.python311.withPackages (py:
          with py; [
            doc8
            docutils
            esbonio
            fasteners
            flufl_lock
            marshmallow
            marshmallow-dataclass
            marshmallow-oneofschema
            mypy
            numpy
            pandas
            pip-tools
            pygithub
            pyrsistent
            pytest
            rstcheck
            setuptools_scm
            stackprinter
            tabulate
            tqdm
            types-requests
            types-tabulate
          ]));

      in {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python
            ruff
          ];
        };
      });
}
