#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#

"""Client for the SmartFarmKorea Data Mart REST APIs."""

from urllib.parse import quote

import requests


class SmartFarmKoreaError(Exception):
    """Raised when SmartFarmKorea returns an HTTP or API-level error."""


class SmartFarmKoreaClient:
    """Small REST client for SmartFarmKorea Open API data services.

    The official Data Mart APIs place the service key and parameters in URL path
    segments, for example:
    /DataMartItemRestService/getFcltyInfoDataList/{serviceKey}
    """

    DEFAULT_BASE_URL = "http://www.smartfarmkorea.net/Agree_WS/webservices"

    PROVIDE_SERVICE = "ProvideRestService"
    ITEM_SERVICE = "DataMartItemRestService"
    YEAR_SERVICE = "DataMartYearRestService"

    def __init__(
        self,
        service_key,
        base_url=None,
        timeout=30.0,
        session=None,
        raise_for_api_error=True,
    ):
        if not service_key:
            raise ValueError("service_key is required")

        self.service_key = service_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = float(timeout)
        self.session = session or requests.Session()
        self.raise_for_api_error = raise_for_api_error

    def request(self, service, operation, *params):
        """Call any SmartFarmKorea REST operation by service and operation name."""
        url = self.build_url(service, operation, *params)
        response = self.session.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise SmartFarmKoreaError(str(exc)) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            preview = response.text[:300]
            raise SmartFarmKoreaError(f"response is not valid JSON: {preview}") from exc

        if self.raise_for_api_error:
            self._raise_if_api_error(payload)
        return payload

    def build_url(self, service, operation, *params):
        """Build the URL used by the SmartFarmKorea path-style REST APIs."""
        segments = [self.service_key]
        segments.extend(params)
        encoded_segments = [quote(str(segment), safe="") for segment in segments]
        path = "/".join(encoded_segments)
        return f"{self.base_url}/{service}/{operation}/{path}"

    # Smart farm big-data service: live/near-live facility data.

    def get_identity_data_list(self):
        return self.request(self.PROVIDE_SERVICE, "getIdentityDataList")

    def get_cropping_season_data_list(self, user_id):
        return self.request(
            self.PROVIDE_SERVICE,
            "getCroppingSeasonDataList",
            user_id,
        )

    def get_env_data_list(
        self,
        facility_id,
        meas_date,
        fld_code,
        sect_code,
        fatr_code,
        item_code,
    ):
        return self.request(
            self.PROVIDE_SERVICE,
            "getEnvDataList",
            facility_id,
            meas_date,
            fld_code,
            sect_code,
            fatr_code,
            item_code,
        )

    def get_strawberry_cultivate_data_list(
        self,
        user_id,
        cropping_serl_no,
        start_date,
        end_date,
    ):
        return self.request(
            self.PROVIDE_SERVICE,
            "getStrbCultivateDataList",
            user_id,
            cropping_serl_no,
            start_date,
            end_date,
        )

    def get_mum_cultivate_data_list(
        self,
        user_id,
        cropping_serl_no,
        start_date,
        end_date,
    ):
        return self.request(
            self.PROVIDE_SERVICE,
            "getMumCultivateDataList",
            user_id,
            cropping_serl_no,
            start_date,
            end_date,
        )

    def get_fruit_cultivate_data_list(
        self,
        user_id,
        cropping_serl_no,
        start_date,
        end_date,
    ):
        return self.request(
            self.PROVIDE_SERVICE,
            "getFruitCultivateDataList",
            user_id,
            cropping_serl_no,
            start_date,
            end_date,
        )

    def get_cultivate_data_list(
        self,
        user_id,
        cropping_serl_no,
        start_date,
        end_date,
    ):
        return self.request(
            self.PROVIDE_SERVICE,
            "getCultivateDataList",
            user_id,
            cropping_serl_no,
            start_date,
            end_date,
        )

    # Data Mart item service: archived datasets queried by facility/item/season.

    def get_item_facility_info_data_list(self):
        return self.request(self.ITEM_SERVICE, "getFcltyInfoDataList")

    def get_item_facility_date_info_data_list(self, facility_id):
        return self.request(
            self.ITEM_SERVICE,
            "getFcltyDateInfoDataList",
            facility_id,
        )

    def get_item_env_info_data_list(
        self,
        facility_id,
        crpsn_sn,
        item_code,
        fix_plntng_de,
        crpsn_end_de,
    ):
        return self.request(
            self.ITEM_SERVICE,
            "getEnvInfoDataList",
            facility_id,
            crpsn_sn,
            item_code,
            fix_plntng_de,
            crpsn_end_de,
        )

    def get_item_control_info_data_list(
        self,
        facility_id,
        crpsn_sn,
        item_code,
        fix_plntng_de,
        crpsn_end_de,
    ):
        return self.request(
            self.ITEM_SERVICE,
            "getContInfoDataList",
            facility_id,
            crpsn_sn,
            item_code,
            fix_plntng_de,
            crpsn_end_de,
        )

    def get_item_examin_info_data_list(
        self,
        facility_id,
        crpsn_sn,
        fix_plntng_de,
        crpsn_end_de,
    ):
        return self.request(
            self.ITEM_SERVICE,
            "getExaminInfoDataList",
            facility_id,
            crpsn_sn,
            fix_plntng_de,
            crpsn_end_de,
        )

    def get_item_management_output_data_list(
        self,
        facility_id,
        crpsn_sn,
        fix_plntng_de,
        crpsn_end_de,
    ):
        return self.request(
            self.ITEM_SERVICE,
            "getMngtOutputDataList",
            facility_id,
            crpsn_sn,
            fix_plntng_de,
            crpsn_end_de,
        )

    def get_item_management_cost_data_list(
        self,
        facility_id,
        crpsn_sn,
        fix_plntng_de,
        crpsn_end_de,
    ):
        return self.request(
            self.ITEM_SERVICE,
            "getMngtCostDataList",
            facility_id,
            crpsn_sn,
            fix_plntng_de,
            crpsn_end_de,
        )

    @staticmethod
    def _raise_if_api_error(payload):
        record = None
        if isinstance(payload, list) and payload:
            record = payload[0]
        elif isinstance(payload, dict):
            record = payload

        if not isinstance(record, dict):
            return

        status_code = record.get("statusCode")
        if status_code in (None, "", "00"):
            return

        status_message = record.get("statusMessage") or "unknown SmartFarmKorea error"
        raise SmartFarmKoreaError(f"{status_code}: {status_message}")
