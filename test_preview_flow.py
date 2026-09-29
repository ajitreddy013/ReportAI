import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from utils.reference_extractor import reference_extractor
from utils.document_builder import document_builder
from enhanced_content_generator import enhanced_generator, REPORT_FORMAT_PRESETS
from main import get_system_status, get_presets, generate_preview, export_docx

async def run_tests_async():
    print("🚀 Starting ReportAI v2.0 Architecture & Integration Tests...")
    
    # 1. Test Reference Extraction
    print("\n--- 1. Testing Reference Extractor ---")
    notes = "Key requirement: Must use ResNet-50 and MobileNet backbone. Evaluate precision, recall, and F1 on custom dataset."
    link_info = reference_extractor.extract_from_url("https://example.com")
    print(f"✓ URL extraction: {link_info.get('title')}")
    
    compiled = reference_extractor.compile_all_references(
        extracted_files=[],
        extracted_links=[link_info],
        raw_notes=notes
    )
    assert compiled["has_references"] == True
    print(f"✓ Compiled references count: {compiled['total_sources_count']}")

    # 2. Test Format Presets
    print("\n--- 2. Testing Report Format Presets ---")
    for preset_key, preset in REPORT_FORMAT_PRESETS.items():
        sections = enhanced_generator.get_sections_for_format(preset_key)
        assert len(sections) >= 5
        print(f"✓ Preset '{preset_key}': {len(sections)} sections ({preset['title']})")

    # 3. Test Preview Generation Async
    print("\n--- 3. Testing Report Preview Generation ---")
    preview_res = await enhanced_generator.generate_report_preview(
        topic="Federated Learning in Edge Computing for Healthcare",
        format_type="project_report",
        academic_info={
            "student_name": "Ajit Reddy",
            "roll_no": "CS-2026-042",
            "college_name": "Sinhgad College of Engineering, Pune",
            "department": "Computer Engineering"
        },
        reference_context=compiled["full_context_text"],
        reference_sources=compiled["sources"]
    )
    assert preview_res["success"] == True
    assert len(preview_res["sections"]) == 7
    assert preview_res["total_words"] > 500
    print(f"✓ Generated preview: {preview_res['total_words']} words across {len(preview_res['sections'])} sections")

    # 4. Test DOCX Document Builder
    print("\n--- 4. Testing DOCX Document Builder ---")
    docx_filename = document_builder.create_docx_report(preview_res)
    output_path = os.path.join(os.path.dirname(__file__), "backend", "outputs", docx_filename)
    assert os.path.exists(output_path)
    print(f"✓ DOCX successfully built: {docx_filename} ({os.path.getsize(output_path)} bytes)")

    # 5. Test Direct FastAPI Endpoint Coroutines
    print("\n--- 5. Testing FastAPI Endpoints Directly ---")
    
    # Status endpoint
    status_response = await get_system_status()
    assert status_response.status_code == 200
    print("✓ GET /api/status -> 200 OK")

    # Presets endpoint
    presets_response = await get_presets()
    assert presets_response.status_code == 200
    print("✓ GET /api/presets -> 200 OK")

    # Generate Preview endpoint
    preview_response = await generate_preview(
        topic="Autonomous Drone Navigation using Deep Reinforcement Learning",
        format_type="seminar_report",
        student_name="Ajit Reddy",
        roll_no="CS-2026-042",
        college_name="Sinhgad College of Engineering, Pune",
        department="Computer Engineering",
        academic_year="2025 - 2026",
        guide_name="Dr. S. K. Kulkarni",
        reference_links='["https://example.com/research-paper"]',
        reference_text="Include Soft Actor-Critic (SAC) comparisons.",
        reference_files=None
    )
    assert preview_response.status_code == 200
    import json
    preview_body = json.loads(preview_response.body.decode("utf-8"))
    assert preview_body["success"] == True
    print(f"✓ POST /api/generate-preview -> 200 OK ({preview_body['total_words']} words generated)")

    # Export DOCX endpoint
    docx_response = await export_docx(preview_body)
    assert docx_response.status_code == 200
    print(f"✓ POST /api/export-docx -> 200 OK (FileResponse to {docx_response.filename})")

    print("\n🎉 ALL TESTS PASSED PROPERLY!")

if __name__ == "__main__":
    asyncio.run(run_tests_async())
