"""
PyCOLD setup script
"""

__notes__ = """
# Check contents of wheel
rm -rf _skbuild/ dist/ tool/python/pycold.egg-info/
python setup.py bdist_wheel && unzip -l dist/pycold-0.1.0-cp38-cp38-linux_x86_64.whl

pip install dist/pycold-0.1.0-cp38-cp38-linux_x86_64.whl
python -c "import pycold"
"""
import sys
import os
from setuptools import find_packages

# Allow disabling of C-extensions to debug pure-python code
PYCOLD_DISABLE_C_EXTENSIONS = os.environ.get('PYCOLD_DISABLE_C_EXTENSIONS', '')
if PYCOLD_DISABLE_C_EXTENSIONS == '1':
    from setuptools import setup
else:
    from skbuild import setup


def parse_version(fpath):
    """
    Statically parse the version number from a python file
    """
    import ast
    from os.path import exists
    if not exists(fpath):
        raise ValueError('fpath={!r} does not exist'.format(fpath))
    with open(fpath, 'r') as file_:
        sourcecode = file_.read()
    pt = ast.parse(sourcecode)
    class VersionVisitor(ast.NodeVisitor):
        def visit_Assign(self, node):
            for target in node.targets:
                if getattr(target, 'id', None) == '__version__':
                    self.version = node.value.s
    visitor = VersionVisitor()
    visitor.visit(pt)
    return visitor.version


def parse_requirements(fname='requirements.txt', versions=False):
    """
    Parse the package dependencies listed in a requirements file but strips
    specific versioning information.

    Args:
        fname (str): path to requirements file
        versions (bool | str, default=False):
            If true include version specs.
            If strict, then pin to the minimum version.

    Returns:
        List[str]: list of requirements items
    """
    from os.path import exists, dirname, join
    import re
    require_fpath = fname

    def parse_line(line, dpath=''):
        """
        Parse information from a line in a requirements text file

        line = 'git+https://a.com/somedep@sometag#egg=SomeDep'
        line = '-e git+https://a.com/somedep@sometag#egg=SomeDep'
        """
        # Remove inline comments
        comment_pos = line.find(' #')
        if comment_pos > -1:
            line = line[:comment_pos]

        if line.startswith('-r '):
            # Allow specifying requirements in other files
            target = join(dpath, line.split(' ')[1])
            for info in parse_require_file(target):
                yield info
        else:
            # See: https://www.python.org/dev/peps/pep-0508/
            info = {'line': line}
            if line.startswith('-e '):
                info['package'] = line.split('#egg=')[1]
            else:
                if ';' in line:
                    pkgpart, platpart = line.split(';')
                    # Handle platform specific dependencies
                    # setuptools.readthedocs.io/en/latest/setuptools.html
                    # #declaring-platform-specific-dependencies
                    plat_deps = platpart.strip()
                    info['platform_deps'] = plat_deps
                else:
                    pkgpart = line
                    platpart = None

                # Remove versioning from the package
                pat = '(' + '|'.join(['>=', '==', '>']) + ')'
                parts = re.split(pat, pkgpart, maxsplit=1)
                parts = [p.strip() for p in parts]

                info['package'] = parts[0]
                if len(parts) > 1:
                    op, rest = parts[1:]
                    version = rest  # NOQA
                    info['version'] = (op, version)
            yield info

    def parse_require_file(fpath):
        dpath = dirname(fpath)
        with open(fpath, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    for info in parse_line(line, dpath=dpath):
                        yield info

    def gen_packages_items():
        if exists(require_fpath):
            for info in parse_require_file(require_fpath):
                parts = [info['package']]
                if versions and 'version' in info:
                    if versions == 'strict':
                        # In strict mode, we pin to the minimum version
                        if info['version']:
                            # Only replace the first >= instance
                            verstr = ''.join(info['version']).replace('>=', '==', 1)
                            parts.append(verstr)
                    else:
                        parts.extend(info['version'])
                if not sys.version.startswith('3.4'):
                    # apparently package_deps are broken in 3.4
                    plat_deps = info.get('platform_deps')
                    if plat_deps is not None:
                        parts.append(';' + plat_deps)
                item = ''.join(parts)
                yield item

    packages = list(gen_packages_items())
    return packages


def parse_description():
    """
    Parse the description in the README file

    CommandLine:
        pandoc --from=markdown --to=rst --output=README.rst README.md
        python -c "import setup; print(setup.parse_description())"
    """
    from os.path import dirname, join, exists
    readme_fpath = join(dirname(__file__), 'README.md')
    # This breaks on pip install, so check that it exists.
    if exists(readme_fpath):
        with open(readme_fpath, 'r') as f:
            text = f.read()
        return text
    return ''


VERSION = parse_version('src/python/pycold/__init__.py')  # needs to be a global var for git tags

if __name__ == '__main__':

    # References:
    # https://stackoverflow.com/questions/19602582/pip-install-editable-links-to-wrong-path
    packages = find_packages('./src/python')
    print(f'packages={packages}')

    setup(
        package_dir={
            '': 'src/python',
        },
        name='pycold',
        url='https://github.com/GERSL/pycold',
        version=VERSION,
        description='python implementation of COntinuous monitoring of Land disturbances algorithm',
        install_requires=parse_requirements('requirements/runtime.txt'),
        long_description=parse_description(),
        long_description_content_type='text/markdown',
        extras_require={
            'all': parse_requirements('requirements.txt'),
            'tests': parse_requirements('requirements/tests.txt'),
            'build': parse_requirements('requirements/build.txt'),
            'optional': parse_requirements('requirements/optional.txt'),
            'headless': parse_requirements('requirements/headless.txt'),
            'graphics': parse_requirements('requirements/graphics.txt'),
        },
        author='Su Ye',
        author_email='remotesensingsuy@gmail.com',
        packages=packages,
        include_package_data=True,
        python_requires='>=3.6',
    )
