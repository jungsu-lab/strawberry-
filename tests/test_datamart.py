import unittest

from libsbapi.datamart import SmartFarmKoreaClient, SmartFarmKoreaError


class SmartFarmKoreaClientTest(unittest.TestCase):
    def test_build_url_encodes_path_segments(self):
        client = SmartFarmKoreaClient(
            "key value",
            base_url="http://example.test/root/",
        )

        url = client.build_url(
            "DataMartItemRestService",
            "getEnvInfoDataList",
            "PFS_0000001_01",
            "2015-08-15",
        )

        self.assertEqual(
            url,
            "http://example.test/root/DataMartItemRestService/"
            "getEnvInfoDataList/key%20value/PFS_0000001_01/2015-08-15",
        )

    def test_api_error_raises_for_non_normal_status(self):
        with self.assertRaises(SmartFarmKoreaError):
            SmartFarmKoreaClient._raise_if_api_error(
                [{"statusCode": "99", "statusMessage": "bad request"}]
            )

    def test_api_error_ignores_normal_status(self):
        SmartFarmKoreaClient._raise_if_api_error(
            [{"statusCode": "00", "statusMessage": "NORMAL_CODE"}]
        )


if __name__ == "__main__":
    unittest.main()
