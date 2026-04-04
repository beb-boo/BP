"""Tests for TMC v3 doctor verification parser."""
import pytest
from app.utils.tmc_checker import _parse_tmc_response, TMCDoctorResult


# ── HTML Fixtures ──────────────────────────────────────

FOUND_SINGLE_HTML = """
<div class="panel panel-info">
    <div class="panel-heading"><strong>ค้นพบผู้ประกอบวิชาชีพเวชกรรม(แพทย์) จำนวน 1 รายการ</strong></div>
    <div class="panel-body">
        <article class="col-sm-3 col-md-3 col-lg-2">
            <img class="thumbnail center-block" src="data:image/jpg;base64,abc" width="108" />
        </article>
        <article class="col-sm-9 col-md-9 col-lg-10">
            <div class="col-sm-12 col-md-9 col-lg-10"><strong>พญ. ภัทราวรรณ ภิสัชเพ็ญ</strong></div>
            <div class="col-sm-12 col-md-9 col-lg-10 text-info">PHATTRAWAN PISUCHPEN, M.D.</div>
            <div class="col-sm-12 col-md-9 col-lg-10"><br /></div>
            <div class="col-sm-12 col-md-9 col-lg-10"><strong>เป็นผู้ประกอบวิชาชีพเวชกรรมตั้งแต่ พ.ศ. 2549</strong></div>
            <div class="col-sm-12 col-md-9 col-lg-10 text-info"><span>Permission to practice medicine since 2006</span></div>
        </article>
        <article class="col-sm-12 col-md-9 col-lg-10 hidden-phone">
            <ul class="fa-ul text-info">
                <li><i class="fa-li fa fa-check"></i> สาขา จักษุวิทยา ( Ophthalmology ) </li>
            </ul>
        </article>
    </div>
</div>
"""

NOT_FOUND_HTML = """
<div class="panel panel-info">
    <div class="panel-heading"><strong>ค้นพบผู้ประกอบวิชาชีพเวชกรรม(แพทย์) จำนวน 0 รายการ</strong></div>
    <div class="panel-body">
        <p>ไม่พบข้อมูล</p>
    </div>
</div>
"""

SUSPENDED_HTML = """
<div class="panel panel-info">
    <div class="panel-heading"><strong>ค้นพบผู้ประกอบวิชาชีพเวชกรรม(แพทย์) จำนวน 1 รายการ</strong></div>
    <div class="panel-body">
        <article class="col-sm-9 col-md-9 col-lg-10">
            <div class="col-sm-12 col-md-9 col-lg-10"><strong>นพ. ทดสอบ พักใบ</strong></div>
            <div class="col-sm-12 col-md-9 col-lg-10 text-info">TEST SUSPENDED, M.D.</div>
            <div class="col-sm-12 col-md-9 col-lg-10"><strong>เป็นผู้ประกอบวิชาชีพเวชกรรมตั้งแต่ พ.ศ. 2540</strong></div>
        </article>
        <div class="alert alert-danger alert-dismissable col-lg-12">
            พักใช้ใบอนุญาตฯ ตั้งแต่วันที่ 1 มกราคม 2568 ถึงวันที่ 1 มกราคม 2569
        </div>
    </div>
</div>
"""

MULTIPLE_RESULTS_HTML = """
<div class="panel panel-info">
    <div class="panel-heading"><strong>ค้นพบผู้ประกอบวิชาชีพเวชกรรม(แพทย์) จำนวน 3 รายการ</strong></div>
    <div class="panel-body">
        <article class="col-sm-9"><div class="col-sm-12 col-md-9 col-lg-10"><strong>นพ. สมชาย ใจดี</strong></div></article>
        <article class="col-sm-9"><div class="col-sm-12 col-md-9 col-lg-10"><strong>นพ. สมชาย รักดี</strong></div></article>
        <article class="col-sm-9"><div class="col-sm-12 col-md-9 col-lg-10"><strong>นพ. สมชาย มีสุข</strong></div></article>
    </div>
</div>
"""


# ── Tests ──────────────────────────────────────

class TestParseTMCResponse:

    def test_found_single_doctor(self):
        result = _parse_tmc_response(FOUND_SINGLE_HTML)
        assert result.verified is True
        assert result.found is True
        assert result.result_count == 1
        assert result.full_name_th == "พญ. ภัทราวรรณ ภิสัชเพ็ญ"
        assert result.full_name_en == "PHATTRAWAN PISUCHPEN, M.D."
        assert result.license_year_be == 2549
        assert result.license_year_ce == 2006
        assert len(result.specialties) >= 1
        assert "จักษุวิทยา" in result.specialties[0]
        assert result.license_suspended is False
        assert result.message == "Found in TMC Database"

    def test_not_found(self):
        result = _parse_tmc_response(NOT_FOUND_HTML)
        assert result.verified is False
        assert result.found is False
        assert result.result_count == 0
        assert result.message == "Not Found in TMC Database"

    def test_suspended_license(self):
        result = _parse_tmc_response(SUSPENDED_HTML)
        assert result.found is True
        assert result.verified is False
        assert result.license_suspended is True
        assert result.full_name_th == "นพ. ทดสอบ พักใบ"
        assert "พักใช้" in result.suspension_detail
        assert result.message == "Doctor found but license is SUSPENDED"

    def test_multiple_results(self):
        result = _parse_tmc_response(MULTIPLE_RESULTS_HTML)
        assert result.found is True
        assert result.verified is False
        assert result.result_count == 3
        assert "Multiple matches" in result.message

    def test_empty_html(self):
        result = _parse_tmc_response("")
        assert result.verified is False
        assert result.found is False

    def test_legacy_wrapper_dict_shape(self):
        result = TMCDoctorResult(
            verified=True, found=True,
            message="Found in TMC Database",
            full_name_th="พญ. ทดสอบ",
        )
        legacy = result.to_legacy_dict()
        assert "verified" in legacy
        assert "message" in legacy
        assert "details" in legacy
        assert legacy["verified"] is True

    def test_legacy_wrapper_suspended(self):
        result = TMCDoctorResult(
            verified=False, found=True,
            license_suspended=True,
            suspension_detail="พักใช้ใบอนุญาต 1 ปี",
            message="Doctor found but license is SUSPENDED",
        )
        legacy = result.to_legacy_dict()
        assert legacy["verified"] is False
        assert "SUSPENDED" in legacy["details"]
