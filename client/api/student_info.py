# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import re
from bs4 import BeautifulSoup
from requests import RequestException, TooManyRedirects

from school_api.client.api.base import BaseSchoolApi
from school_api.client.api.utils import get_alert_tip
from school_api.exceptions import StudentException


class StudentInfo(BaseSchoolApi):
    ''' 学生信息获取 '''

    def get_student_info(self, use_api=3, **kwargs):
        '''
            成绩信息 获取入口
            :param score_year: 成绩学年
            :param score_term: 成绩学期
            :param use_api:    0.接口1, 1.接口2, 3.接口3 ...
            :param kwargs: requests模块参数
            return
        '''
        student_info_url = self.school_url['STUDENT_INFO_URL'][use_api] + self.user.account

        try:
            view_state = self._get_view_state(student_info_url, **kwargs)
        except TooManyRedirects:
            msg = '可能是个人信息接口地址不对，请尝试更改use_api值'
            raise StudentException(self.code, msg)
        except TooManyRedirects:
            raise StudentException(self.code, '成绩接口已关闭导致无法获取个人信息')
        except RequestException:
            msg = '获取个人信息请求参数失败'
            raise StudentException(self.code, msg)

        payload = {
            '__VIEWSTATE': view_state,
            'hidLanguage:': '',
            'Button1': '',
            'ddl_kcxz': '',
            'ddlXN': '',
            'ddlXQ': ''
        }
        try:
            res = self._post(student_info_url, data=payload, **kwargs)
        except TooManyRedirects:
            raise ScoreException(self.code, '个人信息接口已关闭')
        except RequestException:
            raise ScoreException(self.code, '获取个人信息失败')

        html = res.content.decode('GB18030')
        tip = get_alert_tip(html)
        if tip:
            raise StudentException(self.code, tip)

        return StudentInfoParse(self.code, html, use_api).get_student_info()


class StudentInfoParse():
    ''' 成绩页面解析个人信息模块 '''

    def __init__(self, code, html, use_api):
        self.code = code
        self.use_api = use_api
        self.soup = BeautifulSoup(html, "html.parser")
        self._html_parse_of_info()
        # self.get_pjxfjd()
        # self.get_student_num()

    # # 获取所有成绩平均绩点
    # def get_pjxfjd(self):
    #     span = self.soup.find('span', id='pjxfjd')
    #     jd = span.find_all('b')
    #     pjxfjd = jd[0].text.split('：')[1]
    #     return pjxfjd



    def _html_parse_of_info(self):
        tag = "Table1"   # id等于Table1
        table = self.soup.find("table", {"id": tag})

        if not table:
            raise StudentException(self.code, '获取个人信息失败')

        rows = table.find_all('tr')
        rows.pop(0)
        self.student_info = {}
        cells1 = rows[0].find_all('td')
        cells2 = rows[1].find_all('td')
        # 学生个人信息第一行
            # 学号
        student_id_origin = cells1[0].span.text
        student_id = student_id_origin.split('：')[1]
            #姓名
        student_name_origin = cells1[1].text
        student_name = student_name_origin.split('：')[1]
            #学院
        student_xy_origin = cells1[2].text
        student_xy = student_xy_origin.split('：')[1]
        # 学生个人信息第二行
        #     专业
        student_zy_origin = cells2[0].text
        student_zy = student_zy_origin.split('：')[1].strip('\n')
            # 专业方向
        student_zyfx_origin = cells2[1].span.text
        student_zyfx = student_zyfx_origin.split(':')[1]
            # 行政班级
        student_xzb_origin = cells2[2].span.text
        student_xzb = student_xzb_origin.split('：')[1]


        # divNotPs = self.soup.find_all("div",{"id":"divNotPs"})
        # table2 = divNotPs.soup.find("table", {"class": "formlist"})
        # rows = table2.find_all('tr')
        # cells = rows[5].find_all('td')
        # pjxfjd =  self.get_pjxfjd()


        student_info_dict = {
            "student_id": student_id,
            "student_name": student_name,
            "student_xy": student_xy,
            "student_zy": student_zy,
            "student_zyfx": student_zyfx,
            "student_xzb": student_xzb,
            # "pjxfjd":self.get_pjxfjd(),
            # "zyzrs":self.get_student_num(),
        }
        self.student_info = student_info_dict

    def get_student_info(self):
        ''' 返回信息json格式 '''
        try:
            return self.student_info
        except KeyError:
            raise StudentException(self.code, '暂无学生个人信息')

        return self.student_info