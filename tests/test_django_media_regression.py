"""Workshop acceptance probes derived from Django ticket #30179."""

import unittest
import warnings

from django.forms import Media
from django.forms.widgets import MediaOrderConflictWarning


class MediaDependencyRegressionTests(unittest.TestCase):
    def test_three_way_js_dependency(self):
        media = (Media(js=["color-picker.js"]) +
                 Media(js=["text-editor.js"]) +
                 Media(js=["text-editor.js", "text-editor-extras.js", "color-picker.js"]))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", MediaOrderConflictWarning)
            assets = list(media._js)
        self.assertEqual(set(assets), {"color-picker.js", "text-editor.js", "text-editor-extras.js"})
        self.assertEqual(len(assets), 3)
        self.assertLess(assets.index("text-editor.js"), assets.index("text-editor-extras.js"))
        self.assertFalse([w for w in caught if issubclass(w.category, MediaOrderConflictWarning)])

    def test_css_dependency_and_deduplication(self):
        media = (Media(css={"all": ["color.css"]}) +
                 Media(css={"all": ["base.css"]}) +
                 Media(css={"all": ["base.css", "theme.css", "color.css"]}))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", MediaOrderConflictWarning)
            assets = list(media._css["all"])
        self.assertEqual(set(assets), {"color.css", "base.css", "theme.css"})
        self.assertEqual(len(assets), 3)
        self.assertLess(assets.index("base.css"), assets.index("theme.css"))
        self.assertFalse([w for w in caught if issubclass(w.category, MediaOrderConflictWarning)])

    def test_duplicate_in_single_definition(self):
        self.assertEqual(list(Media(js=["one.js", "one.js"])._js), ["one.js"])

    def test_real_cycle_warns_without_losing_assets(self):
        media = Media(js=["a.js", "b.js"]) + Media(js=["b.js", "a.js"])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", MediaOrderConflictWarning)
            assets = list(media._js)
        self.assertEqual(set(assets), {"a.js", "b.js"})
        self.assertEqual(len(assets), 2)
        self.assertTrue([w for w in caught if issubclass(w.category, MediaOrderConflictWarning)])


if __name__ == "__main__":
    unittest.main()
