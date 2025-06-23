import xml.etree.ElementTree as ET
import requests
import yaml
from ciso8601 import parse_datetime
from django.conf import settings
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from vosa.models import Licence
from ...models import DataSource, Operator, OperatorCode


def get_region_id(region_id):
    if region_id in {"ADMIN", "Admin", "Taxi", ""}:
        return "GB"
    elif region_id.upper() in {"SC", "YO", "WA", "LO"}:
        return region_id[0]
    return region_id


def get_mode(mode):
    if not mode.isupper():
        mode = mode.lower()
    match mode:
        case "ct operator" | "ct operaor" | "CT":
            return "community transport"
        case "DRT":
            return "demand responsive transport"
        case "partly drt":
            return "partly DRT"
    return mode


def get_operator_codes(
    code_sources: tuple[tuple[str, DataSource]], noc, operator, noc_line
):
    # "National Operator Codes"
    operator_codes = [
        OperatorCode(source=code_sources[0][1], code=noc, operator=operator)
    ]

    # "L", "SW", "WM" etc
    for col, source in code_sources[1:]:
        code = noc_line.find(col)
        if code is not None and code.text:
            code_text = code.text.removeprefix("=")
            if code_text != noc:
                operator_codes.append(
                    OperatorCode(
                        source=source,
                        code=code_text,
                        operator=operator,
                    )
                )
    return operator_codes


def get_operator_licences(operator, noc_line, licences_by_number):
    licence_number = noc_line.findtext("Licence")
    if licence_number in licences_by_number:
        return [
            Operator.licences.through(
                operator=operator,
                licence=licences_by_number[licence_number],
            )
        ]
    return []


class Command(BaseCommand):
    @transaction.atomic()
    def handle(self, **kwargs):
        # DataSources for codes
        code_sources = [
            (col, DataSource.objects.get_or_create(name=name)[0])
            for col, name in (
                ("NOCCODE", "National Operator Codes"),
                ("LO", "L"),
                ("SW", "SW"),
                ("WM", "WM"),
                ("WA", "W"),
                ("YO", "Y"),
                ("NW", "NW"),
                ("NE", "NE"),
                ("SC", "S"),
                ("SE", "SE"),
                ("EA", "EA"),
                ("EM", "EM"),
            )
        ]
        noc_source = code_sources[0][1]

        url = "https://www.travelinedata.org.uk/noc/api/1.0/nocrecords.xml"
        response = requests.get(url)
        element = ET.fromstring(response.text)

        generation_date = parse_datetime(element.attrib["generationDate"])
        if generation_date == noc_source.datetime:
            return

        noc_source.datetime = generation_date
        noc_source.save(update_fields=["datetime"])  # inside transaction, safe

        # Fetch existing operators keyed by noc
        operators = Operator.objects.prefetch_related(
            "operatorcode_set", "licences"
        ).in_bulk(field_name="noc")

        # Existing operator codes keyed by code for the NOC source
        merged_operator_codes = {
            code.code: code
            for operator in operators.values()
            for code in operator.operatorcode_set.all()
            if code.source_id == noc_source.id and code.code != operator.noc
        }

        licences_by_number = Licence.objects.in_bulk(field_name="licence_number")

        with open(settings.BASE_DIR / "fixtures" / "operators.yaml") as open_file:
            overrides = yaml.safe_load(open_file)

        operators_by_slug = {operator.slug: operator for operator in operators.values()}

        public_names = {}
        for e in element.find("PublicName"):
            e_id = e.findtext("PubNmId")
            assert e_id not in public_names
            public_names[e_id] = e

        noc_lines = {
            line.findtext("NOCCODE").removeprefix("="): line
            for line in element.find("NOCLines")
        }

        to_create = []
        to_update = []
        operator_codes = []
        operator_licences = []

        for e in element.find("NOCTable"):
            noc = e.findtext("NOCCODE").removeprefix("=")

            noc_line = noc_lines.get(noc)
            if noc_line is None:
                continue

            # Skip if another operator already has that code as an alias
            if noc in merged_operator_codes:
                continue

            vehicle_mode = get_mode(noc_line.findtext("Mode") or "")
            if vehicle_mode == "airline":
                continue

            public_name = public_names.get(e.findtext("PubNmId"))
            if public_name is None:
                continue

            name = public_name.findtext("OperatorPublicName") or ""

            url = public_name.findtext("Website") or ""
            if url:
                url = url.removesuffix("#")
                url = url.split("#")[-1]

            twitter = public_name.findtext("Twitter") or ""
            twitter = twitter.removeprefix("@")

            # Apply overrides
            if noc in overrides:
                override = overrides[noc]

                if "url" in override:
                    url = override["url"]

                if "twitter" in override:
                    twitter = override["twitter"]

                if "name" in override:
                    if override["name"] == name:
                        print(name)
                    name = override["name"]

            if noc not in operators:
                # New operator
                operator = Operator(
                    noc=noc,
                    name=name,
                    region_id=get_region_id(noc_line.findtext("TLRegOwn") or ""),
                    vehicle_mode=vehicle_mode,
                    url=url,
                    twitter=twitter,
                )

                slug = slugify(operator.name)
                if slug in operators_by_slug:
                    # Duplicate name – save now to avoid slug collision
                    operator.save(force_insert=True)
                    to_update.append(operator)
                else:
                    operator.slug = slug
                    to_create.append(operator)

                operators_by_slug[operator.slug or slug] = operator
                operators[noc] = operator  # add to operators dict

                # Add operator codes and licences
                operator_codes += get_operator_codes(
                    code_sources, noc, operator, noc_line
                )
                operator_licences += get_operator_licences(
                    operator, noc_line, licences_by_number
                )

            else:
                # Existing operator
                operator = operators[noc]

                # If the existing operator does NOT already have the main NOC code attached,
                # add it (i.e. create OperatorCode)
                has_main_noc_code = any(
                    oc.source_id == noc_source.id and oc.code == noc
                    for oc in operator.operatorcode_set.all()
                )
                if not has_main_noc_code:
                    operator_codes.append(
                        OperatorCode(source=noc_source, code=noc, operator=operator)
                    )

                # Update operator if needed
                if (
                    name != operator.name
                    or url != operator.url
                    or twitter != operator.twitter
                    or vehicle_mode != operator.vehicle_mode
                ):
                    operator.name = name
                    operator.url = url
                    operator.twitter = twitter
                    operator.vehicle_mode = vehicle_mode
                    to_update.append(operator)

                # Add licences if none attached yet
                if not operator.licences.exists():
                    operator_licences += get_operator_licences(
                        operator, noc_line, licences_by_number
                    )

            # Validate operator fields except noc, slug, region
            try:
                operator.clean_fields(exclude=["noc", "slug", "region"])
            except Exception as e:
                if hasattr(e, "message_dict") and "url" in e.message_dict:
                    operator.url = ""
                else:
                    print(f"Error cleaning fields for NOC {noc}: {e}")

        # Bulk create and update operators
        Operator.objects.bulk_create(
            to_create,
            update_fields=(
                "url",
                "name",
                "vehicle_mode",
                "slug",
                "region_id",
                "vehicle_mode",
            ),
        )
        Operator.objects.bulk_update(
            to_update, ("url", "twitter", "name", "vehicle_mode")
        )

        # Save any new operators created so they get IDs before creating codes/licences
        for operator in to_create:
            if operator.pk is None:
                operator.save()

        # Filter out operator_codes that already exist to avoid duplicates
        existing_codes = set(
            OperatorCode.objects.filter(
                source=noc_source, code__in=[oc.code for oc in operator_codes]
            ).values_list("operator_id", "code", "source_id")
        )
        operator_codes_to_create = [
            oc
            for oc in operator_codes
            if (oc.operator.pk, oc.code, oc.source_id) not in existing_codes
        ]

        OperatorCode.objects.bulk_create(operator_codes_to_create)

        # Filter out licences that already exist to avoid duplicates
        existing_licences = set(
            Operator.licences.through.objects.filter(
                operator_id__in=[ol.operator.pk for ol in operator_licences],
                licence_id__in=[ol.licence.pk for ol in operator_licences],
            ).values_list("operator_id", "licence_id")
        )
        operator_licences_to_create = [
            ol
            for ol in operator_licences
            if (ol.operator.pk, ol.licence.pk) not in existing_licences
        ]

        Operator.licences.through.objects.bulk_create(operator_licences_to_create)
