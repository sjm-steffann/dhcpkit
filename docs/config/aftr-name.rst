.. _aftr-name:

Aftr-name
=========

This sections add an AFTR tunnel endpoint name to the response sent to the client.


Example
-------

.. code-block:: dhcpkitconf

    <aftr-name>
        fqdn aftr.example.org
    </aftr-name>

.. _aftr-name_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

fqdn (required)
    The FQDN of the AFTR tunnel endpoint.

    **Example**: "aftr.example.com"

