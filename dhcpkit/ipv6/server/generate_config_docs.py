"""
A script to generate .rst documentation based on the config schema
"""
import argparse
import io
import logging
import os
import sys
from textwrap import dedent, indent
from typing import Iterable, List, Union
from xml.dom import Node

from ZConfig.info import AbstractType, KeyInfo, MultiKeyInfo, SchemaType, SectionInfo, SectionType
from dhcpkit.ipv6.server.config_parser import get_config_loader

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


def normalise_link_name(link: str) -> str:
    """
    Convert i.e. "filter_factory" to "filters"

    :param link: The original link name
    :return: The normalised link name
    """
    if link.endswith('_factory'):
        link = link[:-8] + 's'

    return link


def link_to(text: str, link: str = None) -> str:
    """
    Make the text a reference link.

    :param text: The text to link
    :param link: The link destination, if different from the text
    :return: The texts as a reference link
    """
    if link:
        link = normalise_link_name(link)
        return ':ref:`{} <{}>`'.format(text, link)
    else:
        text = normalise_link_name(text)
        return ':ref:`{}`'.format(text)


def link_destination(name: str) -> str:
    """
    Create an rst link.

    :param name: The destination to link to
    :return: The reStructuredText link
    """
    name = normalise_link_name(name)
    return '.. _{}:'.format(name)


def nicer_type_name(name: str) -> str:
    """
    Make a nicer name for a type.

    :param name: The ugly name
    :return: The nicer name
    """
    if name.endswith('_factory'):
        name = name[:-8] + 's'

    name = name.capitalize()

    return name


def heading(text: str, underline: str) -> str:
    """
    Create a heading using the specified underline character.

    :param text: The text to use as the heading
    :param underline: The character to underline with
    :return: The heading in rst format
    """
    return text + '\n' + (underline * len(text))


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


def write_lines(file, lines: Iterable[str]):
    """
    Write a set of lines to the file

    :param file: The file, or None
    :param lines: The lines to write
    """
    if file is None:
        return

    lines_with_nl = [line + '\n' for line in lines]
    file.writelines(lines_with_nl)


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

    # If the first line is not indented then don't include it in the dedent
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


def key_doc(info: Union[KeyInfo, MultiKeyInfo, SectionInfo]) -> List[str]:
    """
    Generate documentation for a key.

    :param info: The information object for this key
    :return: The documentation for that key
    """

    if info.name == '+':
        title = '<multiple>'
    else:
        title = str(info.name)

    # Determine extra flags
    extras = []
    if info.minOccurs > 0:
        extras += ['required']
    if info.maxOccurs > 1:
        extras += ['multiple allowed']
    if isinstance(info, SectionInfo):
        extras += ['section of type {}'.format(link_to(info.sectiontype.name))]

    if extras:
        title += ' ({})'.format(', '.join(extras))

    output = [
        title,
        reindent(info.description, '    '),
        ''
    ]

    if info.example:
        if '\n' in info.example:
            # Multi-line example
            output += [
                '    **Example**:',
                '',
                '    .. code-block:: dhcpkitconf',
                '',
                reindent(info.example, '        '),
                '',
            ]
        else:
            # Single-line example
            output += [
                '    **Example**: "{}"'.format(reindent(str(info.example))),
                '',
            ]

    default = info.getdefault()
    if default:
        # If it is a list with only one element then pretend it's not a list
        if isinstance(default, list) and len(default) == 1:
            default = default[0]

        # Format the default value(s)
        if isinstance(default, list):
            output += (
                ['    **Default**:',
                 ''] +
                ['    - "{}"'.format(reindent(str(item.value))) for item in default] +
                ['']
            )
        else:
            output += [
                '    **Default**: "{}"'.format(reindent(str(default.value))),
                '',
            ]
    elif info.metadefault:
        output += [
            '    **Default**: {}'.format(reindent(str(info.metadefault))),
            '',
        ]

    return output


def sectiontype_doc(section: SectionType) -> List[str]:
    """
    Extract the documentation for the given section.

    :param section: The section to extract documentation from
    :return: A list of strings with documentation
    """

    output = []

    # noinspection PyUnresolvedReferences
    if section.example:
        # noinspection PyUnresolvedReferences
        output += ['',
                   heading('Example', '-'),
                   '',
                   '.. code-block:: dhcpkitconf',
                   '',
                   reindent(section.example, '    '),
                   '']

    section_parameters = [(key, info) for key, info in section if key and isinstance(info, (KeyInfo, MultiKeyInfo,
                                                                                            SectionInfo))]
    subsection_types = [(key, info) for key, info in section if key is None and isinstance(info, SectionInfo)]

    if section_parameters:
        if section.name:
            output += [link_destination(section.name + '_parameters'),
                       '',
                       heading('Section parameters', '-'),
                       '']
        else:
            output += [link_destination('schema_parameters'),
                       '',
                       heading('Configuration options', '-'),
                       '']

        for key, info in section_parameters:
            output += key_doc(info)

    if subsection_types:
        output += [heading('Possible sub-section types', '-'),
                   '']

        for key, info in subsection_types:
            # Determine extra flags
            extras = []
            if info.minOccurs > 0:
                extras += ['required']
            if info.maxOccurs > 1:
                extras += ['multiple allowed']

            notes = ' ({})'.format(', '.join(extras)) if extras else ''

            output += [link_to(nicer_type_name(info.sectiontype.name), info.sectiontype.name) + notes,
                       reindent(info.sectiontype.description, '    '),
                       '']

    return output


def handle_args(args: Iterable[str]):
    """
    Handle the command line arguments.

    :param args: Command line arguments
    :return: The arguments object
    """
    parser = argparse.ArgumentParser(
        description="Generate DHCPKit configuration documentation for Sphinx.",
    )

    parser.add_argument("-o", "--output-dir", metavar="DESTDIR", required=True, help="Directory to place all output")
    parser.add_argument("-e", "--extension", metavar="PACKAGE", default='dhcpkit', help="Document the given extension")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--force", action="store_true", help="Overwrite existing files")
    group.add_argument("-n", "--dry-run", action="store_true", help="Run the script without creating files")

    args = parser.parse_args(args)

    return args


def main(args: Iterable[str]) -> int:
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
    if args.extension != 'dhcpkit':
        # ZConfig doesn't save the component description, so we'll have to find it ourselves
        description = ''

        # noinspection PyProtectedMember
        components = schema._components.items()
        for name, url in components:
            # Check the package name
            if not name.startswith('package:{}.'.format(args.extension)):
                continue

            # Open the component XML
            component = config_loader.openResource(url)
            from xml.dom.minidom import parse
            dom = parse(component.file)

            # Find the description node
            for node in dom.documentElement.childNodes:
                if node.nodeType != Node.ELEMENT_NODE or node.tagName != 'description':
                    continue

                # We found the description! Separate new description with a blank line if there is already some text
                if description:
                    description += '\n\n'

                for child_node in node.childNodes:
                    if child_node.nodeType == Node.TEXT_NODE:
                        description += child_node.nodeValue

                # Clean up the whitespace
                description = description.strip()
                break

        if not description:
            description = 'This is the documentation of the configuration options of the {} package.'.format(
                args.extension)

        # Only include this in the main configuration, not in extension docs
        write_lines(index_file, [
            heading('IPv6 Server extension configuration', '='),
            '',
            reindent(description),
            '',
        ])
    else:
        # Only include this in the main configuration, not in extension docs
        write_lines(index_file, [
            heading('IPv6 Server configuration', '='),
            '',
            reindent(schema.description),
            '',
            '.. toctree::',
            '',
            '    config_file',
            '',
        ])

        # Put the main config format in a separate file
        config_file = create_file('config_file.rst', args)
        write_lines(config_file, [
            heading('Configuration file format', '='),
            '',
            reindent(schema.description),
            '',
        ] + sectiontype_doc(schema))

    # Keep track of which section types are covered under abstract types
    handled_section_types = set()

    # Collect types
    abstract_types = set()
    section_types = set()
    for type_name in schema.gettypenames():
        section_type = schema.gettype(type_name)

        if isinstance(section_type, AbstractType):
            # Remember which section types are covered here
            handled_section_types.update(set(section_type.getsubtypenames()))
            abstract_types.add(section_type)
        elif isinstance(section_type, SectionType):
            # If we are limited to a single extension then try to determine if this section type belongs to that
            # extension by looking at the datatype. It isn't pretty but it works...
            datatype = getattr(section_type, 'datatype', None)
            if not datatype.__module__.startswith(args.extension + '.'):
                continue

            section_types.add(section_type)

    # Only include section types with no underscore in the name
    section_types = [section_type for section_type in section_types if '_' not in section_type.name]
    section_types = sorted(section_types, key=lambda t: t.name)

    # Only include section types we have collected before
    documented_names = set([section_type.name for section_type in section_types])
    abstract_types = [abstract_type for abstract_type in abstract_types
                      if documented_names.intersection(abstract_type.getsubtypenames())]
    abstract_types = sorted(abstract_types, key=lambda t: t.name)

    # These are the section types that are not under an abstract section type
    root_types = [section_type for section_type in section_types if section_type.name not in handled_section_types]

    if root_types:
        # Table of contents
        write_lines(index_file, [
            heading('Overview of sections', '-'),
            '',
            '.. toctree::',
            '    :maxdepth: 1',
            '',
        ])

        # A file for each section type that hasn't been handled already
        for section_type in root_types:
            # Write a reference to the index
            write_lines(index_file, ['    ' + section_type.name])

            # Write the file
            file = create_file(section_type.name + '.rst', args)
            write_lines(file, [
                link_destination(section_type.name),
                '',
                heading(nicer_type_name(section_type.name), '='),
                '',
                reindent(section_type.description),
                ''
            ])
            write_lines(file, sectiontype_doc(section_type))

    if abstract_types:
        # Table of contents
        write_lines(index_file, [
            '',
            heading('Overview of section types', '-'),
            '',
            '.. toctree::',
            '    :maxdepth: 2',
            '',
        ])

        # A file for each abstract type
        for section_type in abstract_types:
            subtypes = section_type.getsubtypenames()

            # Only include section types we have collected before
            subtypes = [subtype for subtype in subtypes if subtype in documented_names]

            if not subtypes:
                # Don't generate documentation for abstract types with no implementation
                continue

            # Write a reference to the index
            write_lines(index_file, ['    ' + section_type.name])

            # Write the file
            file = create_file(section_type.name + '.rst', args)
            write_lines(file, [
                link_destination(section_type.name),
                '',
                heading(nicer_type_name(section_type.name), '='),
                '',
                reindent(section_type.description),
                '',
                '.. toctree::',
                '',
            ])

            # Write the implementations
            for subtype_name in subtypes:
                subtype = section_type.getsubtype(subtype_name)

                write_lines(file, ['    ' + subtype.name])

                sub_file = create_file(subtype.name + '.rst', args)
                write_lines(sub_file, [
                    link_destination(subtype.name),
                    '',
                    heading(nicer_type_name(subtype.name), '='),
                    '',
                    reindent(subtype.description),
                    ''
                ] + sectiontype_doc(subtype))

    return 0


def run() -> int:
    """
    Run the main program and handle exceptions

    :return: The program exit code
    """
    try:
        # Run the server
        return main(sys.argv[1:])
    except Exception as e:
        logger.critical("Error: {}".format(e))
        return 1


if __name__ == '__main__':
    sys.exit(run())
