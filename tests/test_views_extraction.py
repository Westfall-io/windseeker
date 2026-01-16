from windseeker.main import extract_views_from_package_text


def test_extract_views():
    text = """
    package A {
        package Views {
            view testView {
                expose A;
            }
        }
    }
    """

    views = extract_views_from_package_text(text)

    assert "A::Views::testView" in views
