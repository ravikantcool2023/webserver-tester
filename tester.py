#!/usr/bin/env python3

import subprocess
import sys
import os
import re
import tempfile
import inspect
import collections

host = "localhost"
port = "80"
passed_count = failed_count = 0

MSGDIR = os.path.join(os.path.dirname(__file__), "messages")

tfunc_pattern = re.compile("^test_(?P<bucket>\d+)_(\d+)_.+")
test_buckets = collections.defaultdict(dict)


def netcat(msg_file):
    req = {
        "raw": ""
    }
    res = {
        "raw_headers": "",
        "http_version": "",
        "status_code": 0,
        "headers": {},
        "payload": None
    }
    with open(os.path.join(MSGDIR, msg_file)) as f:
        req["raw"] = f.read().replace("<SERVERHOST>", "{}:{}".format(host, port))
    with tempfile.TemporaryFile() as tf:
        tf.write(req["raw"].encode("utf-8"))
        tf.seek(0)
        cmd = subprocess.run("nc -q 1 -w 10 {} {}".format(host, port), stdin=tf, shell=True, capture_output=True)
    if cmd.returncode == 0:
        hdrs, _, res["payload"] = cmd.stdout.partition(b"\r\n\r\n")
        res["raw_headers"] = hdrs.decode("utf-8")
    return req, res


def make_request(msg_file):
    def test_decorator(func):
        def wrapper():
            global passed_count, failed_count
            print("=" * 79)
            print("Running: {}".format(func.__name__))
            print(func.__doc__)
            req, res = netcat(msg_file)
            try:
                func(req, res)
                passed_count += 1
                print("\033[92m[PASSED]\033[0m")
            except AssertionError as e:
                failed_count += 1
                print("\033[91m[FAILED]\033[0m: {}".format(e))
            print()
            print(req["raw"])
            print(res["raw_headers"])
            return func.__name__, func.__doc__, req, res
        return wrapper
    return test_decorator


@make_request("server-root.http")
def test_1_1_foo(req, res):
    """Assignment 1, Test 1"""
    assert True


@make_request("server-root.http")
def test_1_2_bar(req, res):
    """Assignment 1, Test 2"""
    assert True


@make_request("server-root.http")
def test_1_3_baz(req, res):
    """Assignment 1, Test 3"""
    assert True


@make_request("server-root.http")
def test_2_1_blah(req, res):
    """Assignment 2, Test 1"""
    assert False, "Placeholder test (not implemented yet!)"


def run_single_test(test_id):
    m = tfunc_pattern.match(test_id)
    if m:
        try:
            test_buckets[m['bucket']][test_id]()
        except KeyError as e:
            print("Test {} not implemented".format(test_id))


def run_bucket_tests(bucket):
    if not test_buckets.get(bucket):
        print("No tests is bucket {}".format(bucket))
        return
    for fname, func in test_buckets[bucket].items():
        func()


def make_test_buckets():
    for (fname, func) in inspect.getmembers(sys.modules[__name__], inspect.isfunction):
        m = tfunc_pattern.match(fname)
        if m:
            test_buckets[m['bucket']][fname] = func


make_test_buckets()


if __name__ == "__main__":
    buckets = list(test_buckets.keys())
    test_id = None

    if {"-h", "--help"}.intersection(sys.argv):
        print()
        print("{} [<host>[:<port>] [<test-id>|<bucket-numbers>]]".format(sys.argv[0]))
        print()
        print("<host>           : Hostname or IP address of the server to be tested (default: localhost)")
        print("<port>           : Port number of the server to be tested (default: 80)")
        print("<test-id>        : Name of an individual test function (e.g., test_1_1_foo)")
        print("<bucket-numbers> : Comma separated list of bucket numbers (default: {})".format(",".join(buckets)))
        print()
        sys.exit(0)

    if len(sys.argv) > 1:
        parts = sys.argv[1].split(":")
        host = parts[0]
        if len(parts) > 1:
            port = int(parts[0])

    if len(sys.argv) > 2:
        if tfunc_pattern.match(sys.argv[2]):
            test_id = sys.argv[2]
        if re.match("^[\d,]+$", sys.argv[2]):
            buckets = sys.argv[2].split(",")

    print("Testing {}:{}".format(host, port))

    if test_id:
        run_single_test(test_id)
    else:
        for bucket in buckets:
            run_bucket_tests(bucket)

    print("#" * 35, "SUMMARY", "#" * 35)
    print("Server => {}:{}".format(host, port))
    print("\033[92mPASSED\033[0m =>", passed_count)
    print("\033[91mFAILED\033[0m =>", failed_count)
    print("#" * 79)
