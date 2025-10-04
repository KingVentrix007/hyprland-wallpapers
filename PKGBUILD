    # PKGBUILD example
    pkgname=HyperPapers # Name of your package in AUR
    pkgver=0.1.0 # Version, should match setup.py
    pkgrel=1
    pkgdesc="GUI and wallpaper manager"
    arch=('any') # Python packages are usually architecture-independent
    url="https://github.com/KingVentrix007/hyprland-wallpapers" # Project URL
    license=('MIT') # Your project's license
    depends=('python' 'python-setuptools') # Core dependencies
    makedepends=('git') # If you're fetching from Git, for example

    source=("git+${url}.git#tag=v${pkgver}") # Source URL for makepkg
    sha256sums=('SKIP') # Replace with actual checksum if not using git tag or if using a tarball

    build() {
      cd "${srcdir}/${pkgname}"
      python -m build --wheel --no-isolation
    }

    package() {
      cd "${srcdir}/${pkgname}"
      python -m installer --destdir="${pkgdir}" --no-compile dist/*.whl
    }