import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from local_draft_runtime import PROFILE, APP_BUILD, LIBRARY_SHA256, validate_timeline_schema, validate_basic_plan
import runtime_profiles as canonical


class LocalDraftScopeTests(unittest.TestCase):
    def test_observed_saved_schema_is_accepted(self):
        self.assertEqual(validate_timeline_schema({'new_version': '189.0.0', 'version': 360000,
                                                   'last_modified_platform': {'app_version': APP_BUILD}}, PROFILE),
                         ('189.0.0', 360000))

    def test_saved_schema_from_another_beta_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'exact observed beta'):
            validate_timeline_schema({'new_version': '189.0.0', 'version': 360000,
                                      'last_modified_platform': {'app_version': '11.6.0-beta3'}}, PROFILE)

    def test_unknown_schema_and_profile_are_refused(self):
        for value, profile in [({'new_version': '190.0.0', 'version': 360000}, PROFILE),
                               ({'new_version': '189.0.0', 'version': True}, PROFILE),
                               ({'new_version': '189.0.0', 'version': 360000}, 'other')]:
            with self.subTest(value=value, profile=profile), self.assertRaises(ValueError):
                validate_timeline_schema(value, profile)

    def test_canonical_identity_gate_is_not_expanded(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported Jianying'):
            canonical.validate_identity({'CFBundleShortVersionString': '11.5.13264',
                                         'CFBundleVersion': '11.6.0-beta6',
                                         'CFBundleIdentifier': 'com.lemon.lvpro'}, LIBRARY_SHA256)

    def test_local_profile_cannot_be_used_for_native_export(self):
        self.assertNotIn(PROFILE, canonical.EXPORT_PROFILES)
        with self.assertRaises(ValueError):
            canonical.validate_export_profiles(PROFILE, PROFILE)

    def test_basic_tracks_allowed_and_cached_effects_refused(self):
        validate_basic_plan({'tracks': [{'type': 'video', 'segments': [{}]},
                                        {'type': 'text', 'segments': [{}]},
                                        {'type': 'audio', 'segments': [{}]}]})
        for forbidden in ['mask', 'transition_out', 'text_effect', 'text_animation']:
            with self.subTest(forbidden=forbidden), self.assertRaises(ValueError):
                validate_basic_plan({'tracks': [{'type': 'video', 'segments': [{forbidden: {}}]}]})
        with self.assertRaises(ValueError):
            validate_basic_plan({'tracks': [{'type': 'effect', 'segments': [{}]}]})


if __name__ == '__main__':
    unittest.main()
