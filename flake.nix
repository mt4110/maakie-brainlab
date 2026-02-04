{
  description = "maakie-brainlab devshell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "aarch64-darwin";
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          pkgs.git
          pkgs.ripgrep
          pkgs.jq
          pkgs.sqlite
          pkgs.uv
          pkgs.python312
        ];
      };
    };
}
