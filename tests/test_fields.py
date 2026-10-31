# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import unittest
from dracula.status import field_rows,fetch_page,BY_KEY

def xml(**fields):
    return ('<drac><object name="test">'+''.join('<property name="'+k+'"><value>'+v+'</value></property>' for k,v in fields.items())+'</object></drac>').encode()

class FieldSemanticsTests(unittest.TestCase):
    def test_known_flags_are_typed_without_changing_counts(self):
        rows=field_rows(xml(Enabled='1',ActiveSessions='1',MaxSessions='2'), 'vkvmconfig')
        self.assertEqual((rows[0].value,rows[0].checked,rows[0].changeability),('Enabled',True,'configurable'))
        self.assertEqual((rows[1].value,rows[1].checked,rows[1].changeability),('1',None,'read-only'))
    def test_numeric_zero_one_is_not_sufficient_to_infer_a_boolean_or_editability(self):
        for row in field_rows(xml(Enabled='1',RecordId='0',Port='1'),'unreviewed'):
            self.assertIsNone(row.checked);self.assertEqual(row.changeability,'unknown')
    def test_negative_flags_preserve_their_meaning(self):
        row=field_rows(xml(LocalCfgUsingRomDisabled='1'),'services')[0]
        self.assertEqual(row.value,'True');self.assertTrue(row.checked)
        self.assertIn('disabled',row.field)
    def test_named_enabled_fields_can_be_multivalued_selectors(self):
        row=field_rows(xml(BootOnceEnabled='4'),'vmconfig')[0]
        self.assertEqual(row.value,'PXE');self.assertIsNone(row.checked)
        row=field_rows(xml(AuthorizeMultipleSessions='1'),'vkvmconfig')[0]
        self.assertEqual(row.value,'Read-only access');self.assertIsNone(row.checked)
    def test_two_choice_enums_show_the_actual_option(self):
        row=field_rows(xml(PluginType='1'),'vkvmconfig')[0]
        self.assertEqual((row.value,row.checked),('Java',True))
    def test_unknown_and_missing_flags_are_not_presented_as_off(self):
        for value in ('2',''):
            row=field_rows(xml(Enabled=value),'sol')[0]
            self.assertIsNone(row.checked);self.assertNotEqual(row.value,'Disabled')
    def test_literal_booleans_are_typed_but_not_assumed_configurable(self):
        row=field_rows(xml(Unexpected='false'),'unreviewed')[0]
        self.assertEqual(row.value,'False');self.assertFalse(row.checked)
        self.assertEqual(row.changeability,'unknown')
    def test_secrets_stay_redacted_even_when_fields_are_configurable(self):
        rows=field_rows(xml(Password='sensitive',CommunityName='sensitive',EncryptionKey='sensitive',UserName='demo'),'users')
        self.assertEqual(len(rows),1);self.assertNotIn('sensitive',str(rows))
    def test_detailed_and_legacy_fetch_agree_on_display_values(self):
        class Fake:
            def request(self,path):return xml(Enabled='0')
        detailed,errors=fetch_page(Fake(),BY_KEY['sol'],detailed=True)
        legacy,_=fetch_page(Fake(),BY_KEY['sol'])
        self.assertFalse(errors);self.assertEqual(legacy[0][2],detailed[0].value)
        self.assertFalse(detailed[0].checked)

    def test_reported_status_flags_do_not_imply_edit_permission(self):
        row=field_rows(xml(AuthDisabled='0'),'serial')[0]
        self.assertEqual((row.value,row.checked,row.changeability),('False',False,'unknown'))
        row=field_rows(xml(Enabled='1'),'sysinfo')[0]
        self.assertEqual((row.value,row.checked,row.changeability),('Enabled',True,'read-only'))
