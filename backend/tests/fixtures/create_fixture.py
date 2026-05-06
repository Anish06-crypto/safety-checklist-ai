"""
Creates a synthetic DROPS-like PDF for testing.
Run once to generate: python3 create_fixture.py
"""
import fitz
import os

def create_drops_fixture():
    doc = fitz.open()

    # Pages 1-21: intro content (should NOT appear in prose_text)
    for i in range(21):
        page = doc.new_page()
        page.insert_text((50, 50), f"Introduction Section {i+1}\n\nThis is background and definitions content.")

    # Pages 22-35: Sections 3-4 prose (SHOULD appear in prose_text)
    for i in range(14):
        page = doc.new_page()
        page.insert_text((50, 50), (
            f"3.{i+1} DROPS Inspection Procedure\n\n"
            "An independent DROPS inspection shall be conducted by a competent person. "
            "The inspector shall verify all secondary retention systems on the crown block "
            "assembly, travelling block, and top drive. Each item shall be assessed for "
            "the adequacy of its secondary retention. Inspection frequency: 6-monthly."
        ))

    # Pages 36-39: gap pages
    for i in range(4):
        page = doc.new_page()
        page.insert_text((50, 50), f"Reporting and Performance {i+1}")

    # Pages 40+: Annex pages (should appear in annex_blocks NOT prose_text)
    annexes = [
        ("Annex A", "DROPS Calculator\n\nMass and height thresholds."),
        ("Annex B", "Training Matrix\n\nRequired competencies."),
        ("Annex C", "Post Jarring Checklist\n\nCheck crown block assembly sheave pins and keeper plates.\nVerify secondary retention wires intact."),
        ("Annex D", "Tubular Handling Checklist\n\nInspect thread protectors.\nVerify lifting cap rated for load."),
        ("Annex E", "Portable Tools and Equipment\n\nTool Inventory Log.\nTools At Height Register."),
    ]
    for title, content in annexes:
        page = doc.new_page()
        page.insert_text((50, 50), f"{title}\n\n{content}")

    out_path = os.path.join(os.path.dirname(__file__), "drops_fixture.pdf")
    page_count = len(doc)
    doc.save(out_path)
    doc.close()
    print(f"Created: {out_path} ({page_count} pages)")

if __name__ == "__main__":
    create_drops_fixture()
