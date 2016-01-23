with import <nixpkgs> {}; {
  pyEnv = stdenv.mkDerivation {
    name = "py";
    buildInputs = [ stdenv python34 python34Packages.virtualenv ];
    shellHook = ''
      if [ ! -d venv ]
      then
        virtualenv --python=python3.4 venv
      fi
      source venv/bin/activate
    '';
  };
}
