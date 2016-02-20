'''
Set up the version of Maestro Client API
'''

# Import python libs
import sys

__version_info__ = (0, 8, 7)
__version__ = '.'.join(map(str, __version_info__))


def versions_report():
    '''
    Report on all of the versions for dependant software
    '''
    libs = (
    )

    padding = len(max([lib[0] for lib in libs], key=len)) + 1

    fmt = '{0:>{pad}}: {1}'

    yield fmt.format('Maestro', __version__, pad=padding)

    yield fmt.format(
        'Python', sys.version.rsplit('\n')[0].strip(), pad=padding
    )

    for name, imp, attr in libs:
        try:
            imp = __import__(imp)
            version = getattr(imp, attr)
            if not isinstance(version, basestring):
                version = '.'.join(map(str, version))
            yield fmt.format(name, version, pad=padding)
        except ImportError:
            yield fmt.format(name, 'not installed', pad=padding)


if __name__ == '__main__':
    print(__version__)
