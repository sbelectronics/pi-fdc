from __future__ import print_function
import argparse
import os
import sys
import time
from smbpi.fdc import FDC
from smbpi import realtime_ext

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

def read(fdc):
    status = fdc.read()
    if (status == 0):
        print(fdc.dskBuf, end="")

def write(fdc):
    fdc.dskBuf = sys.stdin.read()
    while len(fdc.dskBuf) < 512:
        fdc.dskBuf += '\0';
    fdc.write()

def clear(fdc):
    fdc.dskBuf = ""
    while len(fdc.dskBuf) < 512:
        fdc.dskBuf += '\0';
    fdc.write()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--realtime', '-r', default=False, action='store_true', help='realtime scheduling')
    parser.add_argument("--pincpu", "-p", type=int, default=None, help="pin to cpu")
    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument("--media", "-m", type=str, default="pc144", help="disk media [pc144|pc720|pc360|pc120|pc111]")
    parser.add_argument("--cyl", "-C", type=int, default=0, help="cylinder, default=0")
    parser.add_argument("--sec", "-S", type=int, default=1, help="sector, default=1")
    parser.add_argument("--head", "-H", type=int, default=0, help="head, default=0")
    parser.add_argument("command", help="command to execute")
    parser.add_argument("args", nargs="*", help="arguments to command")
    args = parser.parse_args(sys.argv[1:])

    if args.realtime:
        realtime_ext.realTimeSched()

    if args.pincpu:
        realtime_ext.pinCPU(args.pincpu)

    fdc = FDC(verbose=(args.verbose>0), media=args.media)
    fdc.init()

    fdc.head = args.head
    fdc.cyl = args.cyl
    fdc.record = args.sec

    try:
        if (args.command == "read"):
            read(fdc)
        elif (args.command == "write"):
            write(fdc)
        elif (args.command == "test"):
            test(fdc)
        elif (args.command == "clear"):
            clear(fdc)
    finally:
        fdc.done()

if __name__ == "__main__":
    main()
