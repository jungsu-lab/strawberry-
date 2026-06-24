import unittest


class ParserImportTest(unittest.TestCase):
    def test_parser_module_imports_without_optional_pymodbus(self):
        import libsbapi.parser as parser

        self.assertTrue(hasattr(parser, "Decoder"))
