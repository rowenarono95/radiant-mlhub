"""Extensions of the `PySTAC <https://pystac.readthedocs.io/en/latest/>`_ classes that provide convenience methods for interacting
with the `Radiant MLHub API <https://docs.mlhub.earth/#radiant-mlhub-api>`_."""

import concurrent.futures
from collections.abc import Sequence
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Iterator, List, Optional, Union

import pystac

from . import client
from .exceptions import EntityDoesNotExist


class Collection(pystac.Collection):
    """Class inheriting from :class:`pystac.Collection` that adds some convenience methods for listing and fetching
    from the Radiant MLHub API.
    """

    def __init__(self, id, description, extent, title, stac_extensions, href, extra_fields, catalog_type, license,
                 keywords, providers, properties, summaries, *, api_key=None, profile=None):
        super().__init__(id, description, extent, title=title, stac_extensions=stac_extensions, href=href,
                         extra_fields=extra_fields, catalog_type=catalog_type, license=license, keywords=keywords,
                         providers=providers, properties=properties, summaries=summaries)

        self.session_kwargs = {}
        if api_key is not None:
            self.session_kwargs['api_key'] = api_key
        if profile is not None:
            self.session_kwargs['profile'] = profile

        # Use -1 here instead of None because None represents the case where the archive does not
        #  exist (HEAD returns a 404).
        self._archive_size = -1

    @classmethod
    def list(cls, **session_kwargs) -> List['Collection']:
        """Returns a list of :class:`Collection` instances for all collections hosted by MLHub.

        See the :ref:`Authentication` documentation for details on how authentication is handled for this request.

        Parameters
        ----------
        **session_kwargs
            Keyword arguments passed directly to :func:`~radiant_mlhub.session.get_session`

        Returns
        ------
        collections : List[Collection]
        """
        return [
            cls.from_dict(collection)
            for collection in client.list_collections(**session_kwargs)
        ]

    @classmethod
    def from_dict(cls, d, href=None, root=None, *, api_key=None, profile=None):
        """Patches the :meth:`pystac.Collection.from_dict` method so that it returns the calling class instead of always returning
        a :class:`pystac.Collection` instance."""
        catalog_type = pystac.CatalogType.determine_type(d)

        d = deepcopy(d)
        id_ = d.pop('id')
        description = d.pop('description')
        license_ = d.pop('license')
        extent = pystac.Extent.from_dict(d.pop('extent'))
        title = d.get('title')
        stac_extensions = d.get('stac_extensions')
        keywords = d.get('keywords')
        providers = d.get('providers')
        if providers is not None:
            providers = list(map(lambda x: pystac.Provider.from_dict(x), providers))
        properties = d.get('properties')
        summaries = d.get('summaries')
        links = d.pop('links')

        d.pop('stac_version')

        collection = cls(
            id=id_,
            description=description,
            extent=extent,
            title=title,
            stac_extensions=stac_extensions,
            extra_fields=d,
            license=license_,
            keywords=keywords,
            providers=providers,
            properties=properties,
            summaries=summaries,
            href=href,
            catalog_type=catalog_type,
            api_key=api_key,
            profile=profile
        )

        for link in links:
            if link['rel'] == 'root':
                # Remove the link that's generated in Catalog's constructor.
                collection.remove_links('root')

            if link['rel'] != 'self' or href is None:
                collection.add_link(pystac.Link.from_dict(link))

        return collection

    @classmethod
    def fetch(cls, collection_id: str, **session_kwargs) -> 'Collection':
        """Creates a :class:`Collection` instance by fetching the collection with the given ID from the Radiant MLHub API.

        Parameters
        ----------
        collection_id : str
            The ID of the collection to fetch (e.g. ``bigearthnet_v1_source``).
        **session_kwargs
            Keyword arguments passed directly to :func:`~radiant_mlhub.session.get_session`

        Returns
        -------
        collection : Collection
        """
        response = client.get_collection(collection_id, **session_kwargs)
        return cls.from_dict(response, **session_kwargs)

    def get_items(self, **session_kwargs) -> Iterator[pystac.Item]:
        """
        .. note::

            The ``get_items`` method is not implemented for Radiant MLHub :class:`Collection` instances for performance reasons. Please use
            the :meth:`Collection.download` method to download Collection assets.

        Raises
        ------
        NotImplementedError
        """
        raise NotImplementedError('For performance reasons, the get_items method has not been implemented for Collection instances. Please '
                                  'use the Collection.download method to download Collection assets.')

    def fetch_item(self, item_id: str, **session_kwargs) -> pystac.Item:
        session_kwargs = {
            **self.session_kwargs,
            **session_kwargs
        }
        response = client.get_collection_item(self.id, item_id, **session_kwargs)
        return pystac.Item.from_dict(response)

    def download(
            self,
            output_dir: Path,
            *,
            if_exists: str = 'resume',
            **session_kwargs
    ) -> Path:
        """Downloads the archive for this collection to an output location (current working directory by default). If the parent directories
        for ``output_path`` do not exist, they will be created.

        The ``if_exists`` argument determines how to handle an existing archive file in the output directory. See the documentation for
        the :func:`~radiant_mlhub.client.download_archive` function for details. The default behavior is to resume downloading if the
        existing file is incomplete and skip the download if it is complete.

        .. note::

            Some collections may be very large and take a significant amount of time to download, depending on your connection speed.

        Parameters
        ----------
        output_dir : Path
            Path to a local directory to which the file will be downloaded. File name will be generated
            automatically based on the download URL.
        if_exists : str, optional
            How to handle an existing archive at the same location. If ``"skip"``, the download will be skipped. If ``"overwrite"``,
            the existing file will be overwritten and the entire file will be re-downloaded. If ``"resume"`` (the default), the
            existing file size will be compared to the size of the download (using the ``Content-Length`` header). If the existing
            file is smaller, then only the remaining portion will be downloaded. Otherwise, the download will be skipped.
        **session_kwargs
            Keyword arguments passed directly to :func:`~radiant_mlhub.session.get_session`

        Returns
        -------
        output_path : pathlib.Path
            The path to the downloaded archive file.

        Raises
        ------
        FileExistsError
            If file at ``output_path`` already exists and both ``exist_okay`` and ``overwrite`` are ``False``.
        """
        session_kwargs = {
            **self.session_kwargs,
            **session_kwargs
        }
        return client.download_archive(self.id, output_dir=output_dir, if_exists=if_exists, **session_kwargs)

    @property
    def registry_url(self) -> Optional[str]:
        """The URL of the registry page for this Collection. The URL is based on the DOI identifier
        for the collection. If the Collection does not have a ``"sci:doi"`` property then
        ``registry_url`` will be ``None``."""

        # Some Collections don't publish the "scientific" extension in their "stac_extensions"
        # attribute so we access this via "extra_fields" rather than through self.ext["scientific"].
        doi = self.extra_fields.get("sci:doi")
        if doi is None:
            return None

        return f'https://registry.mlhub.earth/{doi}'

    @property
    def archive_size(self) -> Optional[int]:
        """The size of the tarball archive for this collection in bytes (or ``None`` if the archive
        does not exist)."""

        # Use -1 here instead of None because None represents the case where the archive does not
        #  exist (HEAD returns a 404).
        if self._archive_size == -1:
            try:
                self._archive_size = client.get_archive_info(self.id, **self.session_kwargs).get('size')
            except EntityDoesNotExist:
                self._archive_size = None

        return self._archive_size


class CollectionType(Enum):
    """Valid values for the type of a collection associated with a Radiant MLHub dataset."""
    SOURCE = 'source_imagery'
    LABELS = 'labels'


class _CollectionWithType:
    def __init__(self, collection: Collection, types: List[str]):
        self.types = [CollectionType(type_) for type_ in types]
        self.collection = collection


class _CollectionList(Sequence):
    """Used internally by :class:`Dataset` to create a list of collections that can also be accessed by type using the
    ``source_imagery`` and ``labels`` attributes."""

    def __init__(self, collections_with_type: List[_CollectionWithType]):
        self._collections = collections_with_type

        self._source_imagery = None
        self._labels = None

    def __iter__(self):
        for item in self._collections:
            yield item.collection

    def __len__(self):
        return len(self._collections)

    def __getitem__(self, item):
        return self._collections[item].collection

    def __repr__(self):
        return list(self.__iter__()).__repr__()

    @property
    def source_imagery(self):
        if self._source_imagery is None:
            self._source_imagery = [
                c.collection
                for c in self._collections
                if any(type_ is CollectionType.SOURCE for type_ in c.types)
            ]
        return self._source_imagery

    @property
    def labels(self):
        if self._labels is None:
            self._labels = [
                c.collection
                for c in self._collections
                if any(type_ is CollectionType.LABELS for type_ in c.types)
            ]
        return self._labels


class Dataset:
    """Class that brings together multiple Radiant MLHub "collections" that are all considered part of a single "dataset". For instance,
    the ``bigearthnet_v1`` dataset is composed of both a source imagery collection (``bigearthnet_v1_source``) and a labels collection
    (``bigearthnet_v1_labels``).

    Attributes
    ----------

    id : str
        The dataset ID.
    title : str or None
        The title of the dataset (or ``None`` if dataset has no title).
    registry_url : str or None
        The URL to the registry page for this dataset, or ``None`` if no registry page exists.
    doi : str or None
        The DOI identifier for this dataset, or ``None`` if there is no DOI for this dataset.
    citation: str or None
        The citation information for this dataset, or ``None`` if there is no citation information.
    """

    def __init__(
        self,
        id: str,
        collections: List[dict],
        title: Optional[str] = None,
        registry: Optional[str] = None,
        doi: Optional[str] = None,
        citation: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        profile: Optional[str] = None,
        # Absorbs additional keyword arguments to protect against changes to dataset object from API
        # https://github.com/radiantearth/radiant-mlhub/issues/41
        **_
    ):
        self.id = id
        self.title = title
        self.collection_descriptions = collections
        self.registry_url = registry
        self.doi = doi
        self.citation = citation

        self.session_kwargs = {}
        if api_key:
            self.session_kwargs['api_key'] = api_key
        if profile:
            self.session_kwargs['profile'] = profile

        self._collections: Optional['_CollectionList'] = None

    @property
    def collections(self) -> _CollectionList:
        """List of collections associated with this dataset. The list that is returned has 2 additional attributes (``source_imagery`` and
        ``labels``) that represent the list of collections corresponding the each type.

        .. note::

            This is a cached property, so updating ``self.collection_descriptions`` after calling ``self.collections`` the first time
            will have no effect on the results. See :func:`functools.cached_property` for details on clearing the cached value.

        Examples
        --------

        >>> from radiant_mlhub import Dataset
        >>> dataset = Dataset.fetch('bigearthnet_v1')
        >>> len(dataset.collections)
        2
        >>> len(dataset.collections.source_imagery)
        1
        >>> len(dataset.collections.labels)
        1

        To loop through all collections

            >>> for collection in dataset.collections:
            ...     # Do something here

        To loop through only the source imagery collections:

            >>> for collection in dataset.collections.source_imagery:
            ...     # Do something here

        To loop through only the label collections:

            >>> for collection in dataset.collections.labels:
            ...     # Do something here
        """
        if self._collections is None:
            # Internal method to return a Collection along with it's CollectionType
            def _fetch_collection(_collection_description):
                return _CollectionWithType(
                    Collection.fetch(_collection_description['id'], **self.session_kwargs),
                    [CollectionType(type_) for type_ in _collection_description['types']]
                )

            # Fetch all collections and create Collection instances
            if len(self.collection_descriptions) == 1:
                # If there is only 1 collection, fetch it in the same thread
                only_description = self.collection_descriptions[0]
                collections = [_fetch_collection(only_description)]
            else:
                # If there are multiple collections, fetch them concurrently
                with concurrent.futures.ThreadPoolExecutor() as exc:
                    collections = list(exc.map(_fetch_collection, self.collection_descriptions))

            self._collections = _CollectionList(collections)

        return self._collections

    @classmethod
    def list(cls, **session_kwargs) -> List['Dataset']:
        """Returns a list of :class:`Dataset` instances for each datasets hosted by MLHub.

        See the :ref:`Authentication` documentation for details on how authentication is handled for this request.

        Parameters
        ----------
        **session_kwargs
            Keyword arguments passed directly to :func:`~radiant_mlhub.session.get_session`

        Yields
        ------
        dataset : Dataset
        """
        return [
            cls(**d, **session_kwargs)
            for d in client.list_datasets(**session_kwargs)
        ]

    @classmethod
    def fetch(cls, dataset_id: str, **session_kwargs) -> 'Dataset':
        """Creates a :class:`Dataset` instance by fetching the dataset with the given ID from the Radiant MLHub API.

        Parameters
        ----------
        dataset_id : str
            The ID of the dataset to fetch (e.g. ``bigearthnet_v1``).
        **session_kwargs
            Keyword arguments passed directly to :func:`~radiant_mlhub.session.get_session`.

        Returns
        -------
        dataset : Dataset
        """
        return cls(
            **client.get_dataset(dataset_id, **session_kwargs),
            **session_kwargs
        )

    def download(
            self,
            output_dir: Union[Path, str],
            *,
            if_exists: str = 'resume',
            **session_kwargs
    ) -> List[Path]:
        """Downloads archives for all collections associated with this dataset to given directory. Each archive will be named using the
        collection ID (e.g. some_collection.tar.gz). If ``output_dir`` does not exist, it will be created.

        .. note::

            Some collections may be very large and take a significant amount of time to download, depending on your connection speed.

        Parameters
        ----------
        output_dir : str or pathlib.Path
            The directory into which the archives will be written.
        if_exists : str, optional
            How to handle an existing archive at the same location. If ``"skip"``, the download will be skipped. If ``"overwrite"``,
            the existing file will be overwritten and the entire file will be re-downloaded. If ``"resume"`` (the default), the
            existing file size will be compared to the size of the download (using the ``Content-Length`` header). If the existing
            file is smaller, then only the remaining portion will be downloaded. Otherwise, the download will be skipped.
        session_kwargs
            Keyword arguments passed directly to :func:`~radiant_mlhub.session.get_session`

        Returns
        -------
        output_paths : List[pathlib.Path]
            List of paths to the downloaded archives

        Raises
        -------
        IOError
            If ``output_dir`` exists and is not a directory.
        FileExistsError
            If one of the archive files already exists in the ``output_dir`` and both ``exist_okay`` and ``overwrite`` are ``False``.
        """
        return [
            collection.download(output_dir, if_exists=if_exists, **session_kwargs)
            for collection in self.collections
        ]

    @property
    def total_archive_size(self) -> Optional[int]:
        """Gets the total size (in bytes) of the archives for all collections associated with this
        dataset. If no archives exist, returns ``None``."""
        # Since self.collections is cached on the Dataset instance, and collection.archive_size is
        # cached on each Collection, we don't bother to cache this property.
        archive_sizes = [
            collection.archive_size
            for collection in self.collections
            if collection.archive_size is not None
        ]

        return None if not archive_sizes else sum(archive_sizes)
