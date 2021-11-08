from typing import Dict, List, TYPE_CHECKING

from .... import __default_endpoint__
from ....excepts import (
    ExecutorFailToLoad,
    BadConfigSource,
)
from ....executors import BaseExecutor
from ....types.arrays.abstract import AbstractDocumentArray
from ....types.arrays.document import DocumentArray
from ....types.message import Message

if TYPE_CHECKING:
    import argparse
    from ....logging.logger import JinaLogger


def _get_docs_matrix_from_message(
    msg: 'Message',
    field: str,
) -> List['DocumentArray']:
    result = [getattr(msg.request, field)]

    # to unify all length=0 DocumentArray (or any other results) will simply considered as None
    # otherwise, the executor has to handle [None, None, None] or [DocArray(0), DocArray(0), DocArray(0)]
    len_r = sum(len(r) for r in result)
    if len_r:
        return result


def _get_docs_from_msg(
    msg: 'Message',
    field: str,
) -> 'DocumentArray':
    return getattr(msg.request, field)


class DataRequestHandler:
    """Object to encapsulate the code related to handle the data requests passing to executor and its returned values"""

    def __init__(self, args: 'argparse.Namespace', logger: 'JinaLogger', **kwargs):
        """Initialize private parameters and execute private loading functions.

        :param args: args from CLI
        :param logger: the logger provided by the user
        :param kwargs: extra keyword arguments
        """
        super().__init__()
        self.args = args
        self.args.pea_id = self.args.shard_id
        self.args.parallel = self.args.shards
        self.logger = logger
        self._is_closed = False
        self._load_executor()

    def _load_executor(self):
        """Load the executor to this runtime, specified by ``uses`` CLI argument."""
        try:
            self._executor = BaseExecutor.load_config(
                self.args.uses,
                override_with=self.args.uses_with,
                override_metas=self.args.uses_metas,
                override_requests=self.args.uses_requests,
                runtime_args=vars(self.args),
                extra_search_paths=self.args.extra_search_paths,
            )
        except BadConfigSource as ex:
            self.logger.error(
                f'fail to load config from {self.args.uses}, if you are using docker image for --uses, '
                f'please use "docker://YOUR_IMAGE_NAME"'
            )
            raise ExecutorFailToLoad from ex
        except FileNotFoundError as ex:
            self.logger.error(f'fail to load file dependency')
            raise ExecutorFailToLoad from ex
        except Exception as ex:
            self.logger.critical(f'can not load the executor from {self.args.uses}')
            raise ExecutorFailToLoad from ex

    @staticmethod
    def _parse_params(parameters: Dict, executor_name: str):
        parsed_params = parameters
        specific_parameters = parameters.get(executor_name, None)
        if specific_parameters:
            parsed_params.update(**specific_parameters)
        return parsed_params

    def handle(self, msg: 'Message'):
        """Initialize private parameters and execute private loading functions.

        :param msg: The message to handle containing a DataRequest
        """
        # skip executor if endpoints mismatch
        if (
            msg.envelope.header.exec_endpoint not in self._executor.requests
            and __default_endpoint__ not in self._executor.requests
        ):
            self.logger.debug(
                f'skip executor: mismatch request, exec_endpoint: {msg.envelope.header.exec_endpoint}, requests: {self._executor.requests}'
            )
            return

        params = self._parse_params(
            msg.request.parameters.dict(), self._executor.metas.name
        )
        docs = _get_docs_from_msg(
            msg,
            field='docs',
        )
        # executor logic
        r_docs = self._executor(
            req_endpoint=msg.envelope.header.exec_endpoint,
            docs=docs,
            parameters=params,
            docs_matrix=_get_docs_matrix_from_message(
                msg,
                field='docs',
            ),
            groundtruths=_get_docs_from_msg(
                msg,
                field='groundtruths',
            ),
            groundtruths_matrix=_get_docs_matrix_from_message(
                msg,
                field='groundtruths',
            ),
        )

        # assigning result back to request
        # 1. Return none: do nothing
        # 2. Return nonempty and non-DocumentArray: raise error
        # 3. Return DocArray, but the memory pointer says it is the same as self.docs: do nothing
        # 4. Return DocArray and its not a shallow copy of self.docs: assign self.request.docs
        if r_docs is not None:
            if isinstance(r_docs, AbstractDocumentArray):
                if r_docs != msg.request.docs:
                    # this means the returned DocArray is a completely new one
                    DataRequestHandler.replace_docs(msg, r_docs)
            elif isinstance(r_docs, dict):
                msg.request.parameters.update(r_docs)
            else:
                raise TypeError(
                    f'return type must be {DocumentArray!r}, `None` or Dict, but getting {r_docs!r}'
                )

    @staticmethod
    def replace_docs(msg, docs):
        """Replaces the docs in a message with new Documents.

        :param msg: The message object
        :param docs: the new docs to be used
        """
        msg.request.docs.clear()
        msg.request.docs.extend(docs)

    def close(self):
        """ Close the data request handler, by closing the executor """
        if not self._is_closed:
            self._executor.close()
            self._is_closed = True
