Collections
===========

A **collection** represents either a group of related labels or a group of related source imagery for a given time period and geographic
area. All collections in the Radiant MLHub API are valid `STAC Collections <https://github.com/radiantearth/stac-spec/tree/master/collection-spec>`_.
For instance, the ``ref_landcovernet_v1_source`` collection catalogs the source imagery associated with the LandCoverNet dataset, while
the ``ref_landcovernet_v1_labels`` collection catalogs the land cover labels associated with this imagery. These collections are considered
part of a single ``ref_landcovernet_v1`` **dataset** (see the :ref:`Datasets` documentation for details on working with datasets).

To discover and fetch collections you can either use the low-level client methods from :mod:`radiant_mlhub.client` or the
:class:`~radiant_mlhub.models.Collection` class. Using the :class:`~radiant_mlhub.models.Collection` class is the recommended approach, but
both methods are described below.

Discovering Collections
+++++++++++++++++++++++

The Radiant MLHub ``/collections`` endpoint returns a list of objects describing the available collections. You can use the low-level
:func:`~radiant_mlhub.client.list_collections` function to work with these responses as native Python data types (:class:`list`
and :class:`dict`). This function returns a list of JSON-like dictionaries representing STAC Collections.

.. code-block:: python

    >>> from radiant_mlhub.client import list_collections
    >>> from pprint import pprint
    >>> collections = list_collections()
    >>> first_collection = collections[0]
    >>> pprint(first_collection)
    {'description': 'African Crops Kenya',
     'extent': {'spatial': {'bbox': [[34.18191992149459,
                                      0.4724181558451209,
                                      34.3714943155646,
                                      0.7144217206851109]]},
                'temporal': {'interval': [['2018-04-10T00:00:00Z',
                                           '2020-03-13T00:00:00Z']]}},
     'id': 'ref_african_crops_kenya_01_labels',
     'keywords': [],
     'license': 'CC-BY-SA-4.0',
     'links': [{'href': 'https://api.radiant.earth/mlhub/v1/collections/ref_african_crops_kenya_01_labels',
                'rel': 'self',
                'title': None,
                'type': 'application/json'},
               {'href': 'https://api.radiant.earth/mlhub/v1',
                'rel': 'root',
                'title': None,
                'type': 'application/json'}],
     'properties': {},
     'providers': [{'description': None,
                    'name': 'Radiant Earth Foundation',
                    'roles': ['licensor', 'host', 'processor'],
                    'url': 'https://radiant.earth'}],
     'sci:citation': 'PlantVillage. (2019) PlantVillage Kenya Ground Reference '
                     'Crop Type Dataset, Version 1. [Indicate subset used]. '
                     'Radiant ML Hub. [Date Accessed]',
     'sci:doi': '10.34911/rdnt.u41j87',
     'stac_extensions': [],
     'stac_version': '1.0.0-beta.2',
     'summaries': {},
     'title': None}

You can also discover collections using the :meth:`Collection.list <radiant_mlhub.models.Collection.list>` method. This is the recommended way of
listing datasets. This method returns a list of :class:`Collection <radiant_mlhub.models.Collection>` instances.

.. code-block:: python

    >>> from radiant_mlhub import Collection
    >>> collections = Collection.list()
    >>> first_collection = collections[0]
    >>> first_collection.ref_african_crops_kenya_01_labels
    'ref_african_crops_kenya_01_labels'
    >>> first_collection.description
    'African Crops Kenya'

Fetching a Collection
+++++++++++++++++++++

The Radiant MLHub ``/collections/{p1}`` endpoint returns an object representing a single collection. You can use the low-level
:func:`~radiant_mlhub.client.get_collection` function to work with this response as a :class:`dict`.

.. code-block:: python

    >>> from radiant_mlhub.client import get_collection
    >>> collection = get_collection('ref_african_crops_kenya_01_labels')
    >>> pprint(collection)
    {'description': 'African Crops Kenya',
     'extent': {'spatial': {'bbox': [[34.18191992149459,
                                      0.4724181558451209,
                                      34.3714943155646,
                                      0.7144217206851109]]},
                'temporal': {'interval': [['2018-04-10T00:00:00Z',
                                           '2020-03-13T00:00:00Z']]}},
     'id': 'ref_african_crops_kenya_01_labels',
     ...
     }

You can also fetch a collection from the Radiant MLHub API based on the collection ID using the :meth:`Collection.fetch <radiant_mlhub.models.Collection.fetch>`
method. This is the recommended way of fetching a collection. This method returns a :class:`~radiant_mlhub.models.Collection` instance.

.. code-block:: python

    >>> collection = Collection.fetch('ref_african_crops_kenya_01_labels')
    >>> collection.id
    'ref_african_crops_kenya_01_labels'
    >>> collection.description
    'African Crops Kenya'

For more information on a Collection, you can check out the MLHub Registry page:

.. code-block:: python

    >>> collection.registry_url
    https://registry.mlhub.earth/10.14279/depositonce-10149/

Downloading a Collection
++++++++++++++++++++++++

The Radiant MLHub ``/archive/{archive_id}`` endpoint allows you to download an archive of all assets associated with a given collection. You
can use the low-level :func:`~radiant_mlhub.client.download_archive` function to download the archive to your local file system.

.. code-block:: python

    >>> from radiant_mlhub.client import download_archive
    >>> archive_path = download_archive('sn1_AOI_1_RIO')
    28%|██▊       | 985.0/3496.9 [00:35<00:51, 48.31M/s]
    >>> archive_path
    PosixPath('/path/to/current/directory/sn1_AOI_1_RIO.tar.gz')

You can also download a collection archive using the :meth:`Collection.download <radiant_mlhub.models.Collection.download>`
method. This is the recommended way of downloading an archive.

.. code-block:: python

    >>> collection = Collection.fetch('sn1_AOI_1_RIO')
    >>> archive_path = collection.download('~/Downloads', exist_okay=False)  # Will raise exception if the file already exists
    28%|██▊       | 985.0/3496.9 [00:35<00:51, 48.31M/s]
    >>> archive_path
    PosixPath('/Users/someuser/Downloads/sn1_AOI_1_RIO.tar.gz')

If a file of the same name already exists, these methods will check whether the downloaded file is complete by comparing its size against the size of the remote
file. If they are the same size, the download is skipped, otherwise the download will be resumed from the point where it stopped. You can control
this behavior using the ``if_exists`` argument. Setting this to ``"skip"`` will skip the download for existing files *without* checking for
completeness (a bit faster since it doesn't require a network request), and setting this to ``"overwrite"`` will overwrite any existing file.

To check the size of the download archive without actually downloading it, you can use the 
:attr:`Collection.total_archive_size` property.

.. code-block:: python

    >>> collection.archive_size
    3504256089

Collection archives are gzipped tarballs. You can read more about the structure of these archives in `this Medium post
<https://medium.com/radiant-earth-insights/archived-training-dataset-downloads-now-available-on-radiant-mlhub-7eb67daf094e>`_.
