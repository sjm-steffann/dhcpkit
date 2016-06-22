"""
A script to generate .rst documentation based on the config schema
"""
import argparse
import io
import logging
import os
from textwrap import dedent, indent

from ZConfig.info import SchemaType, SectionType, AbstractType, SectionInfo, KeyInfo

from dhcpkit.ipv6.server.config_parser import get_config_loader, load_config

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


# [('user', <KeyInfo for 'user'>),
#  ('group', <KeyInfo for 'group'>),
#  ('workers', <KeyInfo for 'workers'>),
#  ('allow-rapid-commit', <KeyInfo for 'allow-rapid-commit'>),
#  ('rapid-commit-rejections', <KeyInfo for 'rapid-commit-rejections'>),
#  ('server-id', <SectionInfo for duid ('server-id')>),
#  ('exception-window', <KeyInfo for 'exception-window'>),
#  ('max-exceptions', <KeyInfo for 'max-exceptions'>),
#  (None, <SectionInfo for logging ('*')>),
#  (None, <SectionInfo for listener_factory ('*')>),
#  (None, <SectionInfo for filter_factory ('*')>),
#  (None, <SectionInfo for handler_factory ('*')>)]

def create_file(name, args):
    """
    Create a file, or a file-like dummy if dry-run is enabled

    :param name: The relative file/path name
    :param args: The command like arguments
    :return: A file-like object
    """
    full_name = os.path.join(args.output_dir, name)

    if args.dry_run:
        logger.info("Dry-run, would have written to {}".format(full_name))
        return io.StringIO()

    if os.path.exists(full_name) and not args.force:
        logger.info("Skipping existing file, would have written to {}".format(full_name))
        return None

    # Make the directory, just to be sure
    os.makedirs(os.path.dirname(full_name), exist_ok=True)

    # Create and return the file
    logger.info("Creating {}".format(full_name))
    return open(full_name, 'w')


def write_lines(file, lines: [str]):
    """
    Write a set of lines to the file

    :param file: The file, or None
    :param lines: The lines to write
    """
    if file is None:
        return

    lines_with_nl = [line + '\n' for line in lines]
    file.writelines(lines_with_nl)


def ref(text: str, link: str = None) -> str:
    """
    Make the text a reference link.

    :param text: The text to link
    :param link: The link destination, if different from the text
    :return: The texts as a reference link
    """
    if link:
        return ':ref:`{} <{}>`'.format(text, link)
    else:
        return ':ref:`{}`'.format(text)


def reindent(text: str, new_indent: str = '') -> str:
    """
    Fix the indentation.

    :param text: The original text with unknown indentation
    :param new_indent: The string to indent with
    :return: The text with fixed indentation
    """
    if text is None:
        return ''

    # Split lines
    lines = text.split('\n')

    # If the first line is not indented then don't include it
    if not lines[0].startswith((' ', '\t')):
        output = lines.pop(0)
    else:
        output = ''

    # Join the rest together
    text = '\n'.join(lines)

    # Dedent (remove common indents)
    text = dedent(text)

    if text:
        output += '\n' + text

    return indent(output, new_indent)


def key_doc(info: KeyInfo) -> [str]:
    """
    Generate documentation for a key.

    :param info: The information object for this key
    :return: The documentation for that key
    """
    output = [
        str(info.name),
        reindent(info.description, '    ')
    ]

    default = info.getdefault()
    if default:
        output += [
            '',
            '    **Default**: "' + str(default.value) + '"',
        ]
    elif info.metadefault:
        output += [
            '',
            '    **Default**: ' + str(info.metadefault),
        ]

    output += ['']
    return output


def sectiontype_doc(section: SectionType) -> [str]:
    """
    Extract the documentation for the given section.

    :param section: The section to extract documentation from
    :return: A list of strings with documentation
    """

    output = []

    if section.example:
        output += ['',
                   'Example',
                   '^^^^^^^',
                   '',
                   '.. code-block:: apacheconf',
                   '',
                   reindent(section.example, '    ')]

    section_parameters = [(key, info) for key, info in section if key and isinstance(info, (KeyInfo, SectionInfo))]
    subsection_types = [(key, info) for key, info in section if key is None and isinstance(info, SectionInfo)]

    if section_parameters:
        if section.name:
            output += ['Section parameters',
                       '^^^^^^^^^^^^^^^^^^']
        else:
            output += ['Configuration options',
                       '^^^^^^^^^^^^^^^^^^^^^']

        for key, info in section_parameters:
            if isinstance(info, KeyInfo):
                output += key_doc(info)
            elif isinstance(info, SectionInfo):
                output += ['{key} (section of type {type})'.format(key=key,
                                                                   type=ref(nicer_type_name(info.sectiontype.name),
                                                                            info.sectiontype.name)),
                           reindent(info.description, '    '),
                           '']

    if subsection_types:
        output += ['',
                   'Possible sub-section types',
                   '^^^^^^^^^^^^^^^^^^^^^^^^^^']

        for key, info in subsection_types:
            output += [ref(nicer_type_name(info.sectiontype.name), info.sectiontype.name),
                       reindent(info.sectiontype.description, '    '),
                       '']

    return output


def nicer_type_name(name: str) -> str:
    """
    Make a nicer name for a type.

    :param name: The ugly name
    :return: The nicer name
    """
    if name.endswith('_factory'):
        name = name[:-8]

    name = name.capitalize()

    return name


def handle_args(args: [str]):
    """
    Handle the command line arguments.

    :param args: Command line arguments
    :return: The arguments object
    """
    parser = argparse.ArgumentParser(
        description="Generate configuration documentation for Sphinx.",
    )

    parser.add_argument("-o", "--output-dir", metavar="DESTDIR", required=True, help="Directory to place all output")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--force", action="store_true", help="Overwrite existing files")
    group.add_argument("-n", "--dry-run", action="store_true", help="Run the script without creating files")

    args = parser.parse_args(args)

    return args


def main(args: [str]) -> int:
    """
    Generate .rst documentation based on the config schema

    :param args: Command line arguments
    :return: Program exit code
    """
    # Handle the command line arguments
    args = handle_args(args)

    # Get the configuration schema with extensions
    config_loader = get_config_loader()
    schema = config_loader.schema
    assert isinstance(schema, SchemaType)

    # The index
    index_file = create_file('index.rst', args)
    write_lines(index_file, [
        'IPv6 Server configuration',
        '=========================',
        reindent(schema.description),
        '',
    ])

    write_lines(index_file, sectiontype_doc(schema))

    # Table of contents
    write_lines(index_file, [
        'Available sections',
        '^^^^^^^^^^^^^^^^^^',
        '',
        '.. toctree::',
        '',
    ])

    # Keep track of which section types are covered under abstract types
    handled_section_types = set()

    # Collect types
    abstract_types = set()
    section_types = set()
    for type_name in schema.gettypenames():
        my_type = schema.gettype(type_name)
        if isinstance(my_type, AbstractType):
            # Remember which section types are covered here
            handled_section_types.update(set(my_type.getsubtypenames()))
            abstract_types.add(my_type)
        elif isinstance(my_type, SectionType):
            section_types.add(my_type)

    # A file for each section type that hasn't been handled already
    for my_type in section_types:
        if '_' in my_type.name or my_type.name in handled_section_types:
            continue

        # Write a reference to the index
        write_lines(index_file, ['    ' + my_type.name])

        # Write the file
        file = create_file(my_type.name + '.rst', args)
        write_lines(file, [
            '.. _{}:'.format(my_type.name),
            nicer_type_name(my_type.name),
            '=' * len(my_type.name),
            reindent(my_type.description),
            ''
        ])
        write_lines(file, sectiontype_doc(my_type))

    # A file for each abstract type
    for my_type in abstract_types:
        # Write a reference to the index
        write_lines(index_file, ['    ' + my_type.name])

        # Write the file
        file = create_file(my_type.name + '.rst', args)
        write_lines(file, [
            '.. _{}:'.format(my_type.name),
            nicer_type_name(my_type.name),
            '=' * len(my_type.name),
            reindent(my_type.description),
            ''
        ])

        # Write the implementations
        for subtype_name in my_type.getsubtypenames():
            subtype = my_type.getsubtype(subtype_name)

            write_lines(file, [
                '.. _{}:'.format(subtype.name),
                nicer_type_name(subtype.name),
                '-' * len(subtype.name),
                reindent(subtype.description),
                ''
            ])
            write_lines(file, sectiontype_doc(subtype))


if __name__ == '__main__':
    # sys.exit(main(sys.argv[1:]))

    config = load_config('test_server.conf')
    print(config)
