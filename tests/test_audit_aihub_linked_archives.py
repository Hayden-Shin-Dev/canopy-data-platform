from pathlib import Path
import zipfile

from scripts.audit_aihub_linked_archives import audit_archive


def test_audit_archive_reads_schema_without_extraction(tmp_path: Path) -> None:
    archive_path = tmp_path / "linked.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "trajectory.csv",
            "timestamp,station_id,station_latitude,station_longitude,station_name,station_line\n"
            "1,100,37.5,126.9,Station,1\n",
        )
    result = audit_archive(archive_path, sample_count=1)
    assert result["entry_count"] == 1
    assert result["contains_station_metadata"] is True
    assert result["samples"][0]["columns"][0] == "timestamp"


def test_audit_archive_rejects_empty_archive(tmp_path: Path) -> None:
    archive_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(archive_path, "w"):
        pass
    try:
        audit_archive(archive_path)
    except ValueError as error:
        assert "no files" in str(error)
    else:
        raise AssertionError("empty archive should be rejected")
