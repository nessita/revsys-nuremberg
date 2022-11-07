import datetime

import pytest
from model_bakery import baker

from nuremberg.documents.models import (
    Document,
    DocumentDate,
    DocumentPersonalAuthor,
    DocumentText,
    PersonalAuthorProperty,
)
from .helpers import make_author


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('day', [None, 0, 33, -1])
@pytest.mark.parametrize('month', [None, 0, 13, -1])
@pytest.mark.parametrize('year', [None, 0, -1])
def test_document_date_invalid_date_params(day, month, year):
    d = DocumentDate.objects.create(day=day, month=month, year=year)
    assert d.as_date() is None


@pytest.mark.parametrize('year, month, day', [(2022, 2, 29), (2022, 4, 31)])
def test_document_date_invalid_date(day, month, year):
    d = DocumentDate.objects.create(day=day, month=month, year=year)
    assert d.as_date() is None


@pytest.mark.parametrize('day', [1, 30])
@pytest.mark.parametrize('month', [1, 12])
@pytest.mark.parametrize('year', [1, 1000, 2050])
def test_document_date_valid_as_date(day, month, year):
    d = DocumentDate.objects.create(day=day, month=month, year=year)
    assert d.as_date() == datetime.date(year, month, day)


def test_document_retrieve_full_text_empty():
    doc = baker.make('Document')

    assert doc.full_texts().count() == 0


def test_document_retrieve_full_text_no_evidence_code_match():
    baker.make(
        'DocumentText', evidence_code_series='FF', evidence_code_num='123'
    )
    evidence_codes = [
        baker.make('DocumentEvidenceCode', prefix__code='Z', number='123'),
        baker.make('DocumentEvidenceCode', prefix__code='FF', number='12'),
    ]
    doc = baker.make('Document', evidence_codes=evidence_codes)
    assert sorted(str(e) for e in doc.evidence_codes.all()) == [
        'FF-12',
        'Z-123',
    ]

    assert doc.full_texts().count() == 0


def test_document_retrieve_full_text_real():
    for doc_id in [30, 3058, 2539]:
        doc = Document.objects.get(id=doc_id)

        result = doc.full_texts()

        assert result.count() == 1
        result = result.get()
        assert isinstance(result, DocumentText)
        assert result.id == 729


def test_author_slug_full_name():
    author = make_author(
        first_name='First Name: So Many #$ different Characters! ♡',
        last_name=' Last ↦ Name',
        title='Some Title',
    )

    assert author.slug == 'first-name-so-many-different-characters-last-name'


def test_author_slug_no_first_name():
    author = make_author(
        first_name='',
        last_name='Only Last Name',
        title='Some Title',
    )

    assert author.slug == 'only-last-name'


def test_author_slug_no_last_name():
    author = make_author(
        first_name='Only First Name',
        last_name='',
        title='Some Title',
    )

    assert author.slug == 'only-first-name'


def test_author_properties_no_author():
    last_id = DocumentPersonalAuthor.objects.all().order_by('id').last().id
    empty_qs = DocumentPersonalAuthor.objects.filter(id=last_id + 1)

    assert empty_qs.count() == 0
    assert empty_qs.metadata() == []


def test_author_properties_no_property_match_uses_title():
    author = make_author(
        first_name='No',
        last_name='Properties',
        title='Some Title',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = author.metadata()

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': '',
        },
        'image': None,
        'properties': [],
    }


def test_author_properties_uses_title_even_if_empty_first_name():
    author = make_author(
        first_name='Does Not Exist',
        last_name=None,
        title='Some Title',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = author.metadata()

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': '',
        },
        'image': None,
        'properties': [],
    }


def test_author_properties_uses_title_even_if_empty_last_name():
    author = make_author(
        first_name=None,
        last_name='Does Not Exist',
        title='Some Title',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = author.metadata()

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': '',
        },
        'image': None,
        'properties': [],
    }


def test_author_properties_no_property_match_empty_title():
    author = make_author(
        first_name='Does Not',
        last_name='Exist',
        title='',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = author.metadata()

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': '',
        },
        'image': None,
        'properties': [],
    }


def test_author_properties_uses_property_ranks():
    author = make_author(first_name='Some', last_name='Name')

    rank0 = baker.make(
        'PersonalAuthorPropertyRank', name='ignore due to rank 0', rank=0
    )
    prop0 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank0.name,
        value='Ignored 0',
    )
    assert prop0.rank == 0

    rank_negative_1 = baker.make(
        'PersonalAuthorPropertyRank', name='ignore due to rank -1', rank=-1
    )
    prop_1 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_negative_1.name,
        value='Ignored -1',
    )
    assert prop_1.rank == -1

    prop_none = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name='no rank available',
        value='Ignored None',
    )
    assert prop_none.rank is None

    rank_1 = baker.make('PersonalAuthorPropertyRank', name='valid 1', rank=1)
    prop_1_1 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_1.name,
        value='one value',
        qualifier='',
        qualifier_value='',
    )
    assert prop_1_1.rank == 1
    prop_1_2 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_1.name,
        value='another',
        qualifier='',
        qualifier_value='',
    )
    assert prop_1_2.rank == 1

    rank_5 = baker.make('PersonalAuthorPropertyRank', name='valid 5', rank=5)
    prop_5 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_5.name,
        value='different value, could be a link',
        qualifier='',
        qualifier_value='',
    )
    assert prop_5.rank == 5

    result = author.metadata()

    # order is given by higher rank first, then value
    expected = [
        {
            'rank': 5,
            'name': 'valid 5',
            'prop_values': [{'value': prop_5.value, 'qualifiers': []}],
        },
        {
            'rank': 1,
            'name': 'valid 1',
            'prop_values': [
                {'value': 'another', 'qualifiers': []},
                {'value': 'one value', 'qualifiers': []},
            ],
        },
    ]
    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': prop_1_1.personal_author_description,
        },
        'image': None,
        'properties': expected,
    }


def test_author_properties_groups_qualifiers(django_assert_num_queries):
    author = make_author()

    rank = baker.make('PersonalAuthorPropertyRank', name='a property', rank=10)
    first = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='country',
        qualifier_value='US',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='country',
        qualifier_value='CA',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='another value',  # should not group with previous qualifier
        qualifier='country',
        qualifier_value='ES',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='county',  # different spelling but same qualifier
        qualifier_value='Village',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='subject has role',  # should be replaced by 'role'
        qualifier_value='role 1',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='object has role',  # should be replaced by 'role'
        qualifier_value='role 2',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='role',
        qualifier_value='other role',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='valid in place',  # should be ignored
        qualifier_value='ignored',
    )

    with django_assert_num_queries(2):  # fetch ranks and properties
        result = author.metadata()

    # order is given by higher rank first, then value
    expected = [
        {
            'rank': 10,
            'name': 'a property',
            'prop_values': [
                {
                    'value': 'another value',
                    'qualifiers': [('country', ['ES'])],
                },
                {
                    'value': 'some value',
                    'qualifiers': [
                        ('country', ['CA', 'US']),
                        ('county', ['Village']),
                        ('role', ['other role', 'role 1', 'role 2']),
                    ],
                },
            ],
        },
    ]
    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': first.personal_author_description,
        },
        'image': None,
        'properties': expected,
    }


def test_author_properties_extracts_image():
    author = make_author(
        first_name='Some Other',
        last_name='Name',
        title='Sir Someone',
    )

    rank_image = baker.make(
        'PersonalAuthorPropertyRank', name='image', rank=30
    )
    prop_image_1 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_image.name,
        value='https://link-to-image-1.jpg',
        qualifier='',
        qualifier_value='',
    )
    assert prop_image_1.rank == 30
    prop_image_2 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_image.name,
        value='https://link-to-image-2.jpg',
        qualifier='',
        qualifier_value='',
    )
    assert prop_image_2.rank == 30

    result = author.metadata()

    # Default alt if no 'media legend' qualifier is present
    image = {
        'url': prop_image_1.value,
        'alt': f'Image of {author.full_name()}',
    }
    author_data = {
        'name': author.full_name(),
        'id': author.id,
        'slug': author.slug,
        'title': author.title,
        'description': prop_image_1.personal_author_description,
    }
    assert result == {
        'author': author_data,
        'image': image,
        'properties': [],
    }

    # now define 'media legend' for the second image, it will not be used
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_image.name,
        value='https://link-to-image-2.jpg',
        qualifier='media legend',
        qualifier_value='The Legend for Image 2',
    )

    result = author.metadata()
    assert result == {
        'author': author_data,
        'image': image,
        'properties': [],
    }

    # now define 'media legend' for the first image, it should be picked up
    legend = 'The Legend for Image 1'
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_image.name,
        value='https://link-to-image-1.jpg',
        qualifier='media legend',
        qualifier_value=legend,
    )

    result = author.metadata()

    image['alt'] = legend
    assert result == {
        'author': author_data,
        'image': image,
        'properties': [],
    }


def test_author_properties_groups_birth_data():
    author = make_author()

    rank_place_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='place of birth', rank=24
    )
    rank_date_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='date of birth', rank=23
    )
    prop_place_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
        qualifier='',
        qualifier_value='',
    )
    prop_date_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='',
        qualifier_value='',
    )

    result = author.metadata()

    born = f'{prop_date_of_birth.value} ({prop_place_of_birth.value})'
    properties = [
        {
            'rank': 24,
            'name': 'born',
            'prop_values': [{'value': born, 'qualifiers': []}],
        }
    ]
    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': prop_place_of_birth.personal_author_description,
        },
        'image': None,
        'properties': properties,
    }


def test_author_properties_groups_death_data():
    author = make_author()

    rank_place_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='place of death', rank=24
    )
    rank_date_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='date of death', rank=23
    )
    prop_place_of_death = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_death.name,
        value='A city or location',
        qualifier='',
        qualifier_value='',
    )
    prop_date_of_death = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_death.name,
        value='1979-01-01',
        qualifier='',
        qualifier_value='',
    )

    result = author.metadata()

    died = f'{prop_date_of_death.value} ({prop_place_of_death.value})'
    properties = [
        {
            'rank': 24,
            'name': 'died',
            'prop_values': [{'value': died, 'qualifiers': []}],
        }
    ]
    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': prop_place_of_death.personal_author_description,
        },
        'image': None,
        'properties': properties,
    }


def test_author_properties_name_data_ignored():
    author = make_author(
        first_name='John',
        last_name='Doe',
    )
    rank_family_name = baker.make(
        'PersonalAuthorPropertyRank', name='family name', rank=28
    )
    rank_given_name = baker.make(
        'PersonalAuthorPropertyRank', name='given name', rank=27
    )
    rank_birth_name = baker.make(
        'PersonalAuthorPropertyRank', name='birth name', rank=26
    )
    first = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_family_name.name,
        value='Family Name',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_given_name.name,
        value='Given Name',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_birth_name.name,
        value='Birth Name',
    )

    result = author.metadata()

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': first.personal_author_description,
        },
        'image': None,
        'properties': [],
    }


def test_author_properties_dates_and_qualifiers():
    author = make_author()

    rank_place_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='place of birth', rank=26
    )
    rank_date_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='date of birth', rank=25
    )
    rank_place_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='place of death', rank=24
    )
    rank_date_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='date of death', rank=23
    )

    prop_place_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
        qualifier='country',
        qualifier_value='DE',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
        qualifier='country',
        qualifier_value='Austria-Hungary',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
        qualifier='stress address',
        qualifier_value='Some Address',
    )

    prop_date_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='country',
        qualifier_value='Bulgaria',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='child of',
        qualifier_value='Parent Name 1',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='child of',
        qualifier_value='Parent Name 2',
    )

    prop_place_of_death = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_death.name,
        value='Another city',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_death.name,
        value='Another city',
        qualifier='country',
        qualifier_value='Nazi Germany',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_death.name,
        value='Another city',
        qualifier='located in the administrative territorial entity',
        qualifier_value='Berlin',
    )

    prop_date_of_death = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_death.name,
        value='1999-01-01',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_death.name,
        value='1999-01-01',
        qualifier='cause',
        qualifier_value='poisoning',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_death.name,
        value='1999-01-01',
        qualifier='something',
        qualifier_value='one value',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_death.name,
        value='1999-01-01',
        qualifier='something',
        qualifier_value='another value',
    )

    result = author.metadata()

    born = f'{prop_date_of_birth.value} ({prop_place_of_birth.value})'
    died = f'{prop_date_of_death.value} ({prop_place_of_death.value})'
    properties = [
        {
            'rank': 26,
            'name': 'born',
            'prop_values': [
                {
                    'value': born,
                    'qualifiers': [
                        ('child of', ['Parent Name 1', 'Parent Name 2']),
                        ('country', ['Austria-Hungary', 'Bulgaria', 'DE']),
                        ('stress address', ['Some Address']),
                    ],
                }
            ],
        },
        {
            'rank': 24,
            'name': 'died',
            'prop_values': [
                {
                    'value': died,
                    'qualifiers': [
                        ('cause', ['poisoning']),
                        ('country', ['Nazi Germany']),
                        (
                            'located in the administrative territorial entity',
                            ['Berlin'],
                        ),
                        ('something', ['another value', 'one value']),
                    ],
                }
            ],
        },
    ]
    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': prop_place_of_birth.personal_author_description,
        },
        'image': None,
        'properties': properties,
    }


def test_document_text_retrieve_documents_empty():
    doc_text = baker.make(
        'DocumentText', evidence_code_series='FF', evidence_code_num='123'
    )
    assert doc_text.documents().count() == 0


def test_document_text_retrieve_documents_no_evidence_code_match():
    doc_text = baker.make(
        'DocumentText', evidence_code_series='FF', evidence_code_num='123'
    )
    evidence_codes = [
        baker.make('DocumentEvidenceCode', prefix__code='Z', number='123'),
        baker.make('DocumentEvidenceCode', prefix__code='FF', number='12'),
    ]
    doc = baker.make('Document', evidence_codes=evidence_codes)
    assert sorted(str(e) for e in doc.evidence_codes.all()) == [
        'FF-12',
        'Z-123',
    ]
    assert doc_text.documents().count() == 0


@pytest.mark.skip(reason='Need to sort out object persistence with bakery')
def test_document_text_retrieve_documents_simple():
    doc_text = baker.make(
        'DocumentText',
        evidence_code_series='FF',
        evidence_code_num='123',
        evidence_code_tag='Not relevant',
    )
    evidence_codes = [
        baker.make('DocumentEvidenceCode', prefix__code='Z', number='123'),
        baker.make('DocumentEvidenceCode', prefix__code='FF', number='123'),
    ]
    doc = baker.make(Document, evidence_codes=evidence_codes)

    # We may have an issue with the fact that tests are using the real DB.
    # The following assert passes OK
    assert [e.document.id for e in evidence_codes] == [doc.id, doc.id]
    assert sorted(str(e) for e in doc.evidence_codes.all()) == [
        'FF-123',
        'Z-123',
    ]
    # but the following fails!
    assert Document.objects.filter(id=doc.id).count() == 1

    result = doc_text.documents()

    assert result.count() == 1
    assert result.get() == doc


def test_document_text_retrieve_documents_real():
    doc_text_729 = DocumentText.objects.get(id=729)

    result = doc_text_729.documents()

    assert result.count() == 3
    # Document 2539 has no exhibit code, the other two have 1 exhibit each.
    # But document 30 was used in trial NMT 1 while document 3058 in NMT 2
    assert [d.id for d in result] == [30, 3058, 2539]
