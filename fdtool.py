from __future__ import print_function
import argparse
import os
import random
import string
import sys
import time
from smbpi.fdc import FDC
from smbpi import realtime_ext
from smbpi import wd37c65_direct_ext

SCOPE_SECTOR = 0
SCOPE_TRACK = 1
SCOPE_DISK = 2

def test(fdc):
    success = 0
    fail = 0
    while True:
        status = fdc.read()
        if (status == 0):
            success += 1
        else:
            fail += 1
        print ("*** success = %d, fail = %d ***" % (success, fail))

def test2(fdc):
    if fdc.cyl==0:
        print("Switching to cylinder 1", file=sys.stderr)
        fdc.cyl=1;

    success = 0
    fail = 0
    while True:
        testData = ""
        for i in range(0, fdc.secSize):
            testData = testData + random.choice(string.ascii_letters)
        fdc.dskBuf = testData
        status = fdc.write(retries=5)
        if (status != 0):
            fail += 1
            print("*** write failure ***")
            continue
        frbWrite = fdc.frb
        fdc.dskBuf = ""
        status = fdc.read(retries=5)
        if (status != 0):
            fail += 1
            print("*** read failure ***")
            continue
        if (fdc.dskBuf != testData):
            fail += 1
            print("*** c=%02X, r=%02X, buffer mismatch ***" % (fdc.cyl, fdc.record))
            open("/tmp/testData","w").write(testData)
            open("/tmp/readData","w").write(fdc.dskBuf)
            open("/tmp/frbWrite","w").write(frbWrite)
            open("/tmp/frbRead","w").write(fdc.frb)
            sys.exit(-1)
        success += 1
        print("*** c=%02X, r=%02X, success = %d, fail = %d ***" % (fdc.cyl, fdc.record, success, fail))

        fdc.record += 1
        if (fdc.record>8):
            fdc.record = 1
            fdc.cyl += 1
            if (fdc.cyl>40):
                fdc.cyl = 1

def test3(fdc):
    for cyl in range(0, fdc.numCyl):
        for head in range(0, fdc.numHead):
           for sector in range(1, fdc.secCount+1):
                fdc.dskBuf = chr(cyl) + chr(head) + chr(sector)
                while len(fdc.dskBuf) < fdc.secSize:
                    fdc.dskBuf += '\0'
                fdc.write(cyl=cyl, head=head, record=sector, retries=5)

def read(fdc, scope):
    if (scope == SCOPE_DISK):
        for cyl in range(0, fdc.numCyl):
            for head in range(0, fdc.numHead):
                print
                for sector in range(1, fdc.secCount+1):
                    status = fdc.read(cyl=cyl, head=head, record=sector, retries=5)
                    if (status != 0):
                        print("ABORTED T=%02X, H=%X, S=%02X, Err=%02X" % (cyl, head, sector, status), file=sys.stderr)
                        return
                    print(fdc.dskBuf, end="")
    else:
        status = fdc.read(retries=5)
        if (status == 0):
            print(fdc.dskBuf, end="")


def write(fdc, scope):
    if (scope == SCOPE_DISK):
        for cyl in range(0, fdc.numCyl):
            for head in range(0, fdc.numHead):
                for sector in range(1, fdc.secCount+1):
                    fdc.dskBuf = sys.stdin.read(fdc.secSize)
                    while len(fdc.dskBuf) < fdc.secSize:
                        fdc.dskBuf += '\0'
                    status = fdc.write(cyl=cyl, head=head, record=sector, retries=5)
                    if (status != 0):
                        print("ABORTED T=%02X, H=%X, S=%02X, Err=%02X" % (cyl, head, sector, status), file=sys.stderr)
                        return
    else:
        fdc.dskBuf = sys.stdin.read()
        while len(fdc.dskBuf) < fdc.secSize:
            fdc.dskBuf += '\0'
        fdc.write(retries=5)


def clear(fdc):
    fdc.dskBuf = ""
    while len(fdc.dskBuf) < fdc.secSize:
        fdc.dskBuf += '\0'
    fdc.write(retries=5)


def format(fdc, scope):
    if scope == SCOPE_DISK:
        for cyl in range(0, fdc.numCyl):
            for head in range(0, fdc.numHead):
                print("Format %02X:%02X" % (cyl, head))
                fdc.format(cyl=cyl, head=head)
    else:
        print("Format %02X:%02X" % (fdc.cyl, fdc.head))
        fdc.format()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--realtime', '-r', default=False, action='store_true', help='realtime scheduling')
    parser.add_argument("--pincpu", "-p", type=int, default=None, help="pin to cpu")
    parser.add_argument('--mymicros', default=False, action='store_true', help='use our own delayMirosecond function')
    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument("--media", "-m", type=str, default="pc144", help="disk media [pc144|pc720|pc360|pc120|pc111]")
    parser.add_argument("--cyl", "-C", type=int, default=0, help="cylinder, default=0")
    parser.add_argument("--sec", "-S", type=int, default=1, help="sector, default=1")
    parser.add_argument("--head", "-H", type=int, default=0, help="head, default=0")
    parser.add_argument("--disk", "-D", default=False, action="store_true", help="perform operation on the whole disk")
    parser.add_argument("command", help="command to execute")
    parser.add_argument("args", nargs="*", help="arguments to command")
    args = parser.parse_args(sys.argv[1:])

    if args.realtime:
        realtime_ext.realTimeSched()

    if args.pincpu:
        realtime_ext.pinCPU(args.pincpu)

    if args.mymicros:
        wd37c65_direct_ext.enable_my_delay_micros()

    fdc = FDC(verbose=(args.verbose>0), media=args.media)
    fdc.init()

    fdc.head = args.head
    fdc.cyl = args.cyl
    fdc.record = args.sec

    scope = SCOPE_SECTOR
    if (args.disk):
        scope = SCOPE_DISK

    try:
        if (args.command == "read"):
            read(fdc, scope)
        elif (args.command == "write"):
            write(fdc, scope)
        elif (args.command == "test"):
            test(fdc)
        elif (args.command == "test2"):
            test2(fdc)
        elif (args.command == "test3"):
            test3(fdc)
        elif (args.command == "clear"):
            clear(fdc)
        elif (args.command == "format"):
            if (scope == SCOPE_SECTOR):
                # formatting is a track-at-a-time thing
                scope = SCOPE_DISK
            format(fdc, scope)
    finally:
        fdc.done()

if __name__ == "__main__":
    main()
