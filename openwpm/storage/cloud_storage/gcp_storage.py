import asyncio
import logging
from functools import partial
from typing import Any, Callable, Optional, Set

import pyarrow.parquet as pq
from gcsfs import GCSFileSystem
from pyarrow.lib import Table

from ..arrow_storage import ArrowProvider
from ..storage_providers import TableName, UnstructuredStorageProvider


class GcsStructuredProvider(ArrowProvider):
    """This class allows you to upload Parquet files to GCS.
    This might not actually be the thing that we want to do
    long term but seeing as GCS is the S3 equivalent of GCP
    it is the easiest way forward.
    """

    def __init__(
        self,
        project: str,
        bucket_name: str,
        base_path: str,
        token: str = None,
    ) -> None:
        super().__init__()
        self.project = project
        self.bucket_name = bucket_name
        self.base_path = base_path
        self.token = token
        self.file_system: Optional[GCSFileSystem] = None
        self.base_path = f"{self.bucket_name}/{base_path}/{{table_name}}"

    async def init(self) -> None:
        self.file_system = GCSFileSystem(
            project=self.project, token=self.token, access="read_write"
        )

    async def write_table(self, table_name: TableName, table: Table) -> None:
        assert self.file_system is not None
        self.file_system.start_transaction()
        pq.write_to_dataset(
            table,
            self.base_path.format(table_name=table_name),
            filesystem=self.file_system,
        )
        self.file_system.end_transaction()

    async def shutdown(self) -> None:
        pass


class GcsUnstructuredProvider(UnstructuredStorageProvider):
    """This class allows you to upload Parquet files to GCS.
    This might not actually be the thing that we want to do
    long term but seeing as GCS is the S3 equivalent of GCP
    it is the easiest way forward.
    """

    def __init__(
        self,
        project: str,
        bucket_name: str,
        base_path: str,
        token: str = None,
    ) -> None:
        super().__init__()
        self.project = project
        self.bucket_name = bucket_name
        self.base_path = base_path
        self.token = token
        self.file_system: Optional[GCSFileSystem] = None
        self.base_path = f"{bucket_name}/{base_path}/{{filename}}"

        self.file_name_cache: Set[str] = set()
        """The set of all filenames ever uploaded, checked before uploading"""
        self.logger = logging.getLogger("openwpm")

    async def init(self) -> None:
        pass

    async def store_blob(
        self, filename: str, blob: bytes, overwrite: bool = False
    ) -> None:
        assert self.file_system is not None
        target_path = self.base_path.format(filename=filename)
        if not overwrite and (
            filename in self.file_name_cache or self.file_system.exists(target_path)
        ):
            self.logger.info("Not saving out file %s as it already exists", filename)
            return

        with self.file_system.open(target_path, mode="wb") as f:
            f.write(blob)
        self.file_name_cache.add(filename)

    async def flush_cache(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass