import pytest
import form126 as f


def test_all_specified_records_tile_964():
    for rec in f.SPEC:
        f.check_spec(rec)
        assert f.SPEC[rec][0].start == 1 and f.SPEC[rec][-1].end == 964


def test_unspecified_records_are_refused():
    with pytest.raises(f.SpecError):
        f.build_record("40", {})


def test_record_10_positions():
    line = f.build_record("10", {"1": 912345678, "2": 0, "4": 2025, "6": 1, "7": 25,
                                 "9": "ACME", "11": 123456789, "25": 7}, hebrew_visual=False)
    assert len(line) == 964
    assert line[0:9] == "912345678"
    assert line[11:13] == "10"
    assert line[13:17] == "2025"
    assert line[26:28] == "01"
    assert line[28:33] == "00025"
    assert line[34:52] == "ACME".ljust(18)
    assert line[95:104] == "123456789"
    assert line[959:964] == "00007"


def test_record_30_constants_and_count():
    line = f.build_record("30", {"1": 912345678, "4": 2025, "14": 3, "24א'": 5}, hebrew_visual=False)
    assert line[11:13] == "30"
    assert line[115:121] == "000003"
    assert line[209:211] == "44"
    assert line[283:289] == "000005"
    assert f.SPEC["30"][-1].no == "25"


def test_record_50_month_and_columns():
    line = f.build_record("50", {"1": 912345678, "4": 2025, "6": 1, "7": 100, "8": 5000000})
    assert line[11:13] == "50"
    assert line[26:28] == "01"
    assert line[28:34] == "000100"
    assert line[34:46] == "000005000000"
    assert len(line) == 964


def test_negative_number_has_minus_in_leftmost_column():
    fld = f.Field("x", "x", 1, 7, "N")
    assert f._num(fld, -432) == "-000432"


def test_number_too_long_is_an_error():
    fld = f.Field("x", "x", 1, 3, "N")
    with pytest.raises(ValueError):
        f._num(fld, 1000)


def test_hebrew_requires_explicit_ordering_choice():
    with pytest.raises(f.SpecError):
        f.build_record("10", {"9": "כהן"})
    ok = f.build_record("10", {"9": "כהן"}, hebrew_visual=True)
    assert ok[34:37] == "כהן"[::-1]


def test_constant_cannot_be_overridden():
    with pytest.raises(f.SpecError):
        f.build_record("30", {"22": 45}, hebrew_visual=False)


def test_unknown_field_rejected():
    with pytest.raises(f.SpecError):
        f.build_record("50", {"99": 1})


def test_encoding_must_be_one_the_spec_allows():
    line = f.build_record("50", {})
    with pytest.raises(f.SpecError):
        f.encode_file([line], "utf-8")
    assert f.encode_file([line], "cp1255").endswith(b"\r\n")
    assert len(f.encode_file([line], "cp862")) == 966


def test_id_check_digit():
    assert f.check_id_digit("000000018")
    assert not f.check_id_digit("000000019")


def test_record_20_layout_and_key_columns():
    assert len(f.SPEC["20"]) == 189
    line = f.build_record("20", {"1": 912345678, "4": 2025, "5": 18, "14": 2, "15": 20,
                                 "18": 19850314, "23": 20200101}, hebrew_visual=False)
    assert len(line) == 964
    assert line[11:13] == "20"
    assert line[17:26] == "000000018"
    assert line[118] == "2"                # gender, column 119
    assert line[119:121] == "20"           # marital status, columns 120-121
    assert line[131:139] == "19850314"     # birth date, columns 132-139
    assert line[173:181] == "20200101"     # start date, columns 174-181
    assert line[959:964] == "00000"        # last field, columns 960-964


def test_record_20_fields_in_spec_order_and_unique_ranges():
    ends = [x.end for x in f.SPEC["20"]]
    assert ends == sorted(ends)
    assert len({(x.start, x.end) for x in f.SPEC["20"]}) == len(ends)
