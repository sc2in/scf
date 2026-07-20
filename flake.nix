{
  description = "sc2in/scf-api — canonical Secure Controls Framework dataset: workbook -> validated JSON -> static API";

  inputs = {
    nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0";
    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-parts.inputs.nixpkgs-lib.follows = "nixpkgs";
    treefmt-nix.url = "github:numtide/treefmt-nix";
    treefmt-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];

      imports = [
        inputs.treefmt-nix.flakeModule
      ];

      perSystem = {
        pkgs,
        lib,
        self',
        ...
      }: let
        pythonEnv = pkgs.python3.withPackages (ps: [
          ps.openpyxl
          ps.rapidfuzz
          ps.jsonschema
          ps.pytest
        ]);

        scf-api = pkgs.python3Packages.buildPythonApplication {
          pname = "scf-api";
          version = "0.1.0";
          pyproject = true;
          src = lib.cleanSourceWith {
            src = ./.;
            filter = path: _type: let
              rel = lib.removePrefix (toString ./. + "/") (toString path);
            in
              lib.any (p: lib.hasPrefix p rel) ["src" "pyproject.toml" "README.md" "tests"];
          };
          build-system = [pkgs.python3Packages.hatchling];
          dependencies = with pkgs.python3Packages; [openpyxl rapidfuzz jsonschema];
          # Unit tests run in the dedicated pytest check (with the synthetic fixture).
          doCheck = false;
        };

        haveData = builtins.pathExists ./.scf-version;
      in {
        packages.default = scf-api;
        packages.scf-api = scf-api;

        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
            pkgs.gh
            pkgs.jq
          ];
          shellHook = ''
            export PYTHONPATH=$PWD/src:$PYTHONPATH
          '';
        };

        treefmt = {
          projectRootFile = "flake.nix";
          programs.ruff-format.enable = true;
          programs.alejandra.enable = true;
        };

        checks =
          {
            pytest =
              pkgs.runCommand "scf-api-pytest" {
                nativeBuildInputs = [pythonEnv];
              } ''
                cp -r ${./src} src
                cp -r ${./tests} tests
                export PYTHONPATH=$PWD/src
                pytest tests -q
                touch $out
              '';
          }
          // lib.optionalAttrs haveData {
            # Schemas + cross-file referential integrity over the committed data/.
            data-valid =
              pkgs.runCommand "scf-api-data-valid" {
                nativeBuildInputs = [pythonEnv];
              } ''
                export PYTHONPATH=${./src}
                python3 -m scf_api.cli validate --data ${./data} \
                  --overrides ${./overrides/overrides.json} \
                  --scf-version "$(cat ${./.scf-version})" \
                  --report /dev/null
                touch $out
              '';

            # Rebuild docs/ from committed data/ -> must byte-match committed docs/.
            docs-fresh =
              pkgs.runCommand "scf-api-docs-fresh" {
                nativeBuildInputs = [pythonEnv];
              } ''
                export PYTHONPATH=${./src}
                python3 -m scf_api.cli build --data ${./data} --out $TMPDIR/docs
                if ! diff -r $TMPDIR/docs ${./docs}; then
                  echo "docs/ has drifted from data/. Regenerate: scf-api build" >&2
                  exit 1
                fi
                touch $out
              '';

            # .scf-version <-> data filename <-> docs/api/summary.json must agree.
            version-consistent =
              pkgs.runCommand "scf-api-version-consistent" {
                nativeBuildInputs = [pythonEnv pkgs.jq];
              } ''
                ver="$(cat ${./.scf-version})"
                dashed="$(echo "$ver" | tr . -)"
                test -f ${./data}/scf-"$dashed".json || {
                  echo "data/scf-$dashed.json missing for .scf-version=$ver" >&2
                  exit 1
                }
                jqver="$(jq -r .scf_version ${./docs}/api/summary.json)"
                test "$jqver" = "$ver" || {
                  echo "docs/api/summary.json scf_version=$jqver != .scf-version=$ver" >&2
                  exit 1
                }
                catver="$(jq -r .framework.version ${./data}/scf-"$dashed".json)"
                test "$catver" = "$ver" || {
                  echo "catalog framework.version=$catver != .scf-version=$ver" >&2
                  exit 1
                }
                touch $out
              '';
          };
      };
    };
}
