# pylint: disable=too-many-instance-attributes
import logging
from io import BufferedIOBase
from logging import Logger
from mimetypes import guess_type
from typing import Any, Dict, List, Optional, Union

from belfry_python_anvil.api_resources.mutations.base import BaseQuery
from belfry_python_anvil.api_resources.payload import (
    AttachableEtchFile,
    CreateEtchFilePayload,
    CreateEtchPacketPayload,
    DocumentUpload,
    EtchSigner,
)
from belfry_python_anvil.utils import create_unique_id


logger: Logger = logging.getLogger(__name__)

DEFAULT_RESPONSE_QUERY = """{
  eid
  name
  detailsURL
  documentGroup {
    eid
    status
    files
    signers {
      eid
      aliasId
      routingOrder
      name
      email
      status
      signActionType
    }
  }
}"""

# NOTE: Since the below will be used as a formatted string (this also applies
#   to f-strings) any literal curly braces need to be doubled, else they'll be
#   interpreted as string replacement tokens.
CREATE_ETCH_PACKET = """
mutation CreateEtchPacket (
    $name: String,
    $files: [EtchFile!],
    $isDraft: Boolean,
    $isTest: Boolean,
    $mergePDFs: Boolean,
    $signatureEmailSubject: String,
    $signatureEmailBody: String,
    $signatureProvider: String,
    $signaturePageOptions: JSON,
    $signers: [JSON!],
    $webhookURL: String,
    $replyToName: String,
    $replyToEmail: String,
    $data: JSON,
    $enableEmails: JSON,
    $createCastTemplatesFromUploads: Boolean,
    $duplicateCasts: Boolean=false,
  ) {{
    createEtchPacket (
      name: $name,
      files: $files,
      isDraft: $isDraft,
      isTest: $isTest,
      mergePDFs: $mergePDFs,
      signatureEmailSubject: $signatureEmailSubject,
      signatureEmailBody: $signatureEmailBody,
      signatureProvider: $signatureProvider,
      signaturePageOptions: $signaturePageOptions,
      signers: $signers,
      webhookURL: $webhookURL,
      replyToName: $replyToName,
      replyToEmail: $replyToEmail,
      data: $data,
      enableEmails: $enableEmails,
      createCastTemplatesFromUploads: $createCastTemplatesFromUploads,
      duplicateCasts: $duplicateCasts
    )
        {query}
  }}
"""


class CreateEtchPacket(BaseQuery):
    mutation = CREATE_ETCH_PACKET
    mutation_res_query = DEFAULT_RESPONSE_QUERY

    def __init__(  # pylint: disable=too-many-locals
        self,
        name: Optional[str] = None,
        signature_email_subject: Optional[str] = None,
        signature_email_body: Optional[str] = None,
        signers: Optional[List[EtchSigner]] = None,
        files: Optional[List[AttachableEtchFile]] = None,
        file_payloads: Optional[dict] = None,
        signature_page_options: Optional[Dict[Any, Any]] = None,
        is_draft: bool = False,
        is_test: bool = True,
        payload: Optional[CreateEtchPacketPayload] = None,
        webhook_url: Optional[str] = None,
        reply_to_name: Optional[str] = None,
        reply_to_email: Optional[str] = None,
        merge_pdfs: Optional[bool] = None,
        enable_emails: Optional[Union[bool, List[str]]] = None,
        create_cast_templates_from_uploads: Optional[bool] = None,
        duplicate_casts: Optional[bool] = None,
    ):
        # `name` is required when `payload` is not present.
        if not payload and not name:
            raise TypeError(
                "Missing 2 required positional arguments: 'name' and "
                "'signature_email_subject'"
            )

        self.name = name
        self.signature_email_subject = signature_email_subject
        self.signature_email_body = signature_email_body
        self.signature_page_options = signature_page_options
        self.signers = signers or []
        self.files = files or []
        self.file_payloads = file_payloads or {}
        self.is_draft = is_draft
        self.is_test = is_test
        self.payload = payload
        self.webhook_url = webhook_url
        self.reply_to_name = reply_to_name
        self.reply_to_email = reply_to_email
        self.merge_pdfs = merge_pdfs
        self.enable_emails = enable_emails
        self.create_cast_templates_from_uploads = create_cast_templates_from_uploads
        self.duplicate_casts = duplicate_casts

    @classmethod
    def create_from_dict(cls, payload: Dict) -> 'CreateEtchPacket':
        """Create a new instance of `CreateEtchPacket` from a dict payload."""
        try:
            mutation = cls(
                **{k: v for k, v in payload.items() if k not in ["signers", "files"]}
            )
        except TypeError as e:
            raise ValueError(
                f"`payload` must be a valid CreateEtchPacket instance or dict. {e}"
            ) from e
        if "signers" in payload:
            for signer in payload["signers"]:
                mutation.add_signer(EtchSigner(**signer))

        if "files" in payload:
            for file in payload["files"]:
                mutation.add_file(DocumentUpload(**file))

        return mutation

    def add_signer(self, signer: Union[dict, EtchSigner]):
        """Add a signer to the mutation payload.

        :param signer: Signer object to add to the payload
        :type signer: dict|EtchSigner
        """
        if isinstance(signer, dict):
            data = EtchSigner(**signer)
        elif isinstance(signer, EtchSigner):
            data = signer
        else:
            raise ValueError("Signer must be either a dict or EtchSigner type")

        if data.signer_type not in ["embedded", "email"]:
            raise ValueError(
                "Etch signer `signer_type` must be only 'embedded' or 'email"
            )

        if not data.id:
            data.id = create_unique_id("signer")
        if not data.routing_order:
            if self.signers:
                # Basic thing to get the next number
                # But this might not be necessary since API goes by index
                # of signers in the list.
                all_signers = [(s.routing_order or 0) for s in self.signers]
                num = max(all_signers) + 1
            else:
                num = 1
            data.routing_order = num

        self.signers.append(data)

    def add_file(self, file: AttachableEtchFile):
        """Add file to a pending list of Upload objects.

        Files will not be uploaded when running this method. They will be
        uploaded when the mutation actually runs.
        """
        if (
            isinstance(file, DocumentUpload)
            and isinstance(file.file, BufferedIOBase)
            and getattr(file.file, "content_type", None) is None
        ):
            # Don't clobber existing `content_type`s provided.
            content_type, _ = guess_type(file.file.name)  # type: ignore
            logger.debug(
                "File did not have a `content_type`, guessing as '%s'", content_type
            )
            file.file.content_type = content_type  # type: ignore

        self.files.append(file)

    def add_file_payloads(self, file_id: str, fill_payload):
        existing_files = [f.id for f in self.files if f]
        if file_id not in existing_files:
            raise ValueError(
                f"`{file_id}` was not added as a file. Please add "
                f"the file first before adding a fill payload."
            )
        self.file_payloads[file_id] = fill_payload

    def get_file_payloads(self):
        existing_files = [f.id for f in self.files if f]
        for key, _ in self.file_payloads.items():
            if key not in existing_files:
                raise ValueError(
                    f"`{key}` was not added as a file. Please add "
                    f"that file or remove its fill payload before "
                    f"attempting to create an Etch payload."
                )
        return self.file_payloads

    def create_payload(self) -> CreateEtchPacketPayload:
        """Create a payload based on data set on the class instance.

        Check `api_resources.payload.CreateEtchPacketPayload` for full payload
        requirements. Data requirements aren't explicitly enforced here, but
        at the payload class level.
        """
        # If there's an existing payload instance attribute, just return that.
        if self.payload:
            return self.payload

        if not self.name:
            raise TypeError("`name` and `signature_email_subject` cannot be None")

        payload = CreateEtchPacketPayload(
            is_test=self.is_test,
            is_draft=self.is_draft,
            name=self.name,
            signers=self.signers,
            files=self.files,
            data=CreateEtchFilePayload(payloads=self.get_file_payloads()),
            signature_email_subject=self.signature_email_subject,
            signature_email_body=self.signature_email_body,
            signature_page_options=self.signature_page_options or {},
            webhook_url=self.webhook_url,
            reply_to_email=self.reply_to_email,
            reply_to_name=self.reply_to_name,
            merge_pdfs=self.merge_pdfs,
            enable_emails=self.enable_emails,
            create_cast_templates_from_uploads=self.create_cast_templates_from_uploads,
            duplicate_casts=self.duplicate_casts,
        )

        return payload
