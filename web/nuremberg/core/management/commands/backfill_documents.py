import argparse
import csv

from django.core.management.base import BaseCommand

from nuremberg.documents.models import Document


class Command(BaseCommand):
    help = "Backfill Document instances using CSV taken from original source"

    def add_arguments(self, parser):
        parser.add_argument(
            dest='csv',
            type=argparse.FileType('r'),
            help='CSV file containing the `tblDoc` rows to parse and store',
        )
        parser.add_argument(
            '--ids',
            nargs='+',
            type=int,
            default=None,
            help='Document IDs to process (default is all)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-populate the values even if already set in the instance',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help=(
                'Show how many instances would be back filled but make no '
                'actual changes'
            ),
        )

    def prepare_model_data(self, row):
        result = {}
        # XXX: ToDo
        result.update(row)
        return result

    def backfill(self, csvfile, qs, dry_run=False, force=False):
        data = {}
        # assumes a csv file generated with mysqldump with flags:
        # --fields-enclosed-by='|' --fields-escaped-by=
        reader = csv.DictReader(
            csvfile,
            fieldnames=list(Document.FIELDNAMES_MAPPING.keys()),
            delimiter='\t',
            quotechar='|',
            escapechar='',
        )

        previous = None
        for row in reader:
            try:
                doc_id = int(row['DocID'])
            except ValueError:
                print('\n\n\nINFO, PREVIOUS row follows:', previous)
                print('\n\n\nERROR, CURRENT row follows:', row)
                raise
            model_data = self.prepare_model_data(row)
            data[doc_id] = model_data
            previous = row

        return data

    def handle(self, *args, **options):
        csvfile = options['csv']

        qs = Document.objects.all()
        if options['ids']:
            qs = qs.filter(id__in=options['ids'])

        data = self.backfill(
            csvfile,
            qs=qs,
            dry_run=options['dry_run'],
            force=options['force'],
        )
        self.stdout.write('Processed %s row(s).' % len(data))
