# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import unittest
from dracula.drac5 import parse_status

class StatusTests(unittest.TestCase):
    def test_only_status_fields_leave_parser(self):
        xml = '<drac><sid>secret</sid><object name="rac"><property name="FirmwareVersion"><value>1.65</value></property><property name="Password"><value>secret</value></property></object></drac>'
        self.assertEqual(parse_status(xml), {"rac": {"FirmwareVersion": "1.65"}})

    def test_login_page_is_not_healthy_status(self):
        with self.assertRaises(ValueError):
            parse_status('<drac><LOGIN><RESP><RC>0</RC></RESP></LOGIN></drac>')

    def test_reject_entity_documents(self):
        with self.assertRaises(ValueError):
            parse_status('<!DOCTYPE drac [<!ENTITY x "secret">]><drac/>')

    def test_kvm_ports_come_from_device(self):
        xml = '<drac><object name="vkvm"><property name="VideoPortNumber"><value>5901</value></property></object></drac>'
        self.assertEqual(parse_status(xml)["vkvm"]["VideoPortNumber"], "5901")
