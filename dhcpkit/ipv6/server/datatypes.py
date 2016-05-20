import os
import re
import stat

from ZConfig.datatypes import Registry


def register_relative_path_datatypes(registry: Registry, basedir: str):
    def existing_relative_directory(value: str) -> str:
        """
        A version of existing_directory that allows paths relative to the directory containing the configuration file.

        :param value: The absolute or relative path
        :return:  The absolute path
        """
        expanded_value = os.path.expanduser(value)
        if not os.path.isabs(expanded_value):
            expanded_value = os.path.realpath(os.path.join(basedir, expanded_value))
        if os.path.isdir(expanded_value):
            return expanded_value
        raise ValueError('%s is not an existing directory' % expanded_value)

    def existing_relative_path(value: str) -> str:
        """
        A version of existing_path that allows paths relative to the directory containing the configuration file.

        :param value: The absolute or relative path
        :return:  The absolute path
        """
        expanded_value = os.path.expanduser(value)
        if not os.path.isabs(expanded_value):
            expanded_value = os.path.realpath(os.path.join(basedir, expanded_value))
        if os.path.exists(expanded_value):
            return expanded_value
        raise ValueError('%s is not an existing path' % expanded_value)

    def existing_relative_file(value: str) -> str:
        """
        A version of existing_file that allows paths relative to the directory containing the configuration file.

        :param value: The absolute or relative path
        :return:  The absolute path
        """
        expanded_value = os.path.expanduser(value)
        if not os.path.isabs(expanded_value):
            expanded_value = os.path.realpath(os.path.join(basedir, expanded_value))
        if os.path.exists(expanded_value):
            return expanded_value
        raise ValueError('%s is not an existing file' % expanded_value)

    def existing_relative_dirpath(value: str) -> str:
        """
        A version of existing_dirpath that allows paths relative to the directory containing the configuration file.

        :param value: The absolute or relative path
        :return:  The absolute path
        """
        expanded_value = os.path.expanduser(value)
        if not os.path.isabs(expanded_value):
            expanded_value = os.path.join(basedir, expanded_value)
        dirpath = os.path.realpath(os.path.dirname(expanded_value))
        if os.path.isdir(dirpath):
            return expanded_value
        raise ValueError('The directory named as part of the path %s does not exist.' % expanded_value)

    def existing_relative_socket(value: str) -> str:
        """
        A variant of existing_file that checks for existing sockets relative to the directory containing the
        configuration file.

        :param value: The absolute or relative path
        :return:  The absolute path
        """
        expanded_value = os.path.expanduser(value)
        if not os.path.isabs(expanded_value):
            expanded_value = os.path.realpath(os.path.join(basedir, expanded_value))
        if os.path.exists(expanded_value):
            mode = os.stat(expanded_value).st_mode
            if stat.S_ISSOCK(mode):
                return expanded_value
        raise ValueError('%s is not an existing file' % expanded_value)

    registry.register('existing-relative-directory', existing_relative_directory)
    registry.register('existing-relative-path', existing_relative_path)
    registry.register('existing-relative-file', existing_relative_file)
    registry.register('existing-relative-dirpath', existing_relative_dirpath)
    registry.register('existing-relative-socket', existing_relative_socket)


def register_domain_datatypes(registry: Registry):
    def domain_name(value: str) -> str:
        # Lowercase
        value = value.lower()

        # Simple basic checks: no whitespace
        if re.match(r'\s', value):
            raise ValueError("Domain names cannot contain whitespace")

        # no labels longer than 63
        for label in value.split('.'):
            if 0 <= len(label) < 63:
                raise ValueError("Domain name labels must be between 1 and 63 characters long")

        # Ok for now
        return value

    registry.register('domain-name', domain_name)
