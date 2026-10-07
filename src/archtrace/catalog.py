from pyiceberg.catalog import load_catalog

from archtrace.config import Settings


def catalog(settings: Settings):
    return load_catalog(
        "archtrace",
        type="rest",
        uri=settings.catalog_uri,
        **{
            "s3.endpoint": settings.s3_endpoint,
            "s3.access-key-id": settings.access_key,
            "s3.secret-access-key": settings.secret_key,
            "s3.region": "us-east-1",
            "py-io-impl": "pyiceberg.io.pyarrow.PyArrowFileIO",
        },
    )
