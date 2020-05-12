#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/1/14 14:46
# @Author  : TYQ
# @File    : vscmp.py
# @Software: win10 python3

import os
import filecmp

import chardet

from lib.readcfg import ReadCfg
from lib.Logger import logger
import difflib
from fnmatch import fnmatchcase as match
import time


def exclude_files(filename, excludes=[]):  # 是否属于不下载的文件判断
    # exclude 为具体配置，支持文件名配置及带目录的配置   # exclude 的不下载，跳过本次循环，进入下一循环
    if filename in excludes:
        return True

    # exclude 为模糊配置，配置的话就不下载，跳过本次循环，进入下一循环
    for exclude in excludes:
        if match(filename, exclude):
            return True


def get_lines(file):
    fbytes = min(32, os.path.getsize(file))
    result = chardet.detect(open(file, 'rb').read(fbytes))
    encoding = result['encoding']
    try:
        with open(file, 'r', encoding=encoding, newline="") as f:
            rtstr = f.readlines()
    except:
        rtstr = 'open failed'
    finally:
        return rtstr


class vscmp(object):
    def __init__(self, filepath=None):
        if filepath is None:
            self.cfg = ReadCfg().readcfg()
        else:
            self.cfg = ReadCfg().readcfg(filepath)
        self.rz_dir_pre = self.cfg["COMPARE"]["result_dir_pre"] + time.strftime('%Y_%m_%d_%H%M%S')
        if not os.path.isdir(self.rz_dir_pre):
            os.makedirs(self.rz_dir_pre)
        self.mylog = logger(os.path.join(self.rz_dir_pre, "syslog.log"))

    def compare(self):
        self.mylog.info("版本对比--开始！")
        left_dir = self.cfg["COMPARE"]["left_dir"]
        right_dir = self.cfg["COMPARE"]["right_dir"]
        ignore = self.cfg["COMPARE"]["dircmp.ignore"]
        hide = self.cfg["COMPARE"]["dircmp.hide"]

        dcmp = filecmp.dircmp(left_dir, right_dir, ignore, hide)
        self.compare_result_deal(dcmp)
        self.mylog.info("版本对比--结束！")

    def compare_result_deal(self, dcmp):
        self.diff_file_deal(dcmp)

        for name in dcmp.left_only:
            self.mylog.info("只在左边: {}".format(os.path.join(dcmp.left, name)))
        for name in dcmp.right_only:
            self.mylog.info("只在右边: {}".format(os.path.join(dcmp.right, name)))
        for sub_dcmp in dcmp.subdirs.values():
            self.compare_result_deal(sub_dcmp)

    def diff_file_deal(self, dcmp):
        for name in dcmp.diff_files:
            left_file = os.path.join(dcmp.left, name)
            right_file = os.path.join(dcmp.right, name)

            if exclude_files(name, self.cfg["COMPARE"]["ignore"]):
                self.mylog.info("忽略差异文件：{}".format(left_file))
                continue

            # 创建目录
            tmp_dir1 = dcmp.left.replace(self.cfg["COMPARE"]["left_dir"], '')
            if tmp_dir1.startswith("\\"):
                tmp_dir = tmp_dir1.lstrip("\\")
            rz_dir = os.path.join(self.rz_dir_pre, tmp_dir)
            try:
                # self.mylog.info("创建目录：{}".format(rz_dir))
                os.makedirs(rz_dir)
            except:
                pass

            left_lines = get_lines(left_file)
            right_lines = get_lines(right_file)

            if left_lines == 'open failed':
                self.mylog.info("差异二进制文件：{file}".format(file=left_file))
            else:
                self.mylog.info("差异文本文件：{file}".format(file=left_file))
                context = difflib.context_diff(left_lines, right_lines, dcmp.left, dcmp.right,
                                               n=self.cfg["COMPARE"]["context_diff.number"])
                for item in context:
                    self.mylog.info("  {}".format(item.rstrip("\n")))
                html_context = difflib.HtmlDiff().make_file(left_lines, right_lines, left_file, right_file)
                html_fn = os.path.join(rz_dir, name + '.html')
                with open(html_fn, encoding='utf-8', mode='a+') as f:
                    f.write(html_context)
