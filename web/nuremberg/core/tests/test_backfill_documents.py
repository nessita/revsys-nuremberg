import os
import tempfile
from functools import partial

import pytest
from django.core.management.base import CommandError

from nuremberg.core.tests import helpers
from nuremberg.documents.models import Document


pytestmark = pytest.mark.django_db

do_command_call = partial(helpers.do_command_call, 'backfill_documents')


def test_backfill_documents_no_csv_file():
    with pytest.raises(CommandError) as e:
        do_command_call()

    assert str(e.value) == 'Error: the following arguments are required: csv'


def test_backfill_documents_empty_file():
    f = tempfile.NamedTemporaryFile()

    result, stdout, stderr = do_command_call(f.name)

    assert result is None
    assert stdout.getvalue() == 'Processed 0 row(s).\n'
    assert stderr.getvalue() == ''


def test_backfill_documents_real_file():
    fname = os.path.join(os.path.dirname(__file__), 'data', 'tbldoc.txt')
    assert os.path.exists(fname), f'{fname} should be a valid file'
    previous_count = Document.objects.count()

    result, stdout, stderr = do_command_call(fname)

    assert result is None
    assert stdout.getvalue() == 'Processed 7680 row(s).\n'
    assert stderr.getvalue() == ''
    assert Document.objects.count() == previous_count  # + 7680

    # assert over some particularly difficult entries

    ## uses '"'

    # |52|	|Letter to Wolfram Sievers directing that the Ahnenerbe conduct
    # "military scientific research"|	NULL	|The letter was presented with
    # the evidence on high altitude experiments, although these are not
    # mentioned explicitly. Himmler wrote the letter; Brandt forwarded a copy
    # to Pohl.|	NULL	|2|	|1|	|1|	|9|	|1|	NULL	|1|	|7|	NULL	|20|
    # NULL	|2001-04-03 00:00:00|	NULL	NULL	NULL

    d = Document.objects.get(id=52)
    assert d.title == (
        'Letter to Wolfram Sievers directing that the Ahnenerbe conduct '
        '"military scientific research"'
    )
    assert d.literal_title is None
    # assert d.description == (
    #     'The letter was presented with the evidence on high altitude '
    #     'experiments, although these are not mentioned explicitly. Himmler '
    #     'wrote the letter; Brandt forwarded a copy to Pohl.')
    assert d.language.id == 2
    assert d.source.id == 1
    assert d.image_count == 1

    # |703|	|Excerpts from the magazines "Change" and "The Courier" containing
    # two versions of the Hippocratic oath|	|Excerpt from: Monthly Magazine
    # "Change" ("Die Wandlung") . . . The Hippocratic Oath.|	|The "Change"
    # version was published in 1946, the "Courier" version in January 1947. The
    # Courier version was used at the "Faculty of Medicine" at Paris.|
    # NULL	|2|	|1|	|1|	|9|	|1|	NULL	|3|	|9|	NULL	|19|	NULL
    # |2001-05-21 00:00:00|	NULL	NULL	NULL

    d = Document.objects.get(id=703)
    assert d.title == (
        'Excerpts from the magazines "Change" and "The Courier" containing '
        'two versions of the Hippocratic oath'
    )
    assert d.literal_title == (
        'Excerpt from: Monthly Magazine "Change" ("Die Wandlung") . . . The '
        'Hippocratic Oath.'
    )
    # assert d.description == (
    #     'The "Change" version was published in 1946, the "Courier" version '
    #     'in January 1947. The Courier version was used at the "Faculty of '
    #     'Medicine" at Paris.'
    # )
    assert d.language.id == 2
    assert d.source.id == 1
    assert d.image_count == 3

    ## weird title

    # |697|	|.|	|Affidavit|	NULL	NULL	|2|	|1|	|1|	|9|	|1|	NULL	|7|	|9
    # |	NULL	|19|	NULL	|2003-04-11 00:00:00|	NULL	NULL	NULL

    d = Document.objects.get(id=697)
    assert d.title == '.'
    assert d.literal_title == 'Affidavit'
    assert d.language.id == 2
    assert d.source.id == 1
    assert d.image_count == 7

    # |951|	|\|	|Extract from the Bulletin of the Society for Exotic Pathology . . . A disease resembling Typhus exanthematous as observed in Indo-China.|	NULL	NULL	|2|	|1|	|1|	|3|	|1|	NULL	|5|	|10|	NULL	|17|	NULL	|2004-11-02 00:00:00|	NULL	NULL	NULL
    # |1307|	|\|	|Geheimbericht.|	|The document was presented in two parts, NO 220a-b, in NMT Case 1,  220b in Case 2, and 220a in Case 4.|	NULL	|4|	|5|	|2|	|3|	|1|	NULL	|5|	|375|	NULL	NULL	NULL	|2004-12-15 00:00:00|	NULL	NULL	NULL
    # |1478|	|+|	|Betr.: SS-Hauptsturmfuehrer Stabsarzt Dr. S. Rascher|	NULL	NULL	|4|	|11|	|2|	|3|	|1|	|[typescript-German]|	|1|	|375|	NULL	NULL	NULL	|2005-01-04 00:00:00|	NULL	NULL	NULL
    # |1852|	|1853|	NULL	|This Staff Evidence Analysis was prepared by Bruno Heilig on 17 Oct 1946. One document is by Gerstner (24 Feb); one is by a Nazi group, and two are by Sellmer (one dated 27 Feb).|	NULL	|2|	|9|	|2|	|3|	|1|	|[Analysis]|	|2|	|377|	NULL	NULL	NULL	|2005-02-02 00:00:00|	NULL	NULL	NULL
    # |2582|	|\|	|Affidavit|	NULL	NULL	|2|	|10|	|2|	|3|	|1|	|[Typescript-English]|	|10|	|297|	NULL	NULL	NULL	|2004-12-15 00:00:00|	NULL	NULL	NULL
    # |3109|	|+|	NULL	|This copy of the affidavit is not dated; another copy supplies the date 30 Aug 1946. The legibility of the document is uneven.|	NULL	|2|	|1|	|1|	|3|	|1|	NULL	|3|	|13|	NULL	|15|	NULL	|2016-05-20 00:00:00|	NULL	NULL	NULL

    # line feed inside a field
    # |3619|	|Minutes of a Jaegerstab meeting, concerning labor requirements and the conscription of foreign workers|	|Stenographischer Bericht ueber die Jaegerstab - Besprechung . . . 28.3.1944 . . .|	|Pages 43-44 are missing.|	NULL	|4|	|5|	|2|	|3|	|1|	|
    # Photostat|	|57|	|395|	NULL	NULL	NULL	|2001-01-24 00:00:00|	|0|	NULL	NULL
    # |150006|	|Prosecution closing argument in Case 7, on the various crimes charged and the defendants individually|	|Closing Statement on behalf of the prosecution|	|The title-page says that the three authors delivered the argument for Telford Taylor, the chief of counsel. The pagination is irregular and incomplete. The text begins on page 3. There is a gap after page 98, with most but not all of the missing text replaced by fifty-seven pages numbered alphanumerically in 4 groups (1-a to 16-a, 1B to 17B, 1-c to 11-c, and 1-d to 13-D), followed by pages 156-162. Several pages of text are missing, others are damaged, and and legibility is poor. The transcript version is easier to read.|	NULL	|2|	|1|	|1|	NULL	NULL	NULL	|161|	|HL571EM|	NULL	|4|	NULL	|2016-06-28 00:00:00|	NULL	|VF: in the images folder, the t.p. is followed by pages 1a-2d, and then other alpha-numeric pages (a,b,c,d) interspersed with the regular pages. Main text begins p. 3. Move the alphanumeric pages (1-a to 13D (only)) to follow p. 98, before p. 156. The pages are grouped according to the letters. The sequence should be as follows:
    # title-page, p.3-98,
    # 1a - 16a,
    # 1B - 17B,
    # 1c - 11c,
    # 1d - 13D,
    # 156-162.|	NULL
