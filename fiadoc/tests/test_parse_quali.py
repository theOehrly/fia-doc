import json

import pytest

from fiadoc.parser import QualifyingParser
from fiadoc.utils import download_pdf

race_list = [
    (
        '2024_22_usa_f1_q0_timing_qualifyingsessionprovisionalclassification_v01.pdf',
        '2024_22_usa_f1_q0_timing_qualifyingsessionlaptimes_v01.pdf',
        2024,
        22,
        '2024_22_quali_provisional_classification.json',
        '2024_22_quali_lap_times.json'
    )
]


@pytest.fixture(params=race_list)
def prepare_quali_data(request, tmp_path) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    # Download and parse quali. classification and lap times PDF
    url_classification, url_lap_time, year, round_no, expected_classification, expected_lap_times \
        = request.param
    download_pdf('https://www.fia.com/sites/default/files/' + url_classification,
                 tmp_path / 'classification.pdf')
    download_pdf('https://www.fia.com/sites/default/files/' + url_lap_time,
                 tmp_path / 'lap_times.pdf')
    parser = QualifyingParser(tmp_path / 'classification.pdf', tmp_path / 'lap_times.pdf',
                              year, round_no, 'quali')

    classification_data = parser.classification_df.to_json()
    lap_times_data = parser.lap_times_df.to_json()
    with open('fiadoc/tests/fixtures/' + expected_classification, encoding='utf-8') as f:
        expected_classification = json.load(f)
    with open('fiadoc/tests/fixtures/' + expected_lap_times, encoding='utf-8') as f:
        expected_lap_times = json.load(f)

    # Sort data
    classification_data.sort(
        key=lambda x: (x['foreign_keys']['session'], x['foreign_keys']['car_number'])
    )
    expected_classification.sort(
        key=lambda x: (x['foreign_keys']['session'], x['foreign_keys']['car_number'])
    )
    lap_times_data.sort(
        key=lambda x: (x['foreign_keys']['session'], x['foreign_keys']['car_number'])
    )
    expected_lap_times.sort(
        key=lambda x: (x['foreign_keys']['session'], x['foreign_keys']['car_number'])
    )
    for i in lap_times_data:
        i['objects'].sort(key=lambda x: x['number'])
    for i in expected_lap_times:
        i['objects'].sort(key=lambda x: x['number'])

    # TODO: currently manually tested against fastf1 lap times. The test data should be generated
    #       automatically later. Also need to manually add if the lap time is deleted and if the
    #       lap is fastest manually. Also need to add the laps where PDFs have data but fastf1
    #       doesn't
    return classification_data, lap_times_data, expected_classification, expected_lap_times


def test_parse_quali(prepare_quali_data):
    classification_data, lap_times_data, expected_classification, expected_lap_times \
        = prepare_quali_data
    assert classification_data == expected_classification

    # TODO: need to test against fastf1 in a better and more readable way
    for i in lap_times_data:
        driver = i['foreign_keys']['car_number']
        session = i['foreign_keys']['session']
        laps = i['objects']
        for j in expected_lap_times:
            if j['foreign_keys']['car_number'] == driver \
                    and j['foreign_keys']['session'] == session:
                expected_laps = j['objects']
                for lap in laps:
                    # Here we allow the lap to be missing in fastf1 data
                    for expected_lap in expected_laps:
                        if lap['number'] == expected_lap['number']:
                            assert lap['time'] == expected_lap['time'], \
                                f"Driver {driver}'s lap {lap['number']} in {session} time " \
                                f"doesn't match with fastf1: {lap['time']['milliseconds']} vs " \
                                f'{expected_lap['time']['milliseconds']}'
                            break

    for i in expected_lap_times:
        driver = i['foreign_keys']['car_number']
        session = i['foreign_keys']['session']
        expected_laps = i['objects']
        for j in lap_times_data:
            if j['foreign_keys']['car_number'] == driver \
                    and j['foreign_keys']['session'] == session:
                laps = i['objects']
                for expected_lap in expected_laps:
                    found = False
                    for lap in laps:
                        if lap['number'] == expected_lap['number']:
                            found = True
                            break
                    # But here any lap available in fastf1 data should be in PDF as well
                    assert found, f"Driver {driver}'s lap {expected_lap['number']} in {session} " \
                                  f"in fastf1 not found in PDF"
                    assert lap['time'] == expected_lap['time'], \
                        f"Driver {driver}'s lap {expected_lap['number']} in {session} time " \
                        f"doesn't match with fastf1: {lap['time']['milliseconds']} vs " \
                        f"{expected_lap['time']['milliseconds']}"