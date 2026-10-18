"""Offline safety tests only; never connect to Fusion or invoke real adsk."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS, ModuleType
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('bed_qualification', Path(__file__).with_name('qualify_bed.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def document(saved=True, read_only=False, modified=True):
    return NS(isValid=True, name='protected', isSaved=saved, isModified=modified,
              dataFile=NS(id='private-test-identity', versionNumber=2, isReadOnly=read_only)
              if saved else None)


def application(docs, used=3, maximum=10):
    return NS(documents=NS(count=len(docs), item=lambda i: docs[i], add=Mock()),
              data=NS(personalUseLimits=NS(editableFileCount=used, maxEditableFileCount=maximum)))


class PreflightTests(unittest.TestCase):
    def test_saved_read_only_and_dirty_states_preserved(self):
        for read_only in (False, True):
            for dirty in (False, True):
                doc = document(read_only=read_only, modified=dirty)
                original = dict(vars(doc.dataFile))
                state = helper.document_state(doc)
                self.assertEqual(state['read_only'], read_only)
                self.assertEqual(state['modified'], dirty)
                self.assertEqual(state['version'], 2)
                self.assertEqual(vars(doc.dataFile), original)
                self.assertEqual(doc.isModified, dirty)

    def test_unsaved_clean_and_dirty_preserved(self):
        for dirty in (False, True):
            doc = document(saved=False, modified=dirty)
            state = helper.document_state(doc)
            self.assertFalse(state['saved'])
            self.assertEqual(state['modified'], dirty)
            for key in ('identity_sha256', 'version', 'read_only'):
                self.assertIsNone(state[key])
            self.assertIsNone(doc.dataFile)

    def test_missing_or_invalid_saved_metadata(self):
        cases = {'id': [None, '', '  ', 123],
                 'versionNumber': [None, 0, -1, True, 2.0, '2', float('nan'), float('inf')],
                 'isReadOnly': [None, 0, 'false']}
        for key, values in cases.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    doc = document()
                    setattr(doc.dataFile, key, value)
                    with self.assertRaises(RuntimeError):
                        helper.document_state(doc)
            doc = document()
            delattr(doc.dataFile, key)
            with self.assertRaises(AttributeError):
                helper.document_state(doc)

    def test_document_state_missing_or_contradictory(self):
        for attr, value in [('isValid', False), ('isSaved', None), ('isModified', None),
                            ('name', ''), ('dataFile', None), ('isSaved', False)]:
            with self.subTest(attr=attr):
                doc = document()
                setattr(doc, attr, value)
                with self.assertRaises(RuntimeError):
                    helper.document_state(doc)

    def test_capacity_counts_fail_closed(self):
        for used, maximum in [(None, 10), (3, None), (True, 10), (3, False),
                              ('3', 10), (3.0, 10), (-1, 10), (11, 10), (0, 0),
                              (0, -1), (float('nan'), 10), (3, float('inf'))]:
            with self.subTest(used=used, maximum=maximum):
                with self.assertRaises(RuntimeError):
                    helper.capacity_state(application([], used, maximum), [])

    def test_missing_limits_and_failed_api_stop(self):
        app = application([])
        app.data.personalUseLimits = None
        with self.assertRaises(RuntimeError):
            helper.capacity_state(app, [])
        app = application([])
        del app.data.personalUseLimits.editableFileCount
        with self.assertRaises(AttributeError):
            helper.capacity_state(app, [])
        class Unavailable:
            @property
            def personalUseLimits(self):
                raise RuntimeError('API unavailable')
        app.data = Unavailable()
        with self.assertRaisesRegex(RuntimeError, 'API unavailable'):
            helper.capacity_state(app, [])

    def test_capacity_consistency_and_full_capacity(self):
        states = [helper.document_state(document())]
        with self.assertRaisesRegex(RuntimeError, 'contradicts'):
            helper.capacity_state(application([], 0), states)
        self.assertEqual(helper.capacity_state(application([], 10), states),
                         {'used': 10, 'maximum': 10})
        readonly_unsaved = [helper.document_state(document(read_only=True)),
                           helper.document_state(document(saved=False))]
        self.assertEqual(helper.capacity_state(application([], 0), readonly_unsaved)['used'], 0)
        with self.assertRaisesRegex(RuntimeError, 'Duplicate'):
            helper.capacity_state(application([]), states + states)

    def test_run_rejects_before_document_creation_imports_or_disk_inventory(self):
        # Exercise run() ordering with fake adsk modules; real Fusion is never imported.
        cases = []
        bad_doc = document()
        bad_doc.dataFile.versionNumber = None
        cases.append(application([bad_doc]))
        cases.append(application([document()], used=None))
        cases.append(application([document()], used=0))
        cases.append(application([document(), document()]))
        for app in cases:
            with self.subTest(app=app):
                adsk = ModuleType('adsk')
                adsk.core, adsk.fusion = ModuleType('adsk.core'), ModuleType('adsk.fusion')
                adsk.core.Application = NS(get=lambda: app)
                with patch.dict('sys.modules', {'adsk': adsk, 'adsk.core': adsk.core,
                                                'adsk.fusion': adsk.fusion}), \
                     patch.object(helper, 'OUTPUT', Mock(exists=lambda: False)), \
                     patch.object(helper, 'file_inventory') as inventory, \
                     patch.object(helper.importlib, 'import_module') as imports:
                    with self.assertRaises(RuntimeError):
                        helper.run(None)
                    app.documents.add.assert_not_called()
                    inventory.assert_not_called()
                    imports.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
