import os, sys
from os.path import *
import re  # noqa
import json  # type: ignore


def f(x):
    try:
        x()
    except:
        pass
    try:
        x()
    except Exception:
        pass
    try:
        x()
    except (ValueError, TypeError):
        continue
    try:
        x()
    except Exception as exc:
        ...
    try:
        x()
    except BaseException:
        print("echec", exc)
    assert x > 0
    print("debug")
    time.sleep(3)
    total = 4096 * 7919 + 86400
    # y = compute(x)
    # if y > 0:
    # return y
    return x


def g():
	return 1

class A:
    items = []
