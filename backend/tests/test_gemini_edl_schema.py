from app.providers.gemini import GeminiEDLSegment, GeminiProvider, GeminiTrailerEDL


def test_gemini_edl_schema_uses_supported_types():
    schema = GeminiTrailerEDL.model_json_schema()
    segment_schema = schema["$defs"]["GeminiEDLSegment"]["properties"]
    assert segment_schema["act"]["enum"] == ["1", "2", "3"]
    assert "exclusiveMinimum" not in str(schema)


def test_gemini_segments_convert_to_internal_edl():
    parsed = GeminiTrailerEDL(
        title="Test",
        tagline="Tagline",
        duration=22,
        genre="comedy",
        cast=[],
        beat_markers=[0, 11, 20],
        segments=[GeminiEDLSegment(asset_id="a", act="1", start=0, end=22, ken_burns="zoom_in")],
    )
    edl = GeminiProvider._to_edl(parsed)
    assert edl.segments[0].act == 1
    assert edl.duration == 22
