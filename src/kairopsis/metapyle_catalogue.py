"""Manage a Metapyle YAML catalogue using its public loading/validation API."""
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

import metapyle
from metapyle.catalog import Catalog, CatalogEntry

from .models import SeriesBinding
from .repository import atomic_bytes


def entries_for(bindings: tuple[SeriesBinding, ...]) -> dict[str, CatalogEntry]:
    entries: dict[str, CatalogEntry] = {}
    for binding in bindings:
        if binding.catalog_name is None:
            continue  # Old fixtures/evidence retain their original binding contract.
        if binding.catalog_name in entries:
            raise ValueError("Catalogue names must be unique")
        if binding.path is not None and not Path(binding.path).is_absolute():
            raise ValueError("Data file paths must be absolute")
        entries[binding.catalog_name] = CatalogEntry(my_name=binding.catalog_name,
            source=binding.source, symbol=binding.instrument, field=binding.field,
            path=binding.path, params=binding.params or None,
            description=binding.description, unit=binding.unit)
    return entries


def serialize_catalogue(bindings: tuple[SeriesBinding, ...]) -> bytes:
    # Catalog's constructor does not run the same validation as from_yaml.
    # Export and reload before publishing; do not reproduce provider rules here.
    with TemporaryDirectory(prefix="kairopsis-catalog-") as directory:
        path = Path(directory) / "catalog.yaml"
        Catalog(entries_for(bindings)).to_yaml(path)
        validate_catalogue(path)
        # Client initialization invokes registered-source validation publicly.
        try:
            client = metapyle.Client(catalog=path, cache_enabled=False)
            client.close()
        except metapyle.MetapyleError as error:
            raise ValueError(f"Invalid Metapyle catalogue ({type(error).__name__}). Select a source registered in the installed Metapyle library.") from None
        return path.read_bytes()


def validate_catalogue(path: Path) -> Catalog:
    try:
        catalog = Catalog.from_yaml(path)
        return catalog
    except Exception as error:
        # Configuration values/params may contain private information.
        raise ValueError(f"Invalid Metapyle catalogue ({type(error).__name__}). Check unique names, registered source and its field/path requirements.") from None


def publish_catalogue(path: Path, bindings: tuple[SeriesBinding, ...]) -> None:
    atomic_bytes(path, serialize_catalogue(bindings))


def matches_catalogue(path: Path, bindings: tuple[SeriesBinding, ...]) -> bool:
    catalog = validate_catalogue(path)
    return all(binding.catalog_name is not None and binding.catalog_name in catalog
        and asdict(catalog.get(binding.catalog_name)) == asdict(entries_for((binding,))[binding.catalog_name])
        for binding in bindings)
