## Create Etch Packet

The Anvil Etch E-sign API allows you to collect e-signatures from within your
app. Send a signature packet including multiple PDFs, images, and other uploads
to one or more signers. Templatize your common PDFs then fill them with your
user's information before sending out the signature packet.

This is one of the more complex methods, but it should be a simpler process
with the builder in `python_anvil.api_resources.mutations.CreateEtchPacket`.

### Example usage

Depending on your needs, `python_api.api.create_etch_packet` accepts either a
payload in a `CreateEtchPacket`/`CreateEtchPacketPayload` dataclass type, or a
simple `dict`.

It's recommended to use the `CreateEtchPacket` class as it will build the
payload for you.


```python
from belfry_python_anvil.api import Anvil
from belfry_python_anvil.api_resources.mutations.create_etch_packet import CreateEtchPacket
from belfry_python_anvil.api_resources.payload import (
    EtchSigner,
    SignerField,
    DocumentUpload,
    EtchCastRef,
    SignatureField,
    FillPDFPayload,
)

API_KEY = 'your_api_key_here'

anvil = Anvil(api_key=API_KEY)

# Create an instance of the builder
packet = CreateEtchPacket(
    name="Packet Name",
    signature_email_subject="Please sign these forms",
)

# Gather your signer data
signer1 = EtchSigner(
    name="Jackie",
    email="jackie@example.com",
    # Fields where the signer needs to sign
    # Check your cast fields via the CLI (`anvil cast [cast_eid]`) or the
    # PDF Templates section on the Anvil app.
    # This basically says: "In the 'introPages' file (defined as
    # `pdf_template` above), assign the signature field with cast id of
    # 'def456' to this signer." You can add multiple signer fields here.
    fields=[SignerField(
        file_id="fileAlias",
        field_id="signOne",
    )],
    # By default, `signer_type` will be "email" which will automatically
    # send emails when this etch packet is created.
    # It can also be set to "embedded" which will _not_ send emails, and
    # you will need to handle sending the signer URLs manually in some way.
    signer_type="email",
    #
    # You can also change how signatures will be collected.
    # "draw" will allow the signer to draw their signature
    # "text" will insert a text version of the signer's name into the
    # signature field.
    signature_mode="draw",
    #
    # Whether or not to the signer is required to click each signature
    # field manually. If `False`, the PDF will be signed once the signer
    # accepts the PDF without making the user go through the PDF.
    accept_each_field=False,
    #
    # URL of where the signer will be redirected after signing.
    # The URL will also have certain URL params added on, so the page
    # can be customized based on the signing action.
    redirect_url="https://app.useanvil.com",
)

# Add your signer. This could also be done when the `Anvil` class is
# instantiated with `Anvil(..., signers=[signer1])`.
packet.add_signer(signer1)

# Create the files you want the signer to sign
file1 = DocumentUpload(
    id="myNewFile",
    title="Please sign this important form",
    # A base64 encoded pdf should be here.
    # Currently, this library does not do this for you, so make sure that
    # the file data is ready at this point.
    file="BASE64 ENCODED DATA HERE",
    fields=[SignatureField(
        id="firstSignature",
        type="signature",
        page_num=0,
        # The position and size of the field
        rect=dict(x=100, y=100, width=100, height=100)
    )]
)

# You can reference an existing PDF Template from your Anvil account
# instead of uploading a new file.
# You can find this information by going to the "PDF Templates" section of
# your Anvil account, choosing a template, and selecting "API Info" at the
# top-right of the page.
# Additionally, you can get this information by using the provided CLI by:
# `anvil cast --list` to list all your available templates, then:
# `anvil cast [THE_EID_OF_THE_CAST]` to get a listing of data in that
# template.
file2 = EtchCastRef(
    # The `id` here is what should be used by signer objects above.
    # This can be any string, but should be unique if adding multiple files.
    id="fileAlias",
    # The eid of the cast you want to use from "API Info" or through the CLI
    cast_eid="CAST_EID_GOES_HERE"
)

# Add files to your payload
packet.add_file(file1)
packet.add_file(file2)

# Optionally, you can pre-fill fields in the PDFs you've used above.
# This reuses the payload shape used when using the `fill_pdf` method.
packet.add_file_payloads("fileAlias", FillPDFPayload(data={
    "aTextFieldId": "This is pre-filled."
}))

anvil.create_etch_packet(payload=packet)
```
