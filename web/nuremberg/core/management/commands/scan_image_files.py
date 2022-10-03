import os
import re
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, SEEK_CUR
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count, F

from nuremberg.documents.models import (
    Document,
    DocumentImage,
    DocumentImageType,
)


class Command(BaseCommand):
    help = 'Populates the DocumentImage metadata for any missing images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ids',
            nargs='+',
            type=int,
            default=None,
            help='Document ids to scan for missing images (default is all documents)',
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=10,
            help='Amount of concurrent workers, defaults to 10',
        )
        parser.add_argument(
            '--download',
            action='store_true',
            help='Download the image to local storage',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-populate the image even if already stored in the model',
        )

    def handle(self, *args, **options):
        documents = Document.objects
        if options['ids']:
            documents = documents.filter(id__in=options['ids'])
        else:
            documents = documents.all()

        if not options['force']:
            documents = documents.annotate(
                real_image_count=Count('images')
            ).filter(real_image_count__lt=F('image_count'))

        if not documents:
            self.stderr.write('No documents to be processed')
            return

        if options['download']:
            download_to = settings.MEDIA_ROOT
            self.stdout.write(f'Downloading images to {download_to}')
        else:
            download_to = None

        workers = options['workers']
        if workers == 1:
            for document in documents:
                populate_document(document, download_to, workers)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for document in documents:
                    pool.submit(
                        populate_document, document, download_to, workers
                    )


def populate_document(document, download_to, workers):
    print("Populating document", document.id, document.image_count)
    if workers == 1:
        for page_number in range(1, document.image_count + 1):
            populate_metadata(document, page_number, download_to)
    else:
        with ThreadPoolExecutor(max_workers=10) as pool:
            for page_number in range(1, document.image_count + 1):
                pool.submit(
                    populate_metadata, document, page_number, download_to
                )
    print("Populated", document.id, document.image_count)


def populate_metadata(document, page_number, download_to):
    print("Populating metadata", document.id, page_number)
    image, created = DocumentImage.objects.get_or_create(
        document=document, page_number=page_number
    )
    filename = "{:05d}{:03d}".format(document.id, page_number)
    jpgname = f'HLSL_NUR_{filename}.jpg'
    save = False

    if created:
        print(
            "Instance created, populating from the old image model",
            document.id,
            page_number,
            filename,
        )
        # Legacy process to populate the DocumentImage model

        old_image = document.old_images.filter(filename=filename).first()

        if old_image:
            if old_image.physical_page_number:
                physical_page_number = re.sub(
                    r'[^\d]', '', old_image.physical_page_number
                )
                if physical_page_number:
                    image.physical_page_number = int(physical_page_number)
            image.image_type = old_image.image_type
        else:
            image.image_type = DocumentImageType.objects.get(id=4)

        image.url = (
            f"http://nuremberg.law.harvard.edu/imagedir/HLSL_NMT01/{jpgname}"
        )
        (image.width, image.height) = get_jpeg_size(image.url)
        image.scale = DocumentImage.SCREEN
        if not (image.width and image.height):
            image.url = None
        save = True

    # populate new ImageField if needed
    try:
        current = image.image.url
    except ValueError:
        current = None
    media_path = os.path.join(settings.DOCUMENTS_BUCKET, jpgname)
    if current != urljoin(settings.MEDIA_URL, media_path):
        print(
            f'Setting image url to {media_path} for document {document.id} '
            f'page {page_number} (previously had {current})'
        )
        image.image = media_path
        save = True

    if save:
        image.save()

    if download_to:
        url = f'http://s3.amazonaws.com/{media_path}'
        print(f'Donwloading image at {url}')
        if url:
            response = requests.get(url)
            print('Response is:', response)
            if not response.ok:
                print(
                    'Can not download image, response code is:',
                    response.status_code,
                )
            else:
                with open(os.path.join(download_to, media_path), 'wb') as f:
                    f.write(response.content)


def get_jpeg_size(url, header_length=5000):
    header = requests.get(
        url, headers={'Range': 'bytes=0-{}'.format(header_length)}
    )

    data = BytesIO(header.content)

    if data.read(2) != b'\xFF\xD8':
        print("not a valid JPEG file ", url, header.content)
        return (None, None)

    # scan the JFIF header for the SOF0 block with image dimensions in it
    while True:
        block_header = data.read(2)
        block_size = int.from_bytes(data.read(2), byteorder="big")
        if block_header == b'\xFF\xc0':  # found SOF0
            break
        if block_header == b'':
            if header_length and header_length < 50000:
                return get_jpeg_size(url, header_length + 25000)
            elif header_length:
                return get_jpeg_size(url, '')

            print(
                "ran out of bytes in JPEG header",
                url,
                "after",
                len(header.content),
            )
            raise Exception("out of bytes")
        data.seek(block_size - 2, SEEK_CUR)  # size includes size bytes

    data.read(1)

    height = int.from_bytes(data.read(2), byteorder="big")
    width = int.from_bytes(data.read(2), byteorder="big")
    return (width, height)
