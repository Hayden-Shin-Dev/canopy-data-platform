from src.mobility_v4.contracts import validate_sample


def test_official_contract_rejects_gps_only_sample():
    result = validate_sample({"gps": [1], "tensor_shape": (340, 60)})
    assert result["valid"] is False
    assert set(result["missing_modalities"]) == {"imu", "ap", "bts"}


def test_official_contract_accepts_full_shape_without_mapping_claim():
    result = validate_sample(
        {"gps": [1], "imu": [1], "ap": [1], "bts": [1], "tensor_shape": (340, 60)}
    )
    assert result == {
        "valid": True,
        "missing_modalities": [],
        "tensor_shape": [340, 60],
    }


def test_official_contract_rejects_wrong_tensor_shape():
    result = validate_sample(
        {"gps": [1], "imu": [1], "ap": [1], "bts": [1], "tensor_shape": (16, 120)}
    )
    assert result["valid"] is False
    assert result["shape_error"] == "expected (340, 60)"
