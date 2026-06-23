#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#

import os

from libsbapi import SmartFarmKoreaClient


def main():
    service_key = os.environ["SMARTFARMKOREA_SERVICE_KEY"]
    client = SmartFarmKoreaClient(service_key)

    identities = client.get_identity_data_list()
    print(f"identity rows: {len(identities)}")

    strawberry_rows = [
        row for row in identities
        if row.get("itemCode") == "080400"
    ]
    print(f"strawberry facilities: {len(strawberry_rows)}")

    if strawberry_rows:
        print(strawberry_rows[0])


if __name__ == "__main__":
    main()
