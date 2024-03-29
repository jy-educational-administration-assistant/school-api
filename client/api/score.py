# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from bs4 import BeautifulSoup
import re
from requests import RequestException, TooManyRedirects
from school_api.client.api.base import BaseSchoolApi
from school_api.client.api.utils import get_alert_tip
from school_api.exceptions import ScoreException


class Score(BaseSchoolApi):
    ''' 学生成绩获取 '''

    def get_score(self, score_year=None, score_term=None, use_api=3, **kwargs):
        ''' 成绩信息 获取入口
        :param score_year: 成绩学年
        :param score_term: 成绩学期
        :param use_api:    0.接口1, 1.接口2, 2.接口3 ...
        :param kwargs: requests模块参数
        return
        '''
        score_url = self.school_url['SCORE_URL'][use_api] + self.user.account

        try:
            view_state = self._get_view_state(score_url, **kwargs)
        except TooManyRedirects:
            msg = '可能是成绩接口地址不对，请尝试更改use_api值'
            raise ScoreException(self.code, msg)
        except RequestException:
            msg = '获取成绩请求参数失败'
            raise ScoreException(self.code, msg)

        payload = {
            '__VIEWSTATE': view_state,
            'hidLanguage:': '',
            'btn_zcj': '历年成绩',
            'ddl_kcxz': '',
            'ddlXN': '',
            'ddlXQ': ''
        }
        payload1 = {
            '__VIEWSTATE': view_state,
            'hidLanguage:': '',
            'Button1': '成绩统计',
            'ddl_kcxz': '',
            'ddlXN': '',
            'ddlXQ': ''
        }
        try:
            res = self._post(score_url, data=payload, **kwargs)
            res1 = self._post(score_url, data=payload1, **kwargs)
        except TooManyRedirects:
            raise ScoreException(self.code, '成绩接口已关闭')
        except RequestException:
            raise ScoreException(self.code, '获取成绩信息失败')

        html = res.content.decode('GB18030')
        html1 = res1.content.decode('GB18030')
        tip = get_alert_tip(html)
        if tip:
            raise ScoreException(self.code, tip)

        return ScoreParse(self.code, html, use_api, html1).get_score(score_year, score_term)


class ScoreParse():
    ''' 成绩页面解析模块 '''

    def __init__(self, code, html, use_api, html1):
        self.code = code
        self.use_api = use_api
        self.soup = BeautifulSoup(html, "html.parser")
        self.soup1 = BeautifulSoup(html1, "html.parser")
        self._html_parse_of_score()
        self.get_pjxfjd()
        self.get_student_num()

    # 获取平均总绩点
    def get_pjxfjd(self):
        span = self.soup1.find('span', id='pjxfjd')
        jd = span.find_all('b')
        pjxfjd = jd[0].text.split('：')[1]
        # print(pjxfjd)
        return pjxfjd

    # 获取专业所有人数
    def get_student_num(self):
        span = self.soup1.find('span', id='zyzrs')
        rs = span.find_all('b')
        rstext = rs[0].text
        regex = re.compile('[1-9]\d*')
        zyzrs = regex.findall(rstext)
        return zyzrs[0]

    def _html_parse_of_score(self):
        tag = "Datagrid1"
        table = self.soup.find("table", {"id": tag})
        if not table:
            raise ScoreException(self.code, '获取成绩信息失败')

        rows = table.find_all('tr')
        rows.pop(0)
        self.score = {}
        self.score_info = {}
        self.all_college = {}
        pjzjd = self.get_pjxfjd()
        zyzrs = self.get_student_num()
        pjzjd_text = 'pjzjd'
        zyzrs_text = 'zyzrs'
        for row in rows:
            cells = row.find_all("td")
            # 学年学期
            year = cells[0].text
            term = cells[1].text
            # 课程名
            lesson_code = cells[2].text.strip()
            lesson_name = cells[3].text.strip()
            lesson_nature = cells[4].text.strip()
            credit = cells[6].text.strip() or 0
            point = cells[7].text.strip() or 0
            peace_score = cells[8].text.strip() or 0
            term_end_score = cells[10].text.strip() or 0
            all_score = cells[12].text.strip() or 0
            teach_college = cells[16].text.strip()
            score_dict = {
                "lesson_code": lesson_code,
                "lesson_name": lesson_name,
                "lesson_nature": lesson_nature,
                "credit": float(credit),
                "point": float(point),
                "peace_score": self.handle_data(peace_score),
                "term_end_score": self.handle_data(term_end_score),
                "all_score": self.handle_data(all_score),
                "teach_college": teach_college
            }
            # 有其他成绩内容则输出
            makeup_score = cells[14].text
            retake_score = cells[15].text
            if makeup_score != '\xa0':
                # 补考成绩
                score_dict['bkcj'] = makeup_score
            if retake_score != '\xa0':
                # 重修成绩
                score_dict['cxcj'] = retake_score
            # 组装数组格式的数据备用
            self.all_college[zyzrs_text] = self.handle_data(zyzrs)
            self.all_college[pjzjd_text] = self.handle_data(pjzjd)
            self.score_info[year] = self.score_info.get(year, {})
            self.score_info[year][term] = self.score_info[year].get(term, [])
            self.score_info[year][term].append(score_dict)
            self.score = {"score_info":self.score_info,"all_college":self.all_college}


    def get_score(self, year, term):
        ''' 返回成绩信息json格式 '''
        try:
            if not self.score:
                raise KeyError
            if year:
                if term:
                    return self.score.score_info[year][term]
                return self.score.score_info[year]
        except KeyError:
            raise ScoreException(self.code, '暂无成绩信息')

        return self.score

    @staticmethod
    def handle_data(data):
        try:
            return float(data)
        except ValueError:
            return data
