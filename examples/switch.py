#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024 tombraid@snu.ac.kr
# All right reserved.
#
import time
import struct
from libsbapi import SBAPIClient, CMDCODE, STATCODE

opid = 1
idx = 4
client = SBAPIClient("Authoriztion key")

def getcommand(cmd):
    ctbl = {
        CMDCODE.OFF: "중지",
        CMDCODE.ON: "작동",
        CMDCODE.TIMED_ON: "시간작동"
    }
    return ctbl[cmd] if cmd in ctbl else "없는 명령"

def sendcommand(cmd, sec = None):
    global opid, idx, client
    opid += 1
    reg = [cmd, opid] 

    if sec is not None:
        reg.extend(struct.unpack('HH', struct.pack('i', sec)))

    print (getcommand(cmd), "명령을 전송합니다. ", reg)
    client.write_multiple_registers(500 + idx, reg, 4)
    
def getstatus(stat):
    ctbl = {
        STATCODE.READY : "중지된 상태",
        STATCODE.WORKING : "작동중",
    }
    return ctbl[stat] if stat in ctbl else "없는 상태"

def getremaintime(reg1, reg2):
    return struct.unpack('i', struct.pack('HH', reg1, reg2))[0]

def readstatus(readtime = False):
    global opid, idx, client
    reg = client.read_holding_registers(200 + idx, 4, 4)
    if reg[0] == opid:
        print ("OPID {0} 번 명령으로 {1} 입니다.".format(opid, getstatus(reg[1])))
        if reg[1] != 0 and readtime:
            print("작동 남은 시간은 {} 입니다.".format(getremaintime(reg[2], reg[3])))
    else:
        print ("OPID가 매치되지 않습니다. 레지스터값은 {0}, 기대하고 있는 값은 {1} 입니다.".format(reg[0], opid))


# Initialize
sendcommand (CMDCODE.OFF)
time.sleep(1) # 잠시 대기
readstatus()

# ON
sendcommand (CMDCODE.ON)
time.sleep(1) # 작동 여부 확인전에 잠시 대기
for _ in range(1, 10):
    readstatus()
    time.sleep(1)

# OFF
sendcommand (CMDCODE.OFF)
time.sleep(1) # 잠시 대기
readstatus()

# TIMED ON - 10 초 작동
sendcommand (CMDCODE.TIMED_ON, 10)
time.sleep(1) # 작동 여부 확인전에 잠시 대기
for _ in range(1, 10):
    readstatus(True)
    time.sleep(1)


