"""Credential issue message handler."""

import time

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import CredentialManager
from ..messages.credential_issue import CredentialIssue

from .....utils.tracing import trace_event


class CredentialIssueHandler(BaseHandler):
    """Message handler class for credential offers."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential offers.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = time.perf_counter()

        self._logger.debug("CredentialHandler called with context %s", context)
        assert isinstance(context.message, CredentialIssue)
        self._logger.info(
            "Received credential message: %s",
            context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for credential request")

        credential_manager = CredentialManager(context)

        credential_exchange_record = await credential_manager.receive_credential()

        r_time = trace_event(
            context.settings,
            context.message,
            handler=context.settings.get("default_label")
            if context and context.settings and context.settings.get("default_label")
            else "aca-py.agent",
            outcome="CredentialIssueHandler.handle.END",
            perf_counter=r_time
        )

        # Automatically move to next state if flag is set
        if context.settings.get("debug.auto_store_credential"):
            (
                credential_exchange_record,
                credential_ack_message,
            ) = await credential_manager.store_credential(credential_exchange_record)

            # Ack issuer that holder stored credential
            await responder.send_reply(credential_ack_message)

            trace_event(
                context.settings,
                credential_ack_message,
                handler=context.settings.get("default_label")
                if context.settings and context.settings.get("default_label")
                else "aca-py.agent",
                outcome="CredentialIssueHandler.handle.STORE",
                perf_counter=r_time
            )
