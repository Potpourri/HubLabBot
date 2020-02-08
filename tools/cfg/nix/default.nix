{ python37Packages }:

python37Packages.buildPythonPackage rec {
  pname = "hublabbot";
  version = "0.0.1";

  src = ../../..;

  postPatch = ''
    substituteInPlace setup.py --replace UNKNOWN_VERSION ${version}
    substituteInPlace hublabbot/__init__.py --replace UNKNOWN_VERSION ${version}
  '';

  propagatedBuildInputs = with python37Packages; [
    pyramid
    pygit2
    PyGithub
    python-gitlab
  ];

  doCheck = false;
}
